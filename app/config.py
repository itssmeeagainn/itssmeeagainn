from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/aml_crypto_monitor"
    
    # API Keys
    etherscan_api_key: Optional[str] = None
    bsc_scan_api_key: Optional[str] = None
    polygonscan_api_key: Optional[str] = None
    ftmscan_api_key: Optional[str] = None
    arbitrum_api_key: Optional[str] = None
    optimism_api_key: Optional[str] = None
    solana_rpc_url: str = "https://api.mainnet-beta.solana.com"
    
    # LLM Configuration
    ollama_host: str = "http://localhost:11434"
    llm_model_name: str = "llama2:7b-chat"
    openai_api_key: Optional[str] = None
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Security
    secret_key: str = "your-super-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Application
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    
    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 8001
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Blockchain network configurations
BLOCKCHAIN_CONFIGS = {
    "ethereum": {
        "name": "Ethereum",
        "api_url": "https://api.etherscan.io/api",
        "api_key_field": "etherscan_api_key",
        "native_token": "ETH",
        "chain_id": 1
    },
    "bsc": {
        "name": "Binance Smart Chain",
        "api_url": "https://api.bscscan.com/api",
        "api_key_field": "bsc_scan_api_key",
        "native_token": "BNB",
        "chain_id": 56
    },
    "polygon": {
        "name": "Polygon",
        "api_url": "https://api.polygonscan.com/api",
        "api_key_field": "polygonscan_api_key",
        "native_token": "MATIC",
        "chain_id": 137
    },
    "fantom": {
        "name": "Fantom",
        "api_url": "https://api.ftmscan.com/api",
        "api_key_field": "ftmscan_api_key",
        "native_token": "FTM",
        "chain_id": 250
    },
    "arbitrum": {
        "name": "Arbitrum",
        "api_url": "https://api.arbiscan.io/api",
        "api_key_field": "arbitrum_api_key",
        "native_token": "ETH",
        "chain_id": 42161
    },
    "optimism": {
        "name": "Optimism",
        "api_url": "https://api-optimistic.etherscan.io/api",
        "api_key_field": "optimism_api_key",
        "native_token": "ETH",
        "chain_id": 10
    }
}

# Known wallet labels for AML identification
KNOWN_WALLET_LABELS = {
    # Exchanges
    "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be": "Binance Hot Wallet",
    "0xd551234ae421e3bcba99a0da6d736074f22192ff": "Binance Hot Wallet 2",
    "0x564286362092d8e7936f0549571a803b203aaced": "Binance Hot Wallet 3",
    "0x0681d8db095565fe8a346fa0277bffde9c0edbbf": "Binance Hot Wallet 4",
    "0xfe9e8709d3215310075d67e3ed32a380ccf451c8": "Coinbase Hot Wallet",
    "0xa090e606e30bd747d4e6245a1517ebe430f0057e": "Coinbase Hot Wallet 2",
    "0x503828976d22510aad0201ac7ec88293211d23da": "Coinbase Hot Wallet 3",
    "0xddfabcdc4d8ffc6d5beaf154f18b778f892a0740": "Coinbase Hot Wallet 4",
    "0x1522900b6dafac587d499a862861c0869be6e428": "KuCoin Hot Wallet",
    "0xd6216fc19db775df9774a6e33526131da7d19a2c": "KuCoin Hot Wallet 2",
    "0x2b5634c42055806a59e9107ed44d43c426e58258": "KuCoin Hot Wallet 3",
    "0xa1d8d972560c2f8144af871db508f0b0b10a3fbf": "Kraken Hot Wallet",
    "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13": "Kraken Hot Wallet 2",
    "0xe853c56864a2ebe4576a807d26fdc4a0ada51919": "Kraken Hot Wallet 3",
    
    # Bridges & DEX
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": "Uniswap V3 Router",
    "0x7a250d5630b4cf539739df2c5dacb4c659f2488d": "Uniswap V2 Router",
    "0x1111111254eeb25477b68fb85ed929f73a960582": "1inch Router",
    "0x881d40237659c251811cec9c364ef91dc08d300c": "Metamask Swap Router",
    
    # Others
    "0x47ac0fb4f2d84898e4d9e7b4dab3c24507a6d503": "ChangeNOW",
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "Kraken Exchange",
    "0x6262998ced04146fa42253a5c0af90ca02dfd2a3": "Crypto.com Exchange"
}

# Risk scoring thresholds
RISK_THRESHOLDS = {
    "low": 25,
    "medium": 50,
    "high": 75,
    "critical": 90
}

# Transaction amount thresholds for monitoring (in USD)
AMOUNT_THRESHOLDS = {
    "large": 100000,  # $100K
    "very_large": 1000000,  # $1M
    "whale": 10000000  # $10M
}