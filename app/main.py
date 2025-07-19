from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import time
from datetime import datetime
from contextlib import asynccontextmanager

from .config import settings
from .database import init_database, close_database, create_tables, check_database_connection
from .api.routes import router
from .services.blockchain_api import blockchain_service
from .services.llm_service import llm_service

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Application startup time
START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting AML Crypto Monitor...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("Database connection initialized")
        
        # Create tables if they don't exist
        await create_tables()
        logger.info("Database tables ready")
        
        # Check database connection
        db_connected = await check_database_connection()
        if not db_connected:
            logger.error("Database connection failed!")
        else:
            logger.info("Database connection verified")
        
        logger.info("AML Crypto Monitor started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down AML Crypto Monitor...")
    
    try:
        # Close services
        await blockchain_service.close()
        await llm_service.close()
        await close_database()
        
        logger.info("AML Crypto Monitor shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


# Create FastAPI application
app = FastAPI(
    title="AML Crypto Monitor",
    description="AI-powered Anti-Money Laundering monitoring tool for cryptocurrency transactions",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.debug else ["localhost", "127.0.0.1"]
)

# Include routers
app.include_router(router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db_connected = await check_database_connection()
        
        # Check LLM service (simplified check)
        llm_available = True
        try:
            # This is a simple check - in production you might want a more thorough test
            await llm_service._call_ollama("test", system_prompt="respond with 'ok'")
        except Exception:
            llm_available = False
        
        # Check blockchain APIs
        blockchain_apis = []
        from .config import BLOCKCHAIN_CONFIGS
        for network, config in BLOCKCHAIN_CONFIGS.items():
            api_key = blockchain_service.get_api_key(network)
            blockchain_apis.append({
                "network": network,
                "status": "active" if api_key else "no_api_key",
                "api_key_configured": bool(api_key)
            })
        
        # Determine overall status
        if db_connected and llm_available:
            status = "healthy"
        elif db_connected:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "database_connected": db_connected,
            "llm_service_available": llm_available,
            "blockchain_apis": blockchain_apis,
            "uptime_seconds": time.time() - START_TIME,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@app.get("/api/networks")
async def get_supported_networks():
    """Get list of supported blockchain networks."""
    from .config import BLOCKCHAIN_CONFIGS
    
    networks = []
    for network, config in BLOCKCHAIN_CONFIGS.items():
        api_key = blockchain_service.get_api_key(network)
        networks.append({
            "network": network,
            "name": config["name"],
            "native_token": config["native_token"],
            "chain_id": config["chain_id"],
            "api_configured": bool(api_key),
            "status": "active" if api_key else "no_api_key"
        })
    
    return {
        "networks": networks,
        "total_count": len(networks),
        "configured_count": sum(1 for n in networks if n["api_configured"])
    }


@app.get("/api/config")
async def get_configuration():
    """Get current application configuration (non-sensitive data only)."""
    return {
        "debug": settings.debug,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "ollama_host": settings.ollama_host,
        "llm_model_name": settings.llm_model_name,
        "enable_metrics": settings.enable_metrics,
        "version": "1.0.0",
        "supported_networks": list(BLOCKCHAIN_CONFIGS.keys())
    }


# Additional utility endpoints for debugging (only in debug mode)
if settings.debug:
    @app.get("/debug/database-stats")
    async def debug_database_stats():
        """Debug endpoint to check database statistics."""
        from .database import database
        try:
            # Get table counts
            wallet_count = await database.fetch_val("SELECT COUNT(*) FROM wallets")
            transaction_count = await database.fetch_val("SELECT COUNT(*) FROM transactions")
            risk_assessment_count = await database.fetch_val("SELECT COUNT(*) FROM risk_assessments")
            alert_count = await database.fetch_val("SELECT COUNT(*) FROM alerts")
            
            return {
                "wallets": wallet_count,
                "transactions": transaction_count,
                "risk_assessments": risk_assessment_count,
                "alerts": alert_count,
                "database_url": settings.database_url.replace(settings.database_url.split('@')[0].split('://')[1], "***")
            }
        except Exception as e:
            return {"error": str(e)}
    
    @app.post("/debug/test-llm")
    async def debug_test_llm(prompt: str = "What is AML in cryptocurrency?"):
        """Debug endpoint to test LLM service."""
        try:
            response = await llm_service._call_ollama(prompt)
            return {
                "prompt": prompt,
                "response": response,
                "model": settings.llm_model_name,
                "host": settings.ollama_host
            }
        except Exception as e:
            return {"error": str(e), "prompt": prompt}


def create_app():
    """Factory function to create the FastAPI app."""
    return app


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        workers=1 if settings.debug else settings.workers,
        log_level="debug" if settings.debug else "info"
    )