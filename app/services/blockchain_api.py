import httpx
import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import time
import json
from ..config import settings, BLOCKCHAIN_CONFIGS, KNOWN_WALLET_LABELS
from ..models import Transaction, Wallet
import logging

logger = logging.getLogger(__name__)


class BlockchainAPIService:
    def __init__(self):
        self.session = httpx.AsyncClient(timeout=30.0)
        self.rate_limits = {}  # Track rate limits per API
        
    async def close(self):
        """Close the HTTP session."""
        await self.session.aclose()
    
    def get_api_key(self, network: str) -> Optional[str]:
        """Get API key for a specific network."""
        config = BLOCKCHAIN_CONFIGS.get(network)
        if not config:
            return None
        
        api_key_field = config.get("api_key_field")
        return getattr(settings, api_key_field, None)
    
    async def _make_request(self, url: str, params: Dict[str, Any], network: str) -> Optional[Dict]:
        """Make HTTP request with rate limiting and error handling."""
        # Check rate limiting
        current_time = time.time()
        if network in self.rate_limits:
            last_request, request_count = self.rate_limits[network]
            if current_time - last_request < 60:  # Within 1 minute
                if request_count >= settings.rate_limit_per_minute:
                    logger.warning(f"Rate limit reached for {network}. Waiting...")
                    await asyncio.sleep(60 - (current_time - last_request))
                    self.rate_limits[network] = (current_time, 1)
                else:
                    self.rate_limits[network] = (last_request, request_count + 1)
            else:
                self.rate_limits[network] = (current_time, 1)
        else:
            self.rate_limits[network] = (current_time, 1)
        
        try:
            response = await self.session.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Check for API-specific error responses
            if data.get("status") == "0" and "error" in data.get("message", "").lower():
                logger.error(f"API error for {network}: {data.get('message')}")
                return None
            
            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error for {network}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Request error for {network}: {str(e)}")
            return None
    
    async def get_wallet_transactions(
        self, 
        address: str, 
        network: str, 
        start_block: int = 0, 
        end_block: int = 99999999,
        page: int = 1,
        offset: int = 100
    ) -> List[Dict]:
        """Get transaction history for a wallet address."""
        config = BLOCKCHAIN_CONFIGS.get(network)
        if not config:
            logger.error(f"Unsupported network: {network}")
            return []
        
        api_key = self.get_api_key(network)
        if not api_key:
            logger.error(f"No API key configured for {network}")
            return []
        
        # Get normal transactions
        normal_txs = await self._get_normal_transactions(
            address, network, config, api_key, start_block, end_block, page, offset
        )
        
        # Get internal transactions
        internal_txs = await self._get_internal_transactions(
            address, network, config, api_key, start_block, end_block, page, offset
        )
        
        # Get ERC-20 token transfers
        token_txs = await self._get_token_transactions(
            address, network, config, api_key, start_block, end_block, page, offset
        )
        
        # Combine and sort all transactions
        all_transactions = normal_txs + internal_txs + token_txs
        all_transactions.sort(key=lambda x: int(x.get("timeStamp", 0)), reverse=True)
        
        return all_transactions
    
    async def _get_normal_transactions(
        self, address: str, network: str, config: Dict, api_key: str,
        start_block: int, end_block: int, page: int, offset: int
    ) -> List[Dict]:
        """Get normal transactions."""
        params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": "desc",
            "apikey": api_key
        }
        
        data = await self._make_request(config["api_url"], params, network)
        if data and data.get("status") == "1":
            return data.get("result", [])
        return []
    
    async def _get_internal_transactions(
        self, address: str, network: str, config: Dict, api_key: str,
        start_block: int, end_block: int, page: int, offset: int
    ) -> List[Dict]:
        """Get internal transactions."""
        params = {
            "module": "account",
            "action": "txlistinternal",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": "desc",
            "apikey": api_key
        }
        
        data = await self._make_request(config["api_url"], params, network)
        if data and data.get("status") == "1":
            # Mark as internal transactions
            result = data.get("result", [])
            for tx in result:
                tx["type"] = "internal"
            return result
        return []
    
    async def _get_token_transactions(
        self, address: str, network: str, config: Dict, api_key: str,
        start_block: int, end_block: int, page: int, offset: int
    ) -> List[Dict]:
        """Get ERC-20 token transactions."""
        params = {
            "module": "account",
            "action": "tokentx",
            "address": address,
            "startblock": start_block,
            "endblock": end_block,
            "page": page,
            "offset": offset,
            "sort": "desc",
            "apikey": api_key
        }
        
        data = await self._make_request(config["api_url"], params, network)
        if data and data.get("status") == "1":
            # Mark as token transactions
            result = data.get("result", [])
            for tx in result:
                tx["type"] = "token"
            return result
        return []
    
    async def get_wallet_balance(self, address: str, network: str) -> Optional[Dict]:
        """Get wallet balance for native token."""
        config = BLOCKCHAIN_CONFIGS.get(network)
        if not config:
            return None
        
        api_key = self.get_api_key(network)
        if not api_key:
            return None
        
        params = {
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": api_key
        }
        
        data = await self._make_request(config["api_url"], params, network)
        if data and data.get("status") == "1":
            balance_wei = int(data.get("result", "0"))
            balance_eth = balance_wei / 10**18  # Convert from wei to eth
            
            return {
                "balance": balance_eth,
                "balance_wei": balance_wei,
                "token_symbol": config["native_token"],
                "network": network
            }
        return None
    
    async def get_token_balances(self, address: str, network: str) -> List[Dict]:
        """Get ERC-20 token balances for a wallet."""
        # This would require additional API calls or using services like Moralis/Alchemy
        # For now, we'll return empty list and implement later
        return []
    
    def get_wallet_label(self, address: str) -> Optional[str]:
        """Get known label for a wallet address."""
        return KNOWN_WALLET_LABELS.get(address.lower())
    
    def parse_transaction(self, tx_data: Dict, network: str) -> Dict:
        """Parse raw transaction data into standardized format."""
        # Convert timestamp
        timestamp = datetime.fromtimestamp(int(tx_data.get("timeStamp", 0)))
        
        # Determine transaction type
        tx_type = tx_data.get("type", "normal")
        if tx_data.get("functionName"):
            tx_type = "contract"
        elif tx_data.get("tokenSymbol"):
            tx_type = "token"
        
        # Calculate amount
        value = tx_data.get("value", "0")
        if tx_type == "token":
            decimals = int(tx_data.get("tokenDecimal", 18))
            amount = float(value) / (10 ** decimals)
            token_symbol = tx_data.get("tokenSymbol", "UNKNOWN")
            token_address = tx_data.get("contractAddress")
        else:
            amount = float(value) / (10 ** 18)  # Wei to ETH conversion
            token_symbol = BLOCKCHAIN_CONFIGS[network]["native_token"]
            token_address = None
        
        # Get wallet labels
        from_label = self.get_wallet_label(tx_data.get("from", ""))
        to_label = self.get_wallet_label(tx_data.get("to", ""))
        
        return {
            "hash": tx_data.get("hash"),
            "network": network,
            "block_number": int(tx_data.get("blockNumber", 0)),
            "timestamp": timestamp,
            "from_address": tx_data.get("from", "").lower(),
            "to_address": tx_data.get("to", "").lower(),
            "from_label": from_label,
            "to_label": to_label,
            "amount": amount,
            "amount_raw": value,
            "token_symbol": token_symbol,
            "token_address": token_address,
            "token_name": tx_data.get("tokenName"),
            "token_decimals": int(tx_data.get("tokenDecimal", 18)) if tx_type == "token" else None,
            "gas_used": int(tx_data.get("gasUsed", 0)),
            "gas_price": tx_data.get("gasPrice", "0"),
            "status": "success" if tx_data.get("txreceipt_status") == "1" else "failed",
            "transaction_type": tx_type,
            "function_name": tx_data.get("functionName"),
            "is_error": tx_data.get("isError") == "1"
        }
    
    async def get_multiple_wallet_transactions(
        self, 
        addresses: List[str], 
        networks: List[str] = None
    ) -> Dict[str, List[Dict]]:
        """Get transactions for multiple wallets across multiple networks."""
        if networks is None:
            networks = list(BLOCKCHAIN_CONFIGS.keys())
        
        results = {}
        tasks = []
        
        for address in addresses:
            for network in networks:
                task = self.get_wallet_transactions(address, network)
                tasks.append((address, network, task))
        
        # Execute all tasks concurrently
        for address, network, task in tasks:
            try:
                transactions = await task
                key = f"{address}_{network}"
                results[key] = [self.parse_transaction(tx, network) for tx in transactions]
            except Exception as e:
                logger.error(f"Failed to get transactions for {address} on {network}: {str(e)}")
                results[f"{address}_{network}"] = []
        
        return results


# Global instance
blockchain_service = BlockchainAPIService()