#!/usr/bin/env python3
"""
Quick AML Crypto Transaction Monitor
Simple version using requests instead of httpx
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

# Load environment variables
load_dotenv()

app = FastAPI()

def get_transactions_sync(address, limit=20):
    """Fetch transactions from Etherscan API - synchronous version"""
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
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "1":
            transactions = []
            for tx in data.get("result", []):
                # Convert Wei to ETH
                amount_eth = float(tx.get("value", "0")) / 10**18
                amount_usd = amount_eth * 2000  # Rough USD conversion
                
                # Simple time format
                try:
                    timestamp = int(tx.get("timeStamp", 0))
                    tx_time = datetime.fromtimestamp(timestamp)
                    time_ago = tx_time.strftime("%Y-%m-%d %H:%M")
                except:
                    time_ago = "Unknown"
                
                transactions.append({
                    "hash": tx.get("hash", "")[:10] + "...",
                    "time_ago": time_ago,
                    "from_address": tx.get("from", "")[:6] + "..." + tx.get("from", "")[-4:],
                    "to_address": tx.get("to", "")[:6] + "..." + tx.get("to", "")[-4:],
                    "amount_eth": round(amount_eth, 6),
                    "amount_usd": round(amount_usd, 2),
                    "token": "ETH"
                })
            
            return {"transactions": transactions, "total": len(transactions)}
        else:
            return {"error": data.get("message", "API error")}
    
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

@app.get("/")
def dashboard():
    """Main dashboard"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AML Crypto Monitor</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #333; text-align: center; }}
            .input-section {{ margin: 20px 0; padding: 20px; background: #f9f9f9; border-radius: 8px; }}
            input {{ width: 70%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }}
            button {{ padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }}
            button:hover {{ background: #0056b3; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; font-weight: bold; }}
            .error {{ color: red; padding: 10px; background: #ffe6e6; border-radius: 4px; margin: 10px 0; }}
            .success {{ color: green; padding: 10px; background: #e6ffe6; border-radius: 4px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ AML Crypto Monitor</h1>
            <p style="text-align: center; color: #666;">Using API Key: {os.getenv("ETHERSCAN_API_KEY", "Not set")[:10]}...</p>
            
            <div class="input-section">
                <h3>Analyze Wallet</h3>
                <form method="get" action="/analyze">
                    <input type="text" name="address" placeholder="Enter Ethereum wallet address (0x...)" required>
                    <button type="submit">Analyze</button>
                </form>
                <p><small>Example: 0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be (Binance Hot Wallet)</small></p>
            </div>
            
            <div id="results">
                <p>Enter a wallet address above to see transaction history.</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@app.get("/analyze")
def analyze_wallet(address: str = ""):
    """Analyze wallet endpoint"""
    if not address:
        return HTMLResponse(content="<p class='error'>Please provide a wallet address</p>")
    
    # Get transaction data
    result = get_transactions_sync(address)
    
    html_start = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AML Crypto Monitor - Results</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
            h1 {{ color: #333; text-align: center; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; font-weight: bold; }}
            .error {{ color: red; padding: 10px; background: #ffe6e6; border-radius: 4px; margin: 10px 0; }}
            .success {{ color: green; padding: 10px; background: #e6ffe6; border-radius: 4px; margin: 10px 0; }}
            .back {{ margin: 20px 0; }}
            .back a {{ color: #007bff; text-decoration: none; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ AML Crypto Monitor - Results</h1>
            <div class="back"><a href="/">← Back to Dashboard</a></div>
            <h3>Analysis for: {address[:10]}...{address[-8:]}</h3>
    """
    
    if "error" in result:
        html_content = f"""
            <div class="error">Error: {result['error']}</div>
            <p>Please check the wallet address and try again.</p>
        """
    else:
        transactions = result.get("transactions", [])
        if not transactions:
            html_content = """
                <div class="success">No transactions found for this address.</div>
            """
        else:
            html_content = f"""
                <div class="success">Found {len(transactions)} transactions</div>
                <table>
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>From</th>
                            <th>To</th>
                            <th>Amount (ETH)</th>
                            <th>Token</th>
                            <th>USD Value</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            
            for tx in transactions:
                html_content += f"""
                        <tr>
                            <td>{tx['time_ago']}</td>
                            <td>{tx['from_address']}</td>
                            <td>{tx['to_address']}</td>
                            <td>{tx['amount_eth']}</td>
                            <td>{tx['token']}</td>
                            <td>${tx['amount_usd']:,.2f}</td>
                        </tr>
                """
            
            html_content += """
                    </tbody>
                </table>
            """
    
    html_end = """
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_start + html_content + html_end)

if __name__ == "__main__":
    print("🛡️  Starting Simple AML Crypto Monitor...")
    print("📊 Dashboard: http://localhost:8000")
    api_key = os.getenv("ETHERSCAN_API_KEY", "Not configured")
    print(f"🔑 API Key: {api_key[:10]}..." if api_key != "Not configured" else "🔑 API Key: Not configured")
    print("✅ Ready to analyze crypto transactions!")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")