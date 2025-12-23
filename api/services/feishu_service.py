"""飞书消息服务"""
import os
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict


def send_message(webhook_url: str, message: str) -> dict:
    """
    发送文本消息到飞书 Webhook
    
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


def send_card_message(webhook_url: str, title: str, elements: List[Dict]) -> dict:
    """
    发送卡片消息到飞书 Webhook
    
    参数：
    - webhook_url: 飞书机器人 Webhook URL
    - title: 卡片标题
    - elements: 卡片内容元素列表
    
    返回：
    - dict: 发送结果 {'success': bool, 'response'/'error': ...}
    """
    try:
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": title
                    },
                    "template": "blue"
                },
                "elements": elements
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


def send_daily_summary_card(summary_data: dict) -> dict:
    """
    发送每日汇总卡片消息
    
    参数：
    - summary_data: 汇总数据字典，包含 date, stores 等信息
    
    返回：
    - dict: 发送结果
    """
    webhook_url = get_webhook_url()
    
    if not webhook_url:
        return {
            'success': False,
            'error': '未配置飞书 Webhook URL，请在 .env 文件中设置 FEISHU_WEBHOOK_URL'
        }
    
    date_str = summary_data.get('date', '')
    stores = summary_data.get('stores', [])
    
    # 计算总计
    total_orders = sum(s['order_count'] for s in stores)
    total_amount = sum(s['total_amount'] for s in stores)
    total_print = sum(s.get('total_print_amount', 0.0) for s in stores)
    total_revenue = sum(s.get('total_revenue', 0.0) for s in stores)
    
    # 构建卡片元素
    elements = []
    
    # 添加日期和平台信息
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**📅 日期：** {date_str}\n**🐼 平台：** 熊猫外卖 HungryPanda"
        }
    })
    
    elements.append({"tag": "hr"})
    
    # 添加各店铺数据
    for idx, store in enumerate(stores):
        store_name = store['store_name']
        order_count = store['order_count']
        amount = store['total_amount']
        print_amt = store.get('total_print_amount', 0.0)
        revenue = store.get('total_revenue', 0.0)
        
        # 店铺标题
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🏪 {store_name}**"
            }
        })
        
        # 店铺数据（使用列布局）
        elements.append({
            "tag": "column_set",
            "flex_mode": "none",
            "background_style": "grey",
            "columns": [
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"📦 **订单数**\n{order_count} 单"
                            }
                        }
                    ]
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"💰 **实收金额**\n£{amount:.2f}"
                            }
                        }
                    ]
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"💵 **打印单**\n£{print_amt:.2f}"
                            }
                        }
                    ]
                },
                {
                    "tag": "column",
                    "width": "weighted",
                    "weight": 1,
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"💸 **预计收入**\n£{revenue:.2f}"
                            }
                        }
                    ]
                }
            ]
        })
        
        # 在最后一个店铺后不添加分割线
        if idx < len(stores) - 1:
            elements.append({"tag": "hr"})
    
    # 添加总计区域
    elements.append({"tag": "hr"})
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**📊 汇总统计**"
        }
    })
    
    elements.append({
        "tag": "column_set",
        "flex_mode": "none",
        "background_style": "blue",
        "columns": [
            {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"📈 **总订单**\n{total_orders} 单"
                        }
                    }
                ]
            },
            {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"💷 **实收总额**\n£{total_amount:.2f}"
                        }
                    }
                ]
            },
            {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"📤 **打印单总额**\n£{total_print:.2f}"
                        }
                    }
                ]
            },
            {
                "tag": "column",
                "width": "weighted",
                "weight": 1,
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"💹 **预计总收入**\n£{total_revenue:.2f}"
                        }
                    }
                ]
            }
        ]
    })
    
    # 添加备注
    elements.append({
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"数据生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        ]
    })
    
    title = f"🐼 熊猫外卖 {date_str} 订单数据汇总"
    
    return send_card_message(webhook_url, title, elements)
