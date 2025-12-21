"""飞书消息服务"""
import os
import requests
from datetime import datetime, timedelta
from typing import Optional

from utils import get_db_conn


def send_message(webhook_url: str, message: str) -> dict:
    """
    发送消息到飞书 Webhook
    
    参数：
    - webhook_url: 飞书机器人 Webhook URL
    - message: 要发送的文本消息
    
    返回：
    - dict: 发送结果 {'success': bool, 'response'/'error': ...}
    """
    try:
        payload = {
            "msg_type": "text",
            "content": {
                "text": message
            }
        }
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        response.raise_for_status()
        result = response.json()
        
        return {
            'success': True,
            'response': result
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_webhook_url() -> Optional[str]:
    """
    从环境变量获取飞书 Webhook URL
    
    返回：
    - str: Webhook URL，如果未配置则返回 None
    """
    webhook_url = os.environ.get("FEISHU_WEBHOOK_URL")
    
    if not webhook_url or webhook_url == "https://open.feishu.cn/open-apis/bot/v2/hook/your-webhook-url-here":
        return None
    
    return webhook_url


def send_with_default_webhook(message: str) -> dict:
    """
    使用默认 Webhook 发送消息
    
    参数：
    - message: 消息内容
    
    返回：
    - dict: 发送结果
    """
    webhook_url = get_webhook_url()
    
    if not webhook_url:
        return {
            'success': False,
            'error': '未配置飞书 Webhook URL，请在 .env 文件中设置 FEISHU_WEBHOOK_URL'
        }
    
    return send_message(webhook_url, message)
