"""
FastAPI router for notification endpoints.
Provides organized API routes for sending messages to various platforms.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Query, Body
from fastapi.responses import JSONResponse
from loguru import logger

from ..adapters.telegram import telegram_adapter, TelegramAdapter
from ..adapters.feishu import feishu_adapter
from ..config.settings import settings


# Create the notifier router
router = APIRouter(prefix="/notifier", tags=["notifier"])


@router.post("/notify_telegram")
async def notify_telegram(
    message_text: str = Body("你好", media_type="text/plain", description="Message text content"),
    group_id: int = Query(default=settings.telegram_default_group_id, description="Telegram group ID")
):
    """
    Send a text message to a Telegram group.
    
    Args:
        message_text: 消息文本内容，以plain text格式发送，默认值为"你好"
        group_id: Telegram群组ID，默认使用配置文件中的值
    
    Returns:
        Telegram API响应结果，包含消息发送状态和相关信息
    """
    logger.info(f"Received Telegram notification request for group {group_id}")
    
    try:
        # 验证消息内容不为空
        message_text = message_text.strip()
        
        if not message_text:
            raise HTTPException(status_code=400, detail="Message content is required")
        
        # Validate Telegram configuration
        if not telegram_adapter or not telegram_adapter.validate_config():
            raise HTTPException(
                status_code=503, 
                detail="Telegram service not configured or unavailable"
            )
        
        # Send message via Telegram adapter
        result = await telegram_adapter.send_message(message_text, group_id)
        
        logger.success(f"Telegram message sent successfully to group {group_id}")
        return {
            "status": "success",
            "platform": "telegram",
            "group_id": group_id,
            "message_id": result.get("result", {}).get("message_id"),
            "timestamp": result.get("result", {}).get("date")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send Telegram message: {str(e)}"
        )


@router.post("/notify_feishu")
async def notify_feishu(
    message_text: str = Body("你好", media_type="text/plain", description="Message text content"),
    receive_id: Optional[str] = Query(default=None, description="Target user ID (optional, 10-20 digit number format)")
):
    """
    Send a text message via Feishu (Lark) API.
    
    Args:
        message_text: 消息文本内容，以plain text格式发送，默认值为"你好"
        receive_id: 目标用户ID，可选参数，默认使用配置文件中的FEISHU_DEFAULT_USER_ID值
    
    Returns:
        飞书API响应结果，包含消息发送状态和相关信息
    
    Note:
        - app_id和app_secret从环境配置自动读取（FEISHU_APP_ID、FEISHU_APP_SECRET）
        - receive_id格式要求：必须是10-20位数字格式的用户ID (如: 6421712345678901234)
        - ID优先级：receive_id参数 > FEISHU_DEFAULT_USER_ID配置 > 返回错误
    """
    # 验证Feishu应用配置是否完整（在API启动时应已验证）
    if not settings.feishu_app_id or not settings.feishu_app_secret:
        raise HTTPException(
            status_code=503,
            detail="Feishu service not configured. Please check FEISHU_APP_ID and FEISHU_APP_SECRET environment variables."
        )
    
    # 确定实际使用的接收方ID，优先使用传入的receive_id参数
    actual_receive_id = receive_id or settings.feishu_default_user_id
    target_for_log = actual_receive_id or "NOT_SET"
    logger.info(f"Received Feishu notification request for receive_id: {target_for_log}")
    
    try:
        
        # 验证消息内容不为空
        message_text = message_text.strip()
        if not message_text:
            raise HTTPException(status_code=400, detail="Message content is required")
        
        # 通过飞书适配器发送消息，使用改进的ID处理逻辑
        result = await feishu_adapter.send_message(
            app_id=settings.feishu_app_id,
            app_secret=settings.feishu_app_secret,
            message=message_text,
            receive_id=receive_id,
            default_user_id=settings.feishu_default_user_id
        )
        
        logger.success(f"Feishu message sent successfully to {actual_receive_id}")
        
        return {
            "status": "success",
            "platform": "feishu",
            "app_id": settings.feishu_app_id,
            "receive_id": actual_receive_id,
            "message_id": result.get("data", {}).get("message_id"),
            "timestamp": result.get("data", {}).get("create_time")
        }
        
    except ValueError as e:
        # 处理参数验证错误，返回400状态码
        logger.error(f"Invalid Feishu message parameters: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid parameters: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send Feishu message: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send Feishu message: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring service status.
    
    Returns service configuration and adapter status.
    """
    telegram_status = "configured" if telegram_adapter else "not_configured"
    
    # Feishu状态检查：需要app_id和app_secret都配置才算完整
    feishu_configured = bool(settings.feishu_app_id and settings.feishu_app_secret)
    feishu_status = "configured" if feishu_configured else "not_configured"
    
    # 检查Feishu默认用户ID配置状态
    feishu_default_configured = bool(settings.feishu_default_user_id)
    
    return {
        "status": "healthy",
        "service": "notification-service",
        "port": settings.api_port,
        "adapters": {
            "telegram": telegram_status,
            "feishu": feishu_status
        },
        "configuration": {
            "telegram_default_group": settings.telegram_default_group_id,
            "feishu_credentials_configured": feishu_configured,
            "feishu_default_user_configured": feishu_default_configured
        },
        "api_changes": {
            "notify_feishu": "Now uses environment configuration for app_id/app_secret, only requires receive_id parameter",
            "both_endpoints": "Added default message body value '你好'"
        }
    }