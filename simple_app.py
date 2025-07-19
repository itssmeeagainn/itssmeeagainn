#!/usr/bin/env python3
"""
Simple AML Crypto Transaction Monitor
Uses your Etherscan API key to pull transaction data
"""

import os
import asyncio
import httpx
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI()

# Known wallet labels
KNOWN_WALLETS = {
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": "Binance Hot Wallet",
    "0xd551234ae421e3bcba99a0da6d736074f22192ff": "Binance Hot Wallet 2",
    "0x564286362092d8e7936f0549571a803b203aaced": "Binance Hot Wallet 3",
    "0xfe9e8709d3215310075d67e3ed32a380ccf451c8": "Coinbase Hot Wallet",
    "0xa090e606e30bd747d4e6245a1517ebe430f0057e": "Coinbase Hot Wallet 2",
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503": "ChangeNOW",
    "0x1522900b6dafac587d499a862861c0869be6e428": "KuCoin Hot Wallet",
    "0xa1d8d972560c2f8144af871db508f0b0b10a3fbf": "Kraken Hot Wallet",
}

def get_wallet_label(address):
    """Get label for known wallet addresses"""
    return KNOWN_WALLETS.get(address.lower(), None)

def format_time_ago(timestamp):
    """Format timestamp as time ago"""
    try:
        tx_time = datetime.fromtimestamp(int(timestamp))
        now = datetime.now()
        diff = now - tx_time
        
        if diff.days > 365:
            return f"{diff.days // 365} years ago"
        elif diff.days > 30:
            return f"{diff.days // 30} months ago"
        elif diff.days > 0:
            return f"{diff.days} days ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hours ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minutes ago"
        else:
            return "Just now"
    except:
        return "Unknown"

def calculate_risk_score(amount_usd, from_label, to_label):
    """Simple risk scoring based on amount and known wallets"""
    score = 0
    
    # Amount-based scoring
    if amount_usd > 10000000:  # $10M+
        score += 40
    elif amount_usd > 1000000:  # $1M+
        score += 25
    elif amount_usd > 100000:  # $100K+
        score += 15
    
    # Known wallet scoring
    high_risk_keywords = ["mixer", "tornado", "dark"]
    if from_label:
        if any(keyword in from_label.lower() for keyword in high_risk_keywords):
            score += 50
    if to_label:
        if any(keyword in to_label.lower() for keyword in high_risk_keywords):
            score += 50
    
    return min(score, 100)

