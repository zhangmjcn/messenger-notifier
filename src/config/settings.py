"""
Configuration management system with multi-layer priority:
1. .env file (highest priority)
2. docker-compose.yml environment (medium priority) 
3. env_for_docker defaults (lowest priority)
"""
import os
from typing import Optional
from dotenv import load_dotenv


class Settings:
    """Application settings with multi-layer configuration support."""
    
    def __init__(self):
        # Load environment files in reverse priority order
        # Later loaded files override earlier ones
        load_dotenv("env_for_docker", override=False)  # Lowest priority
        load_dotenv(".env", override=True)  # Highest priority
        
        # API Configuration
        self.api_port = int(os.getenv("API_PORT", "18888"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Telegram Configuration
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_default_group_id = int(os.getenv("TELEGRAM_DEFAULT_GROUP_ID", "-868155406"))
        
        # Feishu Configuration
        self.feishu_app_id = os.getenv("FEISHU_APP_ID")
        self.feishu_app_secret = os.getenv("FEISHU_APP_SECRET")
        self.feishu_default_user_id = os.getenv("FEISHU_DEFAULT_USER_ID")
        
        # 代理配置 - 支持企业网络环境和防火墙
        self.http_proxy = os.getenv('HTTP_PROXY') or os.getenv('http_proxy')
        self.https_proxy = os.getenv('HTTPS_PROXY') or os.getenv('https_proxy')  
        self.no_proxy = os.getenv('NO_PROXY') or os.getenv('no_proxy')
        
        # SSL证书验证配置 - 用于解决企业网络环境中的证书问题
        # 生产环境应该保持True，开发/测试环境可设置为false
        ssl_verify_str = os.getenv('VERIFY_SSL', 'true').lower()
        self.verify_ssl = ssl_verify_str in ('true', '1', 'yes', 'on')


def load_settings() -> Settings:
    """
    Load application settings with multi-layer configuration.
    Priority: .env > docker-compose environment > env_for_docker defaults
    """
    # Load base settings
    settings = Settings()
    
    # Try to import loguru for logging, but don't fail if it's not available
    try:
        from loguru import logger
        # Log configuration sources used
        logger.info(f"Configuration loaded - API Port: {settings.api_port}")
        logger.info(f"Log level: {settings.log_level}")
        
        if settings.telegram_bot_token:
            logger.info("Telegram configuration found")
        else:
            logger.warning("Telegram bot token not configured")
        
        if settings.feishu_app_id and settings.feishu_app_secret:
            logger.info("Feishu basic configuration found")
            if settings.feishu_default_user_id:
                logger.info("Feishu default user ID configured")
            else:
                logger.warning("Feishu default user ID not configured - require receive_id in requests")
        else:
            logger.warning("Feishu basic configuration (app_id/app_secret) not complete")
        
        # 代理配置日志输出
        if settings.http_proxy or settings.https_proxy:
            proxy_info = []
            if settings.http_proxy:
                proxy_info.append("HTTP")
            if settings.https_proxy:
                proxy_info.append("HTTPS")
            logger.info(f"Proxy configuration found for: {', '.join(proxy_info)}")
            if settings.no_proxy:
                logger.info(f"No-proxy list configured: {settings.no_proxy[:50]}..." if len(settings.no_proxy) > 50 else settings.no_proxy)
        else:
            logger.info("No proxy configuration found - using direct connection")
        
        # SSL证书验证配置日志输出
        if settings.verify_ssl:
            logger.info("SSL certificate verification enabled (production mode)")
        else:
            logger.warning("⚠️  SSL certificate verification disabled - only use in development/testing environments!")
            logger.warning("⚠️  This may expose your application to security risks in production")
    except ImportError:
        # Fallback to print if loguru is not available
        print(f"Configuration loaded - API Port: {settings.api_port}")
        print(f"Log level: {settings.log_level}")
    
    return settings


# Global settings instance
settings = load_settings()