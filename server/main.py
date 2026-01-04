import asyncio
import logging
import os
import sys

from grpc import aio
from dotenv import load_dotenv

from .interceptors import LoggingInterceptor
from .chat_handler import EnhancedChatHandler
from .config import get_config
from .health import get_health_checker
from .metrics import get_metrics
from .exceptions import ConfigurationError, log_exception
from .sentry_integration import init_sentry

# Import generated protobuf files
import chat_service_pb2_grpc

# Module-level logger for use before logging is fully configured
logger = logging.getLogger(__name__)


def setup_logging(log_level: str, environment: str):
    """Setup comprehensive logging (optional - controlled by LOGGING_ENABLED env var)"""
    # Check if logging is enabled
    logging_enabled = os.getenv("LOGGING_ENABLED", "true").lower() in ("true", "1", "yes")

    if not logging_enabled:
        # Disable all logging
        logging.disable(logging.CRITICAL)
        return

    log_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s'

    handlers = [logging.StreamHandler()]  # Console output

    # Add file logging if enabled
    log_file = os.getenv("LOGGING_FILE")
    if log_file:
        handlers.append(logging.FileHandler(log_file, mode='a'))
    elif environment != 'production':
        # Default file logging in non-production environments
        handlers.append(logging.FileHandler('/tmp/ai_orchestrator.log', mode='a'))

    logging.basicConfig(
        level=getattr(logging, log_level),
        format=log_format,
        handlers=handlers
    )

    # Set specific log levels for different components
    logging.getLogger('httpx').setLevel(logging.INFO)
    logging.getLogger('openai').setLevel(logging.INFO)
    logging.getLogger('grpc').setLevel(logging.INFO)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"✅ Logging configured for {environment} environment")

async def serve():
    """Start the gRPC server"""
    logger = logging.getLogger(__name__)
    logger.info("🚀 Starting AI Orchestrator server...")

    try:
        # Load and validate configuration
        config = get_config()
        config.log_config()

        # Setup logging with configuration
        setup_logging(config.server.log_level, config.server.environment)
        logger = logging.getLogger(__name__)

        # Initialize Sentry for error tracking
        init_sentry(
            environment=config.server.environment,
            traces_sample_rate=0.1 if config.server.environment == "production" else 1.0,
        )

        logger.info(f"✅ Configuration loaded for {config.server.environment} environment")

    except ConfigurationError as e:
        logger.error(f"❌ Configuration error: {e.message}")
        log_exception(e, "configuration_loading")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {str(e)}")
        log_exception(e, "configuration_loading")
        sys.exit(1)
    
    # Create interceptors
    logging_interceptor = LoggingInterceptor()

    # Create server with interceptors
    server = aio.server(
        interceptors=[logging_interceptor]
    )

    # Add servicer with enhanced features
    logger.info("🚀 Initializing Enhanced ChatHandler with agent tools and context storage")
    chat_handler = EnhancedChatHandler()

    # Setup enhanced features
    try:
        await chat_handler.setup_storage()
        logger.info("✅ Chat storage setup completed")
    except Exception as e:
        logger.warning(f"⚠️ Chat storage setup failed, continuing anyway: {e}")
        log_exception(e, "chat_storage_setup")

    chat_service_pb2_grpc.add_AiOrchestratorServicer_to_server(chat_handler, server)

    # Bind to port
    listen_addr = f'[::]:{config.server.port}'
    server.add_insecure_port(listen_addr)

    # Initialize health checker and metrics
    health_checker = get_health_checker()
    metrics = get_metrics()

    # Start server
    logger.info(f"🎯 Server listening on {listen_addr}")
    logger.info(f"🔗 Java gRPC target: {config.api.java_grpc_target}")
    logger.info(f"🔍 Search provider: {config.api.search_provider}")
    logger.info(f"📍 Default city: {config.api.default_city}")
    logger.info(f"🤖 Chat mode: Enhanced with Agent Tools")
    
    await server.start()
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        if hasattr(chat_handler, 'cleanup'):
            logger.info("🧹 Cleaning up resources...")
            await chat_handler.cleanup()
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
                logger.debug("✅ Using uvloop for enhanced performance")
            except ImportError:
                logger.debug("ℹ️ uvloop not available, using default asyncio")
                pass
        
        asyncio.run(serve())
    except Exception as e:
        logger.error(f"💥 Server failed to start: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()