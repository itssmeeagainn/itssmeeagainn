from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

from ..database import get_db
from ..models import Wallet, Transaction, RiskAssessment, Alert
from ..services.blockchain_api import blockchain_service
from ..services.llm_service import llm_service
from ..config import KNOWN_WALLET_LABELS, BLOCKCHAIN_CONFIGS
from .schemas import WalletAnalysisRequest, TransactionAnalysisResponse, WalletResponse, DashboardResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard HTML page."""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AML Crypto Monitor</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    </head>
    <body class="bg-gray-100">
        <div id="app" x-data="dashboardApp()" x-init="init()">
            <!-- Header -->
            <header class="bg-white shadow-lg">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div class="flex justify-between items-center py-6">
                        <div class="flex items-center">
                            <i class="fas fa-shield-alt text-blue-600 text-2xl mr-3"></i>
                            <h1 class="text-3xl font-bold text-gray-900">AML Crypto Monitor</h1>
                        </div>
                        <div class="flex items-center space-x-4">
                            <div class="text-sm text-gray-500">
                                Last Updated: <span x-text="lastUpdated"></span>
                            </div>
                            <button @click="refreshData()" 
                                    :disabled="loading"
                                    class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50">
                                <i class="fas fa-sync-alt mr-2" :class="{'fa-spin': loading}"></i>
                                Refresh
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            <!-- Wallet Input Section -->
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <div class="bg-white rounded-lg shadow p-6 mb-6">
                    <h2 class="text-xl font-semibold mb-4">Analyze Wallet</h2>
                    <div class="flex space-x-4">
                        <input type="text" 
                               x-model="walletAddress"
                               placeholder="Enter wallet address (0x...)"
                               class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent">
                        <select x-model="selectedNetwork" class="px-4 py-2 border border-gray-300 rounded-lg">
                            <option value="">All Networks</option>
                            <option value="ethereum">Ethereum</option>
                            <option value="bsc">BSC</option>
                            <option value="polygon">Polygon</option>
                            <option value="arbitrum">Arbitrum</option>
                            <option value="optimism">Optimism</option>
                        </select>
                        <button @click="analyzeWallet()" 
                                :disabled="!walletAddress || loading"
                                class="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50">
                            <i class="fas fa-search mr-2"></i>
                            Analyze
                        </button>
                    </div>
                </div>

                <!-- Stats Cards -->
                <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
                    <div class="bg-white rounded-lg shadow p-6">
                        <div class="flex items-center">
                            <div class="p-3 rounded-full bg-blue-100 text-blue-600">
                                <i class="fas fa-wallet text-xl"></i>
                            </div>
                            <div class="ml-4">
                                <p class="text-sm font-medium text-gray-500">Total Wallets</p>
                                <p class="text-2xl font-semibold text-gray-900" x-text="stats.totalWallets"></p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="bg-white rounded-lg shadow p-6">
                        <div class="flex items-center">
                            <div class="p-3 rounded-full bg-green-100 text-green-600">
                                <i class="fas fa-exchange-alt text-xl"></i>
                            </div>
                            <div class="ml-4">
                                <p class="text-sm font-medium text-gray-500">Total Transactions</p>
                                <p class="text-2xl font-semibold text-gray-900" x-text="stats.totalTransactions"></p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="bg-white rounded-lg shadow p-6">
                        <div class="flex items-center">
                            <div class="p-3 rounded-full bg-red-100 text-red-600">
                                <i class="fas fa-exclamation-triangle text-xl"></i>
                            </div>
                            <div class="ml-4">
                                <p class="text-sm font-medium text-gray-500">High Risk</p>
                                <p class="text-2xl font-semibold text-gray-900" x-text="stats.highRiskWallets"></p>
                            </div>
                        </div>
                    </div>
                    
                    <div class="bg-white rounded-lg shadow p-6">
                        <div class="flex items-center">
                            <div class="p-3 rounded-full bg-yellow-100 text-yellow-600">
                                <i class="fas fa-dollar-sign text-xl"></i>
                            </div>
                            <div class="ml-4">
                                <p class="text-sm font-medium text-gray-500">Total Volume</p>
                                <p class="text-2xl font-semibold text-gray-900" x-text="formatCurrency(stats.totalVolume)"></p>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Recent Transactions Table -->
                <div class="bg-white rounded-lg shadow">
                    <div class="px-6 py-4 border-b border-gray-200">
                        <h3 class="text-lg font-medium text-gray-900">Recent Transactions</h3>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">From</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">To</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Token</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">USD Value</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Risk</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-200">
                                <template x-for="tx in transactions" :key="tx.hash">
                                    <tr class="hover:bg-gray-50">
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900" x-text="formatTime(tx.timestamp)"></td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <div class="text-sm font-medium text-gray-900" x-text="tx.from_label || truncateAddress(tx.from_address)"></div>
                                            <div class="text-sm text-gray-500" x-text="truncateAddress(tx.from_address)"></div>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <div class="text-sm font-medium text-gray-900" x-text="tx.to_label || truncateAddress(tx.to_address)"></div>
                                            <div class="text-sm text-gray-500" x-text="truncateAddress(tx.to_address)"></div>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900" x-text="formatAmount(tx.amount)"></td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800" x-text="tx.token_symbol"></span>
                                        </td>
                                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900" x-text="formatCurrency(tx.usd_value)"></td>
                                        <td class="px-6 py-4 whitespace-nowrap">
                                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                                                  :class="getRiskBadgeClass(tx.risk_score)">
                                                <span x-text="getRiskLevel(tx.risk_score)"></span>
                                                (<span x-text="tx.risk_score"></span>)
                                            </span>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                        <div x-show="loading" class="text-center py-8">
                            <i class="fas fa-spinner fa-spin text-2xl text-gray-400"></i>
                            <p class="text-gray-500 mt-2">Loading transactions...</p>
                        </div>
                        <div x-show="!loading && transactions.length === 0" class="text-center py-8">
                            <i class="fas fa-search text-4xl text-gray-300"></i>
                            <p class="text-gray-500 mt-2">No transactions found. Analyze a wallet to get started.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            function dashboardApp() {
                return {
                    walletAddress: '',
                    selectedNetwork: '',
                    transactions: [],
                    stats: {
                        totalWallets: 0,
                        totalTransactions: 0,
                        highRiskWallets: 0,
                        totalVolume: 0
                    },
                    loading: false,
                    lastUpdated: new Date().toLocaleString(),

                    init() {
                        this.loadStats();
                    },

                    async loadStats() {
                        try {
                            const response = await fetch('/api/dashboard/stats');
                            const data = await response.json();
                            this.stats = data;
                        } catch (error) {
                            console.error('Failed to load stats:', error);
                        }
                    },

                    async analyzeWallet() {
                        if (!this.walletAddress) return;
                        
                        this.loading = true;
                        try {
                            const response = await fetch('/api/wallet/analyze', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                    address: this.walletAddress,
                                    networks: this.selectedNetwork ? [this.selectedNetwork] : null
                                })
                            });
                            
                            const data = await response.json();
                            this.transactions = data.transactions || [];
                            this.lastUpdated = new Date().toLocaleString();
                            await this.loadStats();
                        } catch (error) {
                            console.error('Failed to analyze wallet:', error);
                            alert('Failed to analyze wallet. Please check the address and try again.');
                        } finally {
                            this.loading = false;
                        }
                    },

                    async refreshData() {
                        await this.loadStats();
                        if (this.walletAddress) {
                            await this.analyzeWallet();
                        }
                    },

                    formatTime(timestamp) {
                        const date = new Date(timestamp);
                        const now = new Date();
                        const diff = now - date;
                        
                        const minutes = Math.floor(diff / 60000);
                        const hours = Math.floor(diff / 3600000);
                        const days = Math.floor(diff / 86400000);
                        const months = Math.floor(diff / 2628000000);
                        
                        if (months > 0) return `${months} months ago`;
                        if (days > 0) return `${days} days ago`;
                        if (hours > 0) return `${hours} hours ago`;
                        if (minutes > 0) return `${minutes} minutes ago`;
                        return 'Just now';
                    },

                    formatAmount(amount) {
                        if (!amount) return '0';
                        return parseFloat(amount).toLocaleString(undefined, {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 6
                        });
                    },

                    formatCurrency(amount) {
                        if (!amount) return '$0';
                        return new Intl.NumberFormat('en-US', {
                            style: 'currency',
                            currency: 'USD',
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 0
                        }).format(amount);
                    },

                    truncateAddress(address) {
                        if (!address) return '';
                        return address.slice(0, 6) + '...' + address.slice(-4);
                    },

                    getRiskLevel(score) {
                        if (score >= 75) return 'Critical';
                        if (score >= 50) return 'High';
                        if (score >= 25) return 'Medium';
                        return 'Low';
                    },

                    getRiskBadgeClass(score) {
                        if (score >= 75) return 'bg-red-100 text-red-800';
                        if (score >= 50) return 'bg-orange-100 text-orange-800';
                        if (score >= 25) return 'bg-yellow-100 text-yellow-800';
                        return 'bg-green-100 text-green-800';
                    }
                }
            }
        </script>
    </body>
    </html>
    """
    return html_content