async def get_transactions(address, limit=50):
    """Fetch transactions from Etherscan API"""
    api_key = os.getenv("ETHERSCAN_API_KEY")
    if not api_key:
        return {"error": "API key not configured"}
    
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": limit,
        "sort": "desc",
        "apikey": api_key
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
            
            if data.get("status") == "1":
                transactions = []
                for tx in data.get("result", []):
                    # Convert Wei to ETH
                    amount_eth = float(tx.get("value", "0")) / 10**18
                    # Rough USD conversion (ETH price ~$2000)
                    amount_usd = amount_eth * 2000
                    
                    # Get wallet labels
                    from_label = get_wallet_label(tx.get("from", ""))
                    to_label = get_wallet_label(tx.get("to", ""))
                    
                    # Calculate risk score
                    risk_score = calculate_risk_score(amount_usd, from_label, to_label)
                    
                    # Determine risk level
                    if risk_score >= 75:
                        risk_level = "Critical"
                    elif risk_score >= 50:
                        risk_level = "High"
                    elif risk_score >= 25:
                        risk_level = "Medium"
                    else:
                        risk_level = "Low"
                    
                    transactions.append({
                        "hash": tx.get("hash"),
                        "timestamp": tx.get("timeStamp"),
                        "time_ago": format_time_ago(tx.get("timeStamp")),
                        "from_address": tx.get("from"),
                        "to_address": tx.get("to"),
                        "from_label": from_label,
                        "to_label": to_label,
                        "amount_eth": round(amount_eth, 6),
                        "amount_usd": round(amount_usd, 2),
                        "token": "ETH",
                        "risk_score": risk_score,
                        "risk_level": risk_level,
                        "status": "Success" if tx.get("txreceipt_status") == "1" else "Failed"
                    })
                
                return {"transactions": transactions, "total": len(transactions)}
            else:
                return {"error": data.get("message", "API error")}
    
    except Exception as e:
        return {"error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard HTML page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AML Crypto Monitor</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>
    </head>
    <body class="bg-gray-100">
        <div x-data="cryptoMonitor()" x-init="init()">
            <!-- Header -->
            <header class="bg-blue-600 text-white p-6">
                <h1 class="text-3xl font-bold">🛡️ AML Crypto Monitor</h1>
                <p class="text-blue-200">AI-powered crypto transaction analysis</p>
            </header>

            <!-- Input Section -->
            <div class="max-w-6xl mx-auto p-6">
                <div class="bg-white rounded-lg shadow-lg p-6 mb-6">
                    <h2 class="text-xl font-semibold mb-4">Analyze Wallet</h2>
                    <div class="flex gap-4">
                        <input 
                            type="text" 
                            x-model="walletAddress"
                            placeholder="Enter Ethereum wallet address (0x...)"
                            class="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                        >
                        <button 
                            @click="analyzeWallet()" 
                            :disabled="loading || !walletAddress"
                            class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                        >
                            <span x-show="!loading">Analyze</span>
                            <span x-show="loading">Loading...</span>
                        </button>
                    </div>
                </div>

                <!-- Results Table -->
                <div x-show="transactions.length > 0" class="bg-white rounded-lg shadow-lg overflow-hidden">
                    <div class="p-6 border-b">
                        <h3 class="text-lg font-semibold">Transaction History</h3>
                        <p class="text-gray-600" x-text="`Found ${transactions.length} transactions`"></p>
                    </div>
                    
                    <div class="overflow-x-auto">
                        <table class="w-full">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">From</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">To</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Token</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">USD Value</th>
                                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Risk</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-200">
                                <template x-for="tx in transactions" :key="tx.hash">
                                    <tr class="hover:bg-gray-50">
                                        <td class="px-6 py-4 text-sm text-gray-900" x-text="tx.time_ago"></td>
                                        <td class="px-6 py-4">
                                            <div class="text-sm font-medium text-gray-900" x-text="tx.from_label || truncateAddress(tx.from_address)"></div>
                                            <div class="text-sm text-gray-500" x-text="truncateAddress(tx.from_address)"></div>
                                        </td>
                                        <td class="px-6 py-4">
                                            <div class="text-sm font-medium text-gray-900" x-text="tx.to_label || truncateAddress(tx.to_address)"></div>
                                            <div class="text-sm text-gray-500" x-text="truncateAddress(tx.to_address)"></div>
                                        </td>
                                        <td class="px-6 py-4 text-sm text-gray-900" x-text="tx.amount_eth"></td>
                                        <td class="px-6 py-4">
                                            <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800" x-text="tx.token"></span>
                                        </td>
                                        <td class="px-6 py-4 text-sm text-gray-900" x-text="'$' + tx.amount_usd.toLocaleString()"></td>
                                        <td class="px-6 py-4">
                                            <span class="inline-flex px-2 py-1 text-xs font-semibold rounded-full"
                                                  :class="{
                                                      'bg-green-100 text-green-800': tx.risk_level === 'Low',
                                                      'bg-yellow-100 text-yellow-800': tx.risk_level === 'Medium',
                                                      'bg-orange-100 text-orange-800': tx.risk_level === 'High',
                                                      'bg-red-100 text-red-800': tx.risk_level === 'Critical'
                                                  }"
                                                  x-text="tx.risk_level + ' (' + tx.risk_score + ')'">
                                            </span>
                                        </td>
                                    </tr>
                                </template>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Error Message -->
                <div x-show="error" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                    <span x-text="error"></span>
                </div>

                <!-- No Results -->
                <div x-show="!loading && !error && transactions.length === 0 && searched" class="text-center py-8">
                    <p class="text-gray-500">No transactions found. Try analyzing a wallet address.</p>
                </div>
            </div>
        </div>

        <script>
            function cryptoMonitor() {
                return {
                    walletAddress: '',
                    transactions: [],
                    loading: false,
                    error: '',
                    searched: false,

                    init() {
                        // You can pre-fill with a sample address for testing
                        // this.walletAddress = '0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be';
                    },

                    async analyzeWallet() {
                        if (!this.walletAddress) return;
                        
                        this.loading = true;
                        this.error = '';
                        this.searched = true;
                        
                        try {
                            const response = await fetch(`/api/transactions/${this.walletAddress}`);
                            const data = await response.json();
                            
                            if (data.error) {
                                this.error = data.error;
                                this.transactions = [];
                            } else {
                                this.transactions = data.transactions || [];
                                this.error = '';
                            }
                        } catch (err) {
                            this.error = 'Failed to fetch data: ' + err.message;
                            this.transactions = [];
                        } finally {
                            this.loading = false;
                        }
                    },

                    truncateAddress(address) {
                        if (!address) return '';
                        return address.slice(0, 6) + '...' + address.slice(-4);
                    }
                }
            }
        </script>
    </body>
    </html>
    """
    return html

@app.get("/api/transactions/{address}")
async def get_wallet_transactions(address: str):
    """API endpoint to get transactions for a wallet address"""
    return await get_transactions(address)

if __name__ == "__main__":
    print("🛡️  Starting AML Crypto Monitor...")
    print("📊 Dashboard: http://localhost:8000")
    print("🔑 Using Etherscan API key:", os.getenv("ETHERSCAN_API_KEY", "Not configured")[:10] + "...")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)