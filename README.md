# AML Crypto Monitor 🛡️

An AI-powered Anti-Money Laundering (AML) monitoring tool for cryptocurrency transactions that integrates with your local LLM for intelligent risk analysis.

## Features

- **Multi-Chain Support**: Monitor transactions across Ethereum, BSC, Polygon, Arbitrum, Optimism, and more
- **AI-Powered Analysis**: Integrates with local LLM (Ollama) for intelligent transaction risk assessment
- **Real-time Dashboard**: Modern web interface showing transaction history, wallet labels, and risk scores
- **Comprehensive API**: RESTful API for integration with other systems
- **Risk Scoring**: Advanced risk assessment using both rule-based and AI-driven methods
- **Known Entity Detection**: Identifies exchanges, mixers, and other known services
- **Transaction Patterns**: Detects suspicious patterns like structuring and rapid movement

## Dashboard Output

The dashboard displays transaction data in an easy-to-read format with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| **Time** | Relative timestamp | "6 months ago" |
| **From** | Source wallet with label | "Binance Hot Wallet" or "0x1234...5678" |
| **To** | Destination wallet with label | "ChangeNOW" or "0xabcd...efgh" |
| **Amount** | Transaction amount | "1,500.50" |
| **Token** | Token symbol | "ETH", "BNB", "USDT" |
| **USD Value** | USD equivalent | "$3,250,000" |
| **Risk** | Risk level with score | "High (75)" |

## Quick Start

### Prerequisites

1. **Python 3.8+**
2. **PostgreSQL** (for data storage)
3. **Ollama** (for local LLM) - Optional but recommended
4. **Blockchain API Keys** (at least one)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd aml-crypto-monitor
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Setup environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Configure your .env file**
```bash
# Database (Required)
DATABASE_URL=postgresql://user:password@localhost:5432/aml_crypto_monitor

# Blockchain API Keys (At least one required)
ETHERSCAN_API_KEY=your_etherscan_api_key_here
BSC_SCAN_API_KEY=your_bscscan_api_key_here
POLYGONSCAN_API_KEY=your_polygonscan_api_key_here

# Local LLM Configuration (Optional)
OLLAMA_HOST=http://localhost:11434
LLM_MODEL_NAME=llama2:7b-chat
```

5. **Setup PostgreSQL database**
```sql
CREATE DATABASE aml_crypto_monitor;
CREATE USER aml_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE aml_crypto_monitor TO aml_user;
```

6. **Setup Ollama (Optional but recommended)**
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Download a suitable model
ollama pull llama2:7b-chat
```

7. **Start the application**
```bash
python run.py
```

### Getting API Keys

To get blockchain API keys (free):

- **Etherscan**: https://etherscan.io/apis
- **BSCscan**: https://bscscan.com/apis  
- **Polygonscan**: https://polygonscan.com/apis
- **Arbiscan**: https://arbiscan.io/apis
- **Optimistic Etherscan**: https://optimistic.etherscan.io/apis

## Usage

### Web Dashboard

1. Open http://localhost:8000 in your browser
2. Enter a wallet address in the input field
3. Select a network (or leave as "All Networks")
4. Click "Analyze" to fetch and analyze transactions
5. View the results in the transaction table below

### API Usage

**Analyze a wallet:**
```bash
curl -X POST "http://localhost:8000/api/wallet/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "address": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
    "networks": ["ethereum", "bsc"],
    "limit": 50,
    "analyze_risk": true
  }'
```

**Get transaction history:**
```bash
curl "http://localhost:8000/api/transactions?wallet_address=0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be&limit=100"
```

**Get dashboard statistics:**
```bash
curl "http://localhost:8000/api/dashboard/stats"
```

## Local LLM Integration

The tool is designed to work with a local LLM for privacy and security. It uses Ollama to run models locally.

### Fine-tuning for AML

To improve AML detection accuracy, you can fine-tune the model with AML-specific datasets:

1. **Prepare training data** with known AML cases and patterns
2. **Use the Ollama fine-tuning capabilities** or export to other fine-tuning frameworks
3. **Update the model name** in your configuration

### Supported Models

- **llama2:7b-chat** (Default, good balance of speed and accuracy)
- **llama2:13b-chat** (Better accuracy, slower)
- **mistral:7b** (Fast alternative)
- **codellama:7b** (Good for structured analysis)

## Configuration

### Risk Thresholds

Risk levels are determined by scores:
- **Low**: 0-24
- **Medium**: 25-49  
- **High**: 50-74
- **Critical**: 75-100

### Amount Thresholds

Transaction monitoring thresholds:
- **Large**: $100,000+
- **Very Large**: $1,000,000+
- **Whale**: $10,000,000+

### Known Wallet Labels

The system includes a database of known wallets:
- Exchange hot wallets (Binance, Coinbase, Kraken, etc.)
- DEX routers (Uniswap, 1inch, etc.)
- Bridges and cross-chain services
- Known mixing services
- Sanctioned addresses

## API Endpoints

### Core Endpoints

- `GET /` - Web dashboard
- `POST /api/wallet/analyze` - Analyze wallet transactions
- `GET /api/transactions` - Get transactions with filters
- `GET /api/wallets` - Get wallets with filters
- `GET /api/dashboard/stats` - Dashboard statistics

### Utility Endpoints

- `GET /health` - Health check
- `GET /api/networks` - Supported networks
- `GET /api/config` - Configuration info

### Debug Endpoints (Development only)

- `GET /debug/database-stats` - Database statistics
- `POST /debug/test-llm` - Test LLM service

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   FastAPI App   │    │   PostgreSQL    │
│   (Frontend)    │◄──►│   (Backend)     │◄──►│   (Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Blockchain APIs │
                       │ (Etherscan,etc) │
                       └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Local LLM       │
                       │ (Ollama)        │
                       └─────────────────┘
```

## Security Considerations

- **API Keys**: Store securely and use read-only permissions
- **Database**: Use strong passwords and limit network access
- **Local LLM**: Keeps sensitive data on your infrastructure
- **Rate Limiting**: Built-in rate limiting for API calls
- **Input Validation**: All inputs are validated and sanitized

## Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Check connection string in .env
DATABASE_URL=postgresql://user:password@localhost:5432/aml_crypto_monitor
```

**API Key Issues**
```bash
# Test API key manually
curl "https://api.etherscan.io/api?module=stats&action=ethsupply&apikey=YOUR_API_KEY"
```

**Ollama Connection Error**
```bash
# Check if Ollama is running
ollama list

# Test connection
curl http://localhost:11434/api/tags
```

**No Transactions Found**
- Verify the wallet address format
- Check if the address has transactions on the selected network
- Ensure API keys are configured for the network

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please:
1. Check the troubleshooting section above
2. Review the API documentation at `/docs`
3. Open an issue on GitHub

## Disclaimer

This tool is for educational and compliance purposes. Always verify results with additional analysis and consult with compliance professionals for production use.
