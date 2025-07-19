#!/usr/bin/env python3
"""
AML Crypto Monitor - Main Application Runner

This script starts the AML Crypto Monitor application with proper configuration
and environment setup.
"""

import os
import sys
import asyncio
import uvicorn
from dotenv import load_dotenv

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

from app.main import app
from app.config import settings


async def check_prerequisites():
    """Check if all prerequisites are met before starting the application."""
    print("🔍 Checking prerequisites...")
    
    # Check if required environment variables are set
    required_vars = []
    missing_vars = []
    
    # Database URL is required
    if not settings.database_url or settings.database_url == "postgresql://user:password@localhost:5432/aml_crypto_monitor":
        missing_vars.append("DATABASE_URL")
    
    # At least one blockchain API key should be configured
    api_keys_configured = 0
    if settings.etherscan_api_key:
        api_keys_configured += 1
    if settings.bsc_scan_api_key:
        api_keys_configured += 1
    if settings.polygonscan_api_key:
        api_keys_configured += 1
    if settings.arbitrum_api_key:
        api_keys_configured += 1
    if settings.optimism_api_key:
        api_keys_configured += 1
    
    if api_keys_configured == 0:
        print("⚠️  Warning: No blockchain API keys configured. Add at least one:")
        print("   - ETHERSCAN_API_KEY")
        print("   - BSC_SCAN_API_KEY") 
        print("   - POLYGONSCAN_API_KEY")
        print("   - ARBITRUM_API_KEY")
        print("   - OPTIMISM_API_KEY")
    else:
        print(f"✅ {api_keys_configured} blockchain API key(s) configured")
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or environment configuration.")
        return False
    
    # Check if Ollama is running (optional but recommended)
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.ollama_host}/api/tags", timeout=5.0)
            if response.status_code == 200:
                print(f"✅ Ollama LLM service is running at {settings.ollama_host}")
            else:
                print(f"⚠️  Ollama LLM service not responding properly at {settings.ollama_host}")
    except Exception as e:
        print(f"⚠️  Could not connect to Ollama LLM service at {settings.ollama_host}")
        print(f"   Error: {str(e)}")
        print("   The application will use fallback risk analysis without AI.")
    
    print("✅ Prerequisites check completed")
    return True


def print_startup_info():
    """Print application startup information."""
    print("\n" + "="*60)
    print("🛡️  AML CRYPTO MONITOR")
    print("="*60)
    print(f"Version: 1.0.0")
    print(f"Environment: {'Development' if settings.debug else 'Production'}")
    print(f"Host: {settings.host}:{settings.port}")
    print(f"Database: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'Local'}")
    print(f"LLM Service: {settings.ollama_host}")
    print(f"Model: {settings.llm_model_name}")
    print("="*60)
    print()


def print_usage_info():
    """Print usage information."""
    print("🚀 AML Crypto Monitor is now running!")
    print()
    print("📊 Dashboard: http://localhost:8000")
    print("🔧 API Docs: http://localhost:8000/docs")
    print("💊 Health Check: http://localhost:8000/health")
    print()
    print("📖 Quick Start:")
    print("1. Open the dashboard in your browser")
    print("2. Enter a wallet address (e.g., 0x...)")
    print("3. Click 'Analyze' to get transaction history and risk analysis")
    print()
    print("💡 Tips:")
    print("- Make sure your API keys are configured in .env")
    print("- Ollama with a suitable model (llama2:7b-chat) is recommended for AI analysis")
    print("- The application stores analyzed data in PostgreSQL for faster subsequent queries")
    print()


async def main():
    """Main application entry point."""
    print_startup_info()
    
    # Check prerequisites
    if not await check_prerequisites():
        print("\n❌ Prerequisites check failed. Please fix the issues above and try again.")
        sys.exit(1)
    
    print_usage_info()
    
    # Start the application
    try:
        config = uvicorn.Config(
            app=app,
            host=settings.host,
            port=settings.port,
            reload=settings.debug,
            workers=1 if settings.debug else settings.workers,
            log_level="debug" if settings.debug else "info",
            access_log=settings.debug
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down AML Crypto Monitor...")
    except Exception as e:
        print(f"\n❌ Failed to start server: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Application error: {str(e)}")
        sys.exit(1)