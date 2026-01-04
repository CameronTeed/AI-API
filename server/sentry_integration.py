"""
Sentry Integration Module
Handles error tracking and monitoring with Sentry
"""

import logging
import os
from typing import Optional

try:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Global flag to track if Sentry is initialized and enabled
_SENTRY_ENABLED = False


def init_sentry(
    dsn: Optional[str] = None,
    environment: str = "production",
    traces_sample_rate: float = 0.1,
    enable_logging: bool = True,
) -> bool:
    """
    Initialize Sentry for error tracking and monitoring

    Args:
        dsn: Sentry DSN (if None, reads from SENTRY_DSN env var)
        environment: Environment name (production, staging, development)
        traces_sample_rate: Sample rate for performance monitoring (0.0-1.0)
        enable_logging: Whether to integrate with Python logging

    Returns:
        True if Sentry was initialized, False otherwise
    """
    # Check if Sentry is explicitly disabled via environment variable
    sentry_enabled = os.getenv("SENTRY_ENABLED", "true").lower() in ("true", "1", "yes")
    if not sentry_enabled:
        logger.debug("Sentry is disabled via SENTRY_ENABLED=false")
        return False

    if not SENTRY_AVAILABLE:
        logger.warning("Sentry SDK not installed. Install with: pip install sentry-sdk")
        return False

    # Get DSN from parameter or environment
    sentry_dsn = dsn or os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        logger.debug("SENTRY_DSN not configured. Sentry error tracking disabled.")
        return False
    
    try:
        # Configure logging integration to capture logs
        logging_integration = None
        if enable_logging:
            logging_integration = LoggingIntegration(
                level=logging.INFO,  # Capture info and above
                event_level=logging.ERROR,  # Send errors to Sentry
            )
        
        # Initialize Sentry
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            integrations=[logging_integration] if logging_integration else [],
            # Only send errors, not all events
            before_send=_before_send,
        )
        
        logger.info(f"✅ Sentry initialized for {environment} environment")
        global _SENTRY_ENABLED
        _SENTRY_ENABLED = True
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize Sentry: {str(e)}")
        return False


def is_sentry_enabled() -> bool:
    """
    Check if Sentry is enabled and initialized

    Returns:
        True if Sentry is enabled, False otherwise
    """
    return _SENTRY_ENABLED


def _before_send(event: dict, hint: dict) -> Optional[dict]:
    """
    Filter events before sending to Sentry
    Only send critical errors and exceptions
    """
    # Always send exceptions
    if event.get("exception"):
        return event
    
    # Only send ERROR level logs, not INFO/WARNING
    if event.get("level") == "error":
        return event
    
    # Drop other events (like breadcrumbs, info logs)
    return None


def capture_exception(exception: Exception, level: str = "error", **kwargs):
    """
    Manually capture an exception in Sentry

    Args:
        exception: The exception to capture
        level: Log level (error, warning, info)
        **kwargs: Additional context to send with the exception
    """
    if not _SENTRY_ENABLED or not SENTRY_AVAILABLE:
        return

    try:
        with sentry_sdk.push_scope() as scope:
            # Add context
            for key, value in kwargs.items():
                scope.set_context(key, value)

            # Capture exception
            sentry_sdk.capture_exception(exception)
            logger.debug(f"Captured exception in Sentry: {str(exception)}")

    except Exception as e:
        logger.error(f"Failed to capture exception in Sentry: {str(e)}")


def capture_message(message: str, level: str = "error", **kwargs):
    """
    Manually capture a message in Sentry

    Args:
        message: The message to capture
        level: Log level (error, warning, info)
        **kwargs: Additional context
    """
    if not _SENTRY_ENABLED or not SENTRY_AVAILABLE:
        return

    try:
        with sentry_sdk.push_scope() as scope:
            # Add context
            for key, value in kwargs.items():
                scope.set_context(key, value)

            # Capture message
            sentry_sdk.capture_message(message, level=level)
            logger.debug(f"Captured message in Sentry: {message}")

    except Exception as e:
        logger.error(f"Failed to capture message in Sentry: {str(e)}")


def set_user_context(user_id: str, email: Optional[str] = None, **kwargs):
    """
    Set user context for error tracking

    Args:
        user_id: Unique user identifier
        email: User email (optional)
        **kwargs: Additional user properties
    """
    if not _SENTRY_ENABLED or not SENTRY_AVAILABLE:
        return

    try:
        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
            **kwargs,
        })
    except Exception as e:
        logger.error(f"Failed to set user context in Sentry: {str(e)}")


def get_sentry_client():
    """Get the Sentry client instance"""
    if SENTRY_AVAILABLE:
        return sentry_sdk.get_client()
    return None

