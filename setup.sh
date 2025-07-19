#!/bin/bash

# AML Crypto Monitor Setup Script
# This script helps set up the AML Crypto Monitor application

set -e

echo "🛡️  AML Crypto Monitor Setup"
echo "================================"
echo ""

# Check if Python 3.8+ is available
if ! python3 --version | grep -E "Python 3\.(8|9|10|11|12)" > /dev/null; then
    echo "❌ Python 3.8+ is required but not found"
    echo "Please install Python 3.8 or later and try again"
    exit 1
fi

echo "✅ Python version check passed"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is not available"
    echo "Please install pip3 and try again"
    exit 1
fi

echo "✅ pip3 is available"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before running the application"
else
    echo "✅ .env file already exists"
fi

# Check if PostgreSQL is running
if command -v systemctl &> /dev/null; then
    if systemctl is-active --quiet postgresql; then
        echo "✅ PostgreSQL is running"
    else
        echo "⚠️  PostgreSQL is not running. Please start it:"
        echo "   sudo systemctl start postgresql"
    fi
elif command -v pg_isready &> /dev/null; then
    if pg_isready -q; then
        echo "✅ PostgreSQL is running"
    else
        echo "⚠️  PostgreSQL is not running. Please start it manually"
    fi
else
    echo "⚠️  Cannot check PostgreSQL status. Please ensure it's installed and running"
fi

# Check if Ollama is available
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is installed"
    
    # Check if llama2:7b-chat model is available
    if ollama list | grep -q "llama2:7b-chat"; then
        echo "✅ llama2:7b-chat model is available"
    else
        echo "📥 Downloading llama2:7b-chat model (this may take a while)..."
        ollama pull llama2:7b-chat
    fi
else
    echo "⚠️  Ollama is not installed. To install:"
    echo "   curl -fsSL https://ollama.ai/install.sh | sh"
    echo "   ollama pull llama2:7b-chat"
fi

echo ""
echo "🎉 Setup completed!"
echo ""
echo "Next steps:"
echo "1. Configure your .env file with API keys and database connection"
echo "2. Create the PostgreSQL database:"
echo "   createdb aml_crypto_monitor"
echo "3. Start the application:"
echo "   python run.py"
echo ""
echo "📚 For more information, see README.md"