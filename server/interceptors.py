import grpc
import logging
from grpc import aio

logger = logging.getLogger(__name__)

class AuthInterceptor(grpc.aio.ServerInterceptor):
    """gRPC interceptor for bearer token authentication"""
    
    def __init__(self, required_token: str):
        self.required_token = required_token

    async def intercept_service(self, continuation, handler_call_details):
        """Intercept and authenticate requests"""
        
        logger.debug(f"🔐 Auth interceptor called for: {handler_call_details.method}")
        
        # Get metadata from the request
        metadata = dict(handler_call_details.invocation_metadata)
        logger.debug(f"📨 Request metadata keys: {list(metadata.keys())}")
        
        # Check for authorization header
        auth_header = metadata.get('authorization', '')
        logger.debug(f"🔑 Authorization header: '{auth_header[:20]}...'" if len(auth_header) > 20 else f"🔑 Authorization header: '{auth_header}'")
        
        if not auth_header.startswith('Bearer '):
            logger.warning(f"❌ Missing or invalid authorization header from {handler_call_details.method}")
            # Create a proper RPC error response
            def abort_handler(request, context):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "Missing or invalid authorization header")
            return grpc.aio.unary_unary_rpc_method_handler(abort_handler)
        
        # Extract token
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        logger.debug(f"🎫 Extracted token: '{token[:10]}...'" if len(token) > 10 else f"🎫 Extracted token: '{token}'")
        
        if token != self.required_token:
            logger.warning(f"❌ Invalid token from {handler_call_details.method}")
            # Create a proper RPC error response
            def abort_handler(request, context):
                context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid token")
            return grpc.aio.unary_unary_rpc_method_handler(abort_handler)
        
        logger.debug(f"✅ Authentication successful for {handler_call_details.method}")
        # Token is valid, continue with the request
        logger.info(f"Authenticated request to {handler_call_details.method}")
        return await continuation(handler_call_details)

class LoggingInterceptor(grpc.aio.ServerInterceptor):
    """gRPC interceptor for request logging"""
    
    async def intercept_service(self, continuation, handler_call_details):
        """Log request details"""
        
        method = handler_call_details.method
        metadata = dict(handler_call_details.invocation_metadata)
        peer = metadata.get('grpc-accept-encoding', 'unknown')
        
        logger.debug(f"📡 LoggingInterceptor called for: {method}")
        logger.debug(f"👤 Peer info: {peer}")
        logger.debug(f"📊 All metadata: {metadata}")
        
        logger.info(f"🚀 gRPC request: {method} from peer: {peer}")
        
        try:
            logger.debug("⏳ Calling continuation...")
            response = await continuation(handler_call_details)
            logger.info(f"gRPC request completed: {method}")
            return response
        except Exception as e:
            logger.error(f"gRPC request failed: {method} - {str(e)}")
            raise
