"""
Feishu (Lark) Open API adapter for sending messages.
Implements the two-step authentication and messaging process:
1. Get tenant access token
2. Send message to user/group
"""
import asyncio
import aiohttp
import re
from typing import Optional, Dict, Any, Callable
from loguru import logger
from ..config.settings import settings


async def retry_async_feishu(func: Callable, max_retries: int = 3, base_delay: float = 1.0) -> Any:
    """
    异步重试装饰器，专为Feishu API设计，支持指数退避策略。
    
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
            logger.warning(f"Feishu API attempt {attempt + 1} failed: {str(e)}, retrying in {delay}s...")
            await asyncio.sleep(delay)
    
    # 这行代码理论上不会执行到，但为了类型安全
    raise last_exception


class FeishuAdapter:
    """Adapter for sending messages via Feishu Open API."""
    
    AUTH_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"
    
    def __init__(self):
        """Initialize Feishu adapter."""
        self._token_cache = {}  # Simple in-memory token cache
    
    @staticmethod
    def _is_valid_user_id(user_id: str) -> bool:
        """
        验证用户ID是否为有效格式。
        Feishu要求用户ID为64位数字格式。
        
        Args:
            user_id: 待验证的用户ID
            
        Returns:
            bool: 如果是有效的用户ID格式则返回True
        """
        if not user_id:
            return False
        
        # 检查是否为纯数字且长度合理（通常为19位左右的数字）
        return re.match(r'^\d{10,20}$', user_id) is not None
    
    async def _get_access_token(self, app_id: str, app_secret: str) -> str:
        """
        Get tenant access token from Feishu API with proxy support and retry mechanism.
        
        Args:
            app_id: Feishu application ID
            app_secret: Feishu application secret
            
        Returns:
            str: Access token
            
        Raises:
            Exception: If token retrieval fails after retries
        """
        # Check cache first (simple implementation - no expiration handling for now)
        cache_key = f"{app_id}:{app_secret[:8]}..."
        if cache_key in self._token_cache:
            logger.debug("Using cached Feishu access token")
            return self._token_cache[cache_key]
        
        payload = {
            "app_id": app_id,
            "app_secret": app_secret
        }
        
        logger.info("Requesting Feishu access token")
        
        # 配置代理设置
        proxy = None
        if settings.https_proxy:
            proxy = settings.https_proxy
            logger.debug(f"Using HTTPS proxy for Feishu auth: {proxy}")
        elif settings.http_proxy:
            proxy = settings.http_proxy
            logger.debug(f"Using HTTP proxy for Feishu auth: {proxy}")
        
        async def _get_token():
            """内部获取token函数，支持重试机制"""
            connector = None
            try:
                # 配置连接器 - 支持代理和SSL验证设置
                ssl_context = settings.verify_ssl if hasattr(settings, 'verify_ssl') else True
                if proxy or not ssl_context:
                    connector = aiohttp.TCPConnector(ssl=ssl_context)
                    if not ssl_context:
                        logger.warning("⚠️  Feishu API: SSL certificate verification disabled for token request")
                
                timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.post(self.AUTH_URL, json=payload, proxy=proxy) as response:
                        result = await response.json()
                        
                        if response.status == 200 and result.get("code") == 0:
                            token = result.get("tenant_access_token")
                            if token:
                                # Cache the token (simple implementation)
                                self._token_cache[cache_key] = token
                                logger.success("Feishu access token obtained successfully")
                                return token
                        
                        error_msg = result.get("msg", "Unknown error")
                        logger.error(f"Failed to get Feishu access token: {error_msg}")
                        raise Exception(f"Feishu auth error: {error_msg}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Network error getting Feishu token: {str(e)}")
                raise Exception(f"Network error: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error getting Feishu token: {str(e)}")
                raise
            finally:
                if connector:
                    await connector.close()
        
        # 使用重试机制获取token
        try:
            return await retry_async_feishu(_get_token, max_retries=3, base_delay=1.0)
        except Exception as e:
            logger.error(f"All retry attempts failed for Feishu token: {str(e)}")
            raise
    
    async def send_message(self, app_id: str, app_secret: str, message: str, 
                          receive_id: Optional[str] = None, 
                          default_user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a text message via Feishu API.
        
        Args:
            app_id: Feishu application ID
            app_secret: Feishu application secret  
            message: Message text to send
            receive_id: Target user/group ID. 如果为None，将尝试使用default_user_id
            default_user_id: 默认用户ID（从配置中获取）
            
        Returns:
            dict: API response from Feishu
            
        Raises:
            ValueError: If required parameters are missing or invalid
            Exception: If message sending fails
        """
        if not app_id or not app_secret:
            raise ValueError("Feishu app_id and app_secret are required")
        
        # 智能选择接收方ID，优先级：receive_id > default_user_id > 错误
        target_receive_id = None
        
        if receive_id:
            if self._is_valid_user_id(receive_id):
                target_receive_id = receive_id
                logger.info(f"Using provided receive_id: {receive_id}")
            else:
                raise ValueError(f"Invalid receive_id format: '{receive_id}'. Must be 10-20 digit number (e.g., 6421712345678901234)")
        elif default_user_id:
            if self._is_valid_user_id(default_user_id):
                target_receive_id = default_user_id
                logger.info(f"Using default user ID from configuration: {default_user_id}")
            else:
                raise ValueError(f"Invalid default_user_id format in configuration: '{default_user_id}'. Must be 10-20 digit number")
        else:
            raise ValueError(
                "No valid receive_id provided. Either provide a valid receive_id in the request, "
                "or configure FEISHU_DEFAULT_USER_ID in environment variables. "
                "User ID must be 10-20 digit number format (e.g., 6421712345678901234)"
            )
        
        # Step 1: Get access token
        access_token = await self._get_access_token(app_id, app_secret)
        
        # Step 2: Send message
        url = f"{self.MESSAGE_URL}?receive_id_type=user_id"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "receive_id": target_receive_id,
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        
        logger.info(f"Sending Feishu message to {target_receive_id}")
        logger.debug(f"Message content: {message[:100]}...")
        
        # 配置代理设置
        proxy = None
        if settings.https_proxy:
            proxy = settings.https_proxy
            logger.debug(f"Using HTTPS proxy for Feishu message: {proxy}")
        elif settings.http_proxy:
            proxy = settings.http_proxy
            logger.debug(f"Using HTTP proxy for Feishu message: {proxy}")
        
        async def _send_request():
            """内部发送消息函数，支持重试机制"""
            connector = None
            try:
                # 配置连接器 - 支持代理和SSL验证设置
                ssl_context = settings.verify_ssl if hasattr(settings, 'verify_ssl') else True
                if proxy or not ssl_context:
                    connector = aiohttp.TCPConnector(ssl=ssl_context)
                    if not ssl_context:
                        logger.warning("⚠️  Feishu API: SSL certificate verification disabled for message request")
                
                timeout = aiohttp.ClientTimeout(total=30)  # 30秒超时
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    async with session.post(url, json=payload, headers=headers, proxy=proxy) as response:
                        result = await response.json()
                        
                        if response.status == 200 and result.get("code") == 0:
                            logger.success(f"Message sent successfully to Feishu user {target_receive_id}")
                            return result
                        else:
                            error_msg = result.get("msg", "Unknown error")
                            logger.error(f"Failed to send Feishu message: {error_msg}")
                            raise Exception(f"Feishu API error: {error_msg}")
                            
            except aiohttp.ClientError as e:
                logger.error(f"Network error sending Feishu message: {str(e)}")
                raise Exception(f"Network error: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error sending Feishu message: {str(e)}")
                raise
            finally:
                if connector:
                    await connector.close()
        
        # 使用重试机制发送消息
        try:
            return await retry_async_feishu(_send_request, max_retries=3, base_delay=1.0)
        except Exception as e:
            logger.error(f"All retry attempts failed for Feishu message: {str(e)}")
            raise
    
    def clear_token_cache(self):
        """Clear the access token cache."""
        self._token_cache.clear()
        logger.info("Feishu token cache cleared")


# Global feishu adapter instance
feishu_adapter = FeishuAdapter()