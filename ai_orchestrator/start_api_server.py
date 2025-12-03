"""
Start the REST API server for AI Orchestrator
"""

import os
import sys
import logging
from dotenv import load_dotenv
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/ai_orchestrator_api.log', mode='a')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Start the API server"""
    load_dotenv()
    
    # Get configuration from environment
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', '8000'))
    reload = os.getenv('API_RELOAD', 'false').lower() == 'true'
    
    logger.info(f"🚀 Starting AI Orchestrator REST API")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Reload: {reload}")
    
    try:
        uvicorn.run(
            "server.api.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"💥 Failed to start API server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

