"""定时提醒路由"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from services import feishu_service, report_service

router = APIRouter(prefix="/reminder", tags=["reminder"])


class CustomReminderRequest(BaseModel):
    """自定义提醒请求"""
    message: str
    webhook_url: Optional[str] = None


@router.post("/daily-summary")
def send_daily_summary(platform: Optional[str] = None):
    """
    发送每日订单汇总
    
    定时任务接口：每天早上发送昨日订单汇总到飞书群
    
    参数：
    - platform: 可选，指定平台 ('panda', 'deliveroo'，不指定则查询所有平台)
    
    示例 crontab 配置：
    # 所有平台汇总（默认）
    0 9 * * * curl -s -X POST http://api:8000/reminder/daily-summary
    
    # 仅熊猫外卖
    0 9 * * * curl -s -X POST "http://api:8000/reminder/daily-summary?platform=panda"
    
    # 仅 Deliveroo
    0 9 * * * curl -s -X POST "http://api:8000/reminder/daily-summary?platform=deliveroo"
    """
    from datetime import timedelta
    
    # 获取昨天的日期
    date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 标准化平台参数
    if platform:
        platform = platform.lower()
        if platform in ['hungrypanda', 'panda']:
            platform = 'panda'
        elif platform in ['deliveroo', 'roo']:
            platform = 'deliveroo'
    
    # 查询汇总数据
    summary_data = report_service.query_order_summary(date_str, platform=platform)
    
    # 设置标题前缀
    if platform == 'panda':
        platform_emoji = '🐼'
        platform_name = '熊猫外卖'
    elif platform == 'deliveroo':
        platform_emoji = '🦘'
        platform_name = 'Deliveroo'
    else:
        platform_emoji = '📊'
        platform_name = '全平台'
    
    if not summary_data['success']:
        # 如果查询失败，发送文本消息
        result = feishu_service.send_with_default_webhook(
            f"{platform_emoji} {platform_name} {date_str} 数据汇总\n\n{summary_data['message']}"
        )
    else:
        # 发送卡片消息
        result = feishu_service.send_daily_summary_card(summary_data)
    
    # 同时生成文本汇总供返回
    summary_text = report_service.generate_daily_summary_text(date_str, platform=platform)
    
    if result['success']:
        return {
            'status': 'ok',
            'message': f'{platform_name}每日汇总已发送',
            'timestamp': datetime.now().isoformat(),
            'summary': summary_text
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"发送失败: {result.get('error', 'Unknown error')}"
        )


@router.post("/custom")
def send_custom_message(req: CustomReminderRequest):
    """
    发送自定义提醒消息
    
    参数：
    - message: 消息内容
    - webhook_url: 可选的自定义 webhook URL（不提供则使用环境变量配置）
    
    示例：
    curl -X POST http://localhost:8000/reminder/custom \
      -H "Content-Type: application/json" \
      -d '{"message":"测试消息"}'
    """
    if req.webhook_url:
        # 使用自定义 webhook
        result = feishu_service.send_message(req.webhook_url, req.message)
    else:
        # 使用默认 webhook
        result = feishu_service.send_with_default_webhook(req.message)
    
    if result['success']:
        return {
            'status': 'ok',
            'message': '消息已发送',
            'timestamp': datetime.now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"发送失败: {result.get('error', 'Unknown error')}"
        )


@router.post("/store-summary")
def send_store_summary(store_name: str, date: Optional[str] = None, platform: Optional[str] = None):
    """
    发送指定店铺的订单汇总
    
    参数：
    - store_name: 店铺名称
    - date: 日期 YYYY-MM-DD（可选，默认昨天）
    - platform: 平台 ('panda', 'deliveroo'，不指定则查询所有平台)
    
    示例：
    # 所有平台
    curl -X POST "http://localhost:8000/reminder/store-summary?store_name=Battersea&date=2025-12-20"
    
    # 仅熊猫外卖
    curl -X POST "http://localhost:8000/reminder/store-summary?store_name=Battersea&date=2025-12-20&platform=panda"
    """
    # 生成店铺汇总报告
    if not date:
        from datetime import timedelta
        date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 标准化平台参数
    if platform:
        platform = platform.lower()
        if platform in ['hungrypanda', 'panda']:
            platform = 'panda'
        elif platform in ['deliveroo', 'roo']:
            platform = 'deliveroo'
    
    summary = report_service.generate_store_summary_text(store_name, date, platform=platform)
    
    # 发送到飞书
    result = feishu_service.send_with_default_webhook(summary)
    
    if result['success']:
        platform_info = f" ({platform})" if platform else ""
        return {
            'status': 'ok',
            'message': f'店铺 {store_name}{platform_info} 的汇总已发送',
            'timestamp': datetime.now().isoformat(),
            'summary': summary
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"发送失败: {result.get('error', 'Unknown error')}"
        )


@router.get("/test")
def test_webhook_config():
    """
    测试 Webhook 配置
    
    返回当前配置状态，但不发送消息
    """
    webhook_url = feishu_service.get_webhook_url()
    
    if webhook_url:
        # 隐藏部分 URL 以保护隐私
        masked_url = webhook_url[:50] + "..." if len(webhook_url) > 50 else webhook_url
        return {
            'status': 'configured',
            'webhook_url': masked_url,
            'message': 'Webhook 已配置'
        }
    else:
        return {
            'status': 'not_configured',
            'message': '未配置 FEISHU_WEBHOOK_URL 环境变量'
        }


@router.post("/test-send")
def test_send():
    """
    测试发送消息
    
    发送一条测试消息到配置的 webhook
    """
    test_message = f"""🔔 测试消息

这是一条测试消息，用于验证飞书 Webhook 配置是否正确。

⏰ 发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
✅ 如果你看到这条消息，说明配置成功！"""
    
    result = feishu_service.send_with_default_webhook(test_message)
    
    if result['success']:
        return {
            'status': 'ok',
            'message': '测试消息已发送',
            'timestamp': datetime.now().isoformat()
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"发送失败: {result.get('error', 'Unknown error')}"
        )
