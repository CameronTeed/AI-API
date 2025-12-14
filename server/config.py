"""
Production Configuration Module
Handles all configuration management for the AI Orchestrator
"""

import os
import logging
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


@dataclass
class ServerConfig:
    """Server configuration"""
    port: int
    host: str
    environment: str  # 'development', 'staging', 'production'
    debug: bool
    log_level: str


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str
    port: int
    user: str
    password: str
    database: str
    pool_min_size: int
    pool_max_size: int
    pool_timeout: int


@dataclass
class APIConfig:
    """External API configuration"""
    openai_api_key: str
    google_places_api_key: Optional[str]
    bearer_token: str
    java_grpc_target: str
    search_provider: str
    default_city: str


@dataclass
class FeatureConfig:
    """Feature flags"""
    enable_vector_search: bool
    enable_web_search: bool
    enable_caching: bool
    enable_monitoring: bool


class Config:
    """Main configuration class"""
    
    def __init__(self):
        """Initialize configuration from environment"""
        load_dotenv()
        self._validate_required_vars()
        self._load_configs()
    
    def _validate_required_vars(self):
        """Validate required environment variables"""
        required = ['OPENAI_API_KEY']
        missing = [var for var in required if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
    
    def _load_configs(self):
        """Load all configurations"""
        env = os.getenv('ENVIRONMENT', 'development')
        
        self.server = ServerConfig(
            port=int(os.getenv('PORT', '7000')),
            host=os.getenv('HOST', '0.0.0.0'),
            environment=env,
            debug=env != 'production',
            log_level=os.getenv('LOG_LEVEL', 'INFO' if env == 'production' else 'DEBUG')
        )
        
        self.database = DatabaseConfig(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'ai_orchestrator'),
            pool_min_size=int(os.getenv('DB_POOL_MIN', '1')),
            pool_max_size=int(os.getenv('DB_POOL_MAX', '10')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30'))
        )
        
        self.api = APIConfig(
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            google_places_api_key=os.getenv('GOOGLE_PLACES_API_KEY'),
            bearer_token=os.getenv('AI_BEARER_TOKEN', 'default_token'),
            java_grpc_target=os.getenv('JAVA_GRPC_TARGET', 'localhost:8081'),
            search_provider=os.getenv('SEARCH_PROVIDER', 'none'),
            default_city=os.getenv('DEFAULT_CITY', 'Ottawa')
        )
        
        self.features = FeatureConfig(
            enable_vector_search=os.getenv('ENABLE_VECTOR_SEARCH', 'true').lower() == 'true',
            enable_web_search=os.getenv('ENABLE_WEB_SEARCH', 'true').lower() == 'true',
            enable_caching=os.getenv('ENABLE_CACHING', 'true').lower() == 'true',
            enable_monitoring=os.getenv('ENABLE_MONITORING', 'false').lower() == 'true'
        )
    
    def log_config(self):
        """Log configuration (without sensitive data)"""
        logger.info(f"Environment: {self.server.environment}")
        logger.info(f"Server: {self.server.host}:{self.server.port}")
        logger.info(f"Database: {self.database.host}:{self.database.port}/{self.database.database}")
        logger.info(f"Search Provider: {self.api.search_provider}")
        logger.info(f"Default City: {self.api.default_city}")
        logger.debug(f"Features: Vector={self.features.enable_vector_search}, Web={self.features.enable_web_search}")


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config()
    return _config

