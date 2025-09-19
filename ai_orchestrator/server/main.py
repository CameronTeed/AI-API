import asyncio
import logging
import os
import sys
from concurrent import futures

import grpc
from grpc import aio
from dotenv import load_dotenv

from .interceptors import AuthInterceptor, LoggingInterceptor
from .chat_handler import ChatHandler

# Import generated protobuf files
import chat_service_pb2_grpc

# Configure comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('/tmp/ai_orchestrator.log', mode='a')  # File output
    ]
)

# Set specific log levels for different components
logging.getLogger('httpx').setLevel(logging.DEBUG)
logging.getLogger('openai').setLevel(logging.DEBUG)
logging.getLogger('grpc').setLevel(logging.DEBUG)
logging.getLogger('sentence_transformers').setLevel(logging.INFO)  # Keep this less verbose

logger = logging.getLogger(__name__)
logger.debug("🔧 Logging configuration initialized")

async def serve():
    """Start the gRPC server"""
    logger.debug("🚀 Starting serve() function")
    load_dotenv()
    logger.debug("📄 Environment variables loaded")
    
    # Get configuration from environment
    port = int(os.getenv('PORT', '7000'))
    bearer_token = os.getenv('AI_BEARER_TOKEN', 'your_bearer_token_here')
    java_target = os.getenv('JAVA_GRPC_TARGET', 'localhost:8081')
    search_provider = os.getenv('SEARCH_PROVIDER', 'none')
    default_city = os.getenv('DEFAULT_CITY', 'Ottawa')
    
    logger.debug(f"⚙️  Configuration loaded:")
    logger.debug(f"   - Port: {port}")
    logger.debug(f"   - Bearer token: {bearer_token[:10]}..." if len(bearer_token) > 10 else f"   - Bearer token: {bearer_token}")
    logger.debug(f"   - Java target: {java_target}")
    logger.debug(f"   - Search provider: {search_provider}")
    logger.debug(f"   - Default city: {default_city}")
    
    # Validate required environment variables
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    # Create interceptors
    # auth_interceptor = AuthInterceptor(bearer_token)  # Disable auth for now
    logging_interceptor = LoggingInterceptor()
    
    # Create server with interceptors
    server = aio.server(
        interceptors=[logging_interceptor]  # Only logging for now
    )
    
    # Add servicer
    chat_handler = ChatHandler()
    chat_service_pb2_grpc.add_AiOrchestratorServicer_to_server(chat_handler, server)
    
    # Bind to port
    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)
    
    # Start server
    logger.info(f"Starting AI Orchestrator server on {listen_addr}")
    logger.info(f"Java gRPC target: {os.getenv('JAVA_GRPC_TARGET', 'localhost:9090')}")
    logger.info(f"Search provider: {os.getenv('SEARCH_PROVIDER', 'serpapi')}")
    logger.info(f"Default city: {os.getenv('DEFAULT_CITY', 'Ottawa')}")
    
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        await server.stop(5)

def main():
    """Main entry point"""
    try:
        if sys.platform == 'win32':
            # Windows specific event loop policy
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        else:
            # Use uvloop on Unix systems if available
            try:
                import uvloop
                uvloop.install()
            except ImportError:
                pass
        
        asyncio.run(serve())
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