@router.post("/api/wallet/analyze")
async def analyze_wallet(
    request: WalletAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Analyze a wallet address across multiple networks."""
    try:
        # Get transactions from blockchain APIs
        networks = request.networks or list(BLOCKCHAIN_CONFIGS.keys())
        
        all_transactions = []
        wallet_data = None
        
        for network in networks:
            try:
                # Get transactions
                raw_transactions = await blockchain_service.get_wallet_transactions(
                    request.address, network, offset=request.limit or 100
                )
                
                # Parse and add to results
                for raw_tx in raw_transactions:
                    parsed_tx = blockchain_service.parse_transaction(raw_tx, network)
                    
                    # Add USD value estimation (simplified)
                    if not parsed_tx.get("usd_value"):
                        parsed_tx["usd_value"] = parsed_tx["amount"] * 2000  # Rough ETH price
                    
                    # Get risk analysis from LLM
                    if request.analyze_risk:
                        risk_analysis = await llm_service.analyze_transaction_risk(parsed_tx)
                        parsed_tx.update(risk_analysis)
                    
                    all_transactions.append(parsed_tx)
                
                # Store wallet if not exists
                if not wallet_data:
                    wallet = db.query(Wallet).filter(
                        Wallet.address == request.address.lower()
                    ).first()
                    
                    if not wallet:
                        wallet = Wallet(
                            address=request.address.lower(),
                            network=network,
                            label=blockchain_service.get_wallet_label(request.address),
                            is_monitored=True,
                            transaction_count=len(raw_transactions)
                        )
                        db.add(wallet)
                        db.commit()
                        db.refresh(wallet)
                    
                    wallet_data = {
                        "address": wallet.address,
                        "network": wallet.network,
                        "label": wallet.label,
                        "risk_score": wallet.risk_score,
                        "is_flagged": wallet.is_flagged,
                        "transaction_count": wallet.transaction_count
                    }
            
            except Exception as e:
                print(f"Error fetching from {network}: {str(e)}")
                continue
        
        # Sort transactions by timestamp
        all_transactions.sort(key=lambda x: x.get("timestamp", datetime.min), reverse=True)
        
        # Background task: Store transactions in database
        if all_transactions:
            background_tasks.add_task(store_transactions, all_transactions, db)
        
        return {
            "wallet": wallet_data,
            "transactions": all_transactions[:request.limit or 100],
            "total_count": len(all_transactions),
            "networks_analyzed": networks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/api/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    try:
        total_wallets = db.query(Wallet).count()
        total_transactions = db.query(Transaction).count()
        high_risk_wallets = db.query(Wallet).filter(Wallet.risk_score >= 75).count()
        
        # Calculate total volume from recent transactions
        recent_transactions = db.query(Transaction).filter(
            Transaction.usd_value.isnot(None)
        ).limit(1000).all()
        
        total_volume = sum(tx.usd_value or 0 for tx in recent_transactions)
        
        return {
            "totalWallets": total_wallets,
            "totalTransactions": total_transactions,
            "highRiskWallets": high_risk_wallets,
            "totalVolume": total_volume
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/api/transactions")
async def get_transactions(
    wallet_address: Optional[str] = Query(None),
    network: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    risk_level: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get transactions with filtering options."""
    try:
        query = db.query(Transaction)
        
        if wallet_address:
            query = query.filter(
                or_(
                    Transaction.from_address == wallet_address.lower(),
                    Transaction.to_address == wallet_address.lower()
                )
            )
        
        if network:
            query = query.filter(Transaction.network == network)
        
        if risk_level:
            risk_thresholds = {"low": 25, "medium": 50, "high": 75}
            min_score = risk_thresholds.get(risk_level, 0)
            max_score = 100 if risk_level == "critical" else risk_thresholds.get(risk_level, 25)
            query = query.filter(
                and_(
                    Transaction.risk_score >= min_score,
                    Transaction.risk_score < max_score
                )
            )
        
        transactions = query.order_by(desc(Transaction.block_timestamp)).offset(offset).limit(limit).all()
        
        return [
            {
                "hash": tx.hash,
                "network": tx.network,
                "timestamp": tx.block_timestamp,
                "from_address": tx.from_address,
                "to_address": tx.to_address,
                "from_label": blockchain_service.get_wallet_label(tx.from_address),
                "to_label": blockchain_service.get_wallet_label(tx.to_address),
                "amount": float(tx.amount_float),
                "token_symbol": tx.token_symbol,
                "usd_value": tx.usd_value,
                "risk_score": tx.risk_score,
                "status": tx.status,
                "transaction_type": tx.transaction_type
            }
            for tx in transactions
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transactions: {str(e)}")


@router.get("/api/wallets")
async def get_wallets(
    risk_level: Optional[str] = Query(None),
    is_flagged: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get wallets with filtering options."""
    try:
        query = db.query(Wallet)
        
        if risk_level:
            risk_thresholds = {"low": 25, "medium": 50, "high": 75}
            min_score = risk_thresholds.get(risk_level, 0)
            max_score = 100 if risk_level == "critical" else risk_thresholds.get(risk_level, 25)
            query = query.filter(
                and_(
                    Wallet.risk_score >= min_score,
                    Wallet.risk_score < max_score
                )
            )
        
        if is_flagged is not None:
            query = query.filter(Wallet.is_flagged == is_flagged)
        
        wallets = query.order_by(desc(Wallet.risk_score)).offset(offset).limit(limit).all()
        
        return [
            {
                "address": wallet.address,
                "network": wallet.network,
                "label": wallet.label,
                "risk_score": wallet.risk_score,
                "is_flagged": wallet.is_flagged,
                "transaction_count": wallet.transaction_count,
                "total_balance_usd": wallet.total_balance_usd,
                "last_activity": wallet.last_activity
            }
            for wallet in wallets
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get wallets: {str(e)}")


@router.get("/api/alerts")
async def get_alerts(
    severity: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    """Get alerts with filtering options."""
    try:
        query = db.query(Alert)
        
        if severity:
            query = query.filter(Alert.severity == severity)
        
        if acknowledged is not None:
            query = query.filter(Alert.is_acknowledged == acknowledged)
        
        alerts = query.order_by(desc(Alert.created_at)).offset(offset).limit(limit).all()
        
        return [
            {
                "id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "title": alert.title,
                "message": alert.message,
                "related_wallet_address": alert.related_wallet_address,
                "related_transaction_hash": alert.related_transaction_hash,
                "is_acknowledged": alert.is_acknowledged,
                "created_at": alert.created_at
            }
            for alert in alerts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")


async def store_transactions(transactions: List[Dict], db: Session):
    """Background task to store transactions in database."""
    try:
        for tx_data in transactions:
            # Check if transaction already exists
            existing = db.query(Transaction).filter(Transaction.hash == tx_data.get("hash")).first()
            if existing:
                continue
            
            # Create new transaction record
            transaction = Transaction(
                hash=tx_data.get("hash"),
                network=tx_data.get("network"),
                block_number=tx_data.get("block_number", 0),
                block_timestamp=tx_data.get("timestamp"),
                from_address=tx_data.get("from_address"),
                to_address=tx_data.get("to_address"),
                amount=str(tx_data.get("amount_raw", "0")),
                amount_float=tx_data.get("amount", 0),
                token_symbol=tx_data.get("token_symbol"),
                token_address=tx_data.get("token_address"),
                token_name=tx_data.get("token_name"),
                token_decimals=tx_data.get("token_decimals"),
                usd_value=tx_data.get("usd_value"),
                gas_used=tx_data.get("gas_used"),
                gas_price=tx_data.get("gas_price"),
                status=tx_data.get("status", "success"),
                transaction_type=tx_data.get("transaction_type"),
                risk_score=tx_data.get("risk_score", 0)
            )
            
            db.add(transaction)
        
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Failed to store transactions: {str(e)}")