"""飞书机器人回调路由"""
from fastapi import APIRouter, Request, HTTPException
from typing import Dict
import json

from services.feishu_bot import MessageHandler, SignatureVerifier, MessageEncryptor

router = APIRouter(prefix="/feishu/bot", tags=["feishu_bot"])

# 初始化消息处理器和签名验证器
message_handler = MessageHandler()
signature_verifier = SignatureVerifier()
message_encryptor = MessageEncryptor()


@router.post("/callback")
async def feishu_bot_callback(request: Request):
    """
    飞书机器人事件回调接口
    
    飞书会推送各种事件到此接口：
    - URL验证事件（配置webhook时）
    - 消息接收事件（用户发送消息时）
    - 其他事件...
    
    配置步骤：
    1. 在飞书开放平台创建机器人应用
    2. 配置事件订阅，设置请求地址为：http://your-domain/feishu/bot/callback
    3. 订阅「接收消息」事件（im.message.receive_v1）
    4. 发布版本并添加机器人到群聊
    
    返回：
    - Dict: 响应数据（可能包含即时回复的消息）
    """
    try:
        # 获取请求体
        body = await request.body()
        body_str = body.decode('utf-8')
        event_data = json.loads(body_str)
        
        # 打印原始事件（用于调试）
        print(f"📨 收到飞书原始事件: {json.dumps(event_data, ensure_ascii=False, indent=2)}")
        
        # 获取请求头
        headers = dict(request.headers)
        
        # 检查是否是加密消息
        if "encrypt" in event_data:
            # 加密消息：先解密，签名验证在解密过程中完成
            event_data = message_encryptor.verify_and_decrypt(headers, body_str, event_data)
            print(f"✅ 解密后的事件: {json.dumps(event_data, ensure_ascii=False, indent=2)}")
        else:
            # 明文消息：验证签名
            if not signature_verifier.verify_from_headers(headers, body_str):
                print("❌ 签名验证失败，拒绝请求")
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # 处理事件
        response = message_handler.handle_event(event_data)
        
        # 打印响应（用于调试）
        print(f"📤 返回响应: {json.dumps(response, ensure_ascii=False, indent=2)}")
        
        # 返回响应
        if response:
            return response
        else:
            # 空响应表示成功接收但不需要即时回复
            return {"code": 0, "msg": "success"}
    
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    except Exception as e:
        print(f"处理飞书回调时出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def bot_health_check():
    """
    健康检查接口
    
    用于验证机器人服务是否正常运行
    """
    return {
        "status": "ok",
        "service": "feishu_bot",
        "message": "飞书机器人服务运行正常"
    }


@router.post("/test")
async def test_command(text: str):
    """
    测试命令解析接口
    
    用于测试命令解析和响应生成功能，无需实际配置飞书webhook
    
    参数：
    - text: 模拟用户输入的文本
    
    示例：
    curl -X POST "http://localhost:8000/feishu/bot/test?text=查询2025-12-22"
    """
    from services.feishu_bot import CommandParser, Responder
    
    parser = CommandParser()
    responder = Responder()
    
    # 解析命令
    command = parser.parse(text)
    
    if not command:
        return {
            "text": text,
            "command": None,
            "response": responder.create_help_response()
        }
    
    # 模拟执行命令
    command_type = command.get('type')
    params = command.get('params', {})
    
    if command_type == 'query_orders':
        response = responder.create_order_query_response(params)
    elif command_type == 'daily_summary':
        response = responder.create_daily_summary_response(params)
    elif command_type == 'store_summary':
        response = responder.create_store_summary_response(params)
    elif command_type == 'store_rating':
        response = responder.create_store_rating_response(params)
    elif command_type == 'help':
        response = responder.create_help_response()
    else:
        response = responder.create_unknown_command_response()
    
    return {
        "text": text,
        "command": command,
        "response": response
    }
