"""
Custom Exception Classes
Provides structured exception handling for the application
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AIOrchhestratorException(Exception):
    """Base exception for AI Orchestrator"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """Initialize exception"""
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            'error': self.error_code,
            'message': self.message,
            'status_code': self.status_code,
            'details': self.details
        }


class ConfigurationError(AIOrchhestratorException):
    """Raised when configuration is invalid"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )


class DatabaseError(AIOrchhestratorException):
    """Raised when database operation fails"""
    
    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=503,
            details=details
        )


class ExternalAPIError(AIOrchhestratorException):
    """Raised when external API call fails"""
    
    def __init__(self, message: str, api_name: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="EXTERNAL_API_ERROR",
            status_code=502,
            details={'api': api_name, **(details or {})}
        )


class ValidationError(AIOrchhestratorException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details={'field': field, **(details or {})}
        )


class AuthenticationError(AIOrchhestratorException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401
        )


class AuthorizationError(AIOrchhestratorException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403
        )


class RateLimitError(AIOrchhestratorException):
    """Raised when rate limit is exceeded"""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            status_code=429,
            details={'retry_after': retry_after}
        )


class ServiceUnavailableError(AIOrchhestratorException):
    """Raised when service is unavailable"""
    
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            status_code=503
        )


def log_exception(exc: Exception, context: str = ""):
    """Log exception with context"""
    if isinstance(exc, AIOrchhestratorException):
        logger.error(
            f"Error in {context}: {exc.error_code} - {exc.message}",
            extra={'details': exc.details}
        )
    else:
        logger.error(f"Unexpected error in {context}: {str(exc)}", exc_info=True)

