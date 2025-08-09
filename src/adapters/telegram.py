"""
Telegram Bot API adapter for sending messages to Telegram groups.
Uses the official Telegram Bot API to send text messages.
"""
import asyncio
import aiohttp
from typing import Optional, Callable, Any
from loguru import logger
from ..config.settings import settings


async def retry_async(func: Callable, max_retries: int = 3, base_delay: float = 1.0) -> Any:
    """
    异步重试装饰器，支持指数退避策略。
    
    Args:
        func: 要重试的异步函数
        max_retries: 最大重试次数，默认3次
        base_delay: 基础延迟时间（秒），默认1秒
    
    Returns:
        函数执行结果
        
    Raises:
        最后一次尝试的异常
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):  # +1 因为第一次不算重试
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt == max_retries:  # 最后一次尝试失败
                raise e
            
            # 指数退避：1s, 2s, 4s
            delay = base_delay * (2 ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}, retrying in {delay}s...")
            await asyncio.sleep(delay)
    
    # 这行代码理论上不会执行到，但为了类型安全
    raise last_exception


class TelegramAdapter:
    """Adapter for sending messages to Telegram groups via Bot API."""
    
    def __init__(self, bot_token: Optional[str] = None):
        """
        Initialize Telegram adapter.
        
        Args:
            bot_token: Telegram bot token. If None, uses settings.telegram_bot_token
        """
        self.bot_token = bot_token or settings.telegram_bot_token
        if not self.bot_token:
            logger.error("Telegram bot token not configured")
            raise ValueError("Telegram bot token is required")
        
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    async def send_message(self, text: str, group_id: Optional[int] = None) -> dict:
        """
        Send a text message to a Telegram group with proxy support and retry mechanism.
        
        Args:
            text: Message text to send
            group_id: Target group ID. If None, uses default from settings
            
        Returns:
            dict: API response from Telegram
            
        Raises:
            Exception: If message sending fails after retries
        """
        target_group = group_id or settings.telegram_default_group_id
        
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": target_group,
            "text": text,
            "parse_mode": "HTML"  # Support basic HTML formatting
        }
        
        logger.info(f"Sending Telegram message to group {target_group}")
        logger.debug(f"Message content: {text[:100]}...")
        
        # 配置代理设置
        proxy = None
        if settings.https_proxy:
            proxy = settings.https_proxy
            logger.debug(f"Using HTTPS proxy for Telegram API: {proxy}")
        elif settings.http_proxy:
            proxy = settings.http_proxy
            logger.debug(f"Using HTTP proxy for Telegram API: {proxy}")
        
        async def _send_request():
            """内部发送请求函数，支持重试机制"""
            connector = None
            try:
                # 配置连接器 - 支持代理和SSL验证设置
                ssl_context = settings.verify_ssl if hasattr(settings, 'verify_ssl') else True
                if proxy or not ssl_context:
                    connector = aiohttp.TCPConnector(ssl=ssl_context)
                    if not ssl_context:
                        logger.warning("⚠️  Telegram API: SSL certificate verification disabled")
                
                timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.post(url, json=payload, proxy=proxy) as response:
                        result = await response.json()
                        
                        if response.status == 200 and result.get("ok"):
                            logger.success(f"Message sent successfully to Telegram group {target_group}")
                            return result
                        else:
                            error_msg = result.get("description", "Unknown error")
                            logger.error(f"Failed to send Telegram message: {error_msg}")
                            raise Exception(f"Telegram API error: {error_msg}")
            except aiohttp.ClientError as e:
                logger.error(f"Network error sending Telegram message: {str(e)}")
                raise Exception(f"Network error: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error sending Telegram message: {str(e)}")
                raise
            finally:
                if connector:
                    await connector.close()
        
        # 使用重试机制发送消息
        try:
            return await retry_async(_send_request, max_retries=3, base_delay=1.0)
        except Exception as e:
            logger.error(f"All retry attempts failed for Telegram message: {str(e)}")
            raise
    
    def validate_config(self) -> bool:
        """
        Validate Telegram configuration.
        
        Returns:
            bool: True if configuration is valid
        """
        if not self.bot_token:
            logger.error("Telegram bot token not configured")
            return False
        
        if not settings.telegram_default_group_id:
            logger.warning("Default Telegram group ID not configured")
        
        return True


# Global telegram adapter instance
telegram_adapter = TelegramAdapter() if settings.telegram_bot_token else None