"""飞书消息发送服务（使用官方 SDK）"""
import os
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from typing import Optional


class FeishuMessageSender:
    """
    飞书消息发送服务（基于官方 SDK）
    用于主动发送消息到群聊或私聊
    """
    
    def __init__(self):
        self.app_id = os.environ.get("FEISHU_APP_ID", "")
        self.app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        
        if self.app_id and self.app_secret:
            # 初始化飞书客户端
            self.client = lark.Client.builder() \
                .app_id(self.app_id) \
                .app_secret(self.app_secret) \
                .log_level(lark.LogLevel.DEBUG) \
                .build()
            print(f"✅ 飞书 SDK 客户端初始化成功")
        else:
            self.client = None
            print(f"⚠️  未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
    
    def send_text_message(self, chat_id: str, text: str, message_id: Optional[str] = None) -> bool:
        """
        发送文本消息到群聊或私聊
        
        参数：
        - chat_id: 群聊或私聊的 ID（chat_id 或 open_id）
        - text: 消息文本
        - message_id: 回复的消息 ID（可选）
        
        返回：
        - bool: 是否发送成功
        """
        if not self.client:
            print("❌ 飞书客户端未初始化")
            return False
        
        try:
            # 确定接收者类型
            if chat_id.startswith("oc_"):
                receive_id_type = "chat_id"
            elif chat_id.startswith("ou_"):
                receive_id_type = "open_id"
            else:
                print(f"⚠️  未知的 ID 格式: {chat_id}，默认使用 chat_id")
                receive_id_type = "chat_id"
            
            # 构建消息内容
            content = lark.JSON.marshal({
                "text": text
            })
            
            print(f"📤 使用飞书 SDK 发送消息到 {chat_id}")
            print(f"   接收者类型: {receive_id_type}")
            print(f"   内容: {text[:100]}...")
            
            # 构建请求
            request = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("text")
                    .content(content)
                    .build()
                ) \
                .build()
            
            # 如果是回复消息，添加 reply 字段
            if message_id:
                # 注意：SDK 的回复消息方式可能需要使用 ReplyMessageRequest
                pass
            
            # 发送消息
            response = self.client.im.v1.message.create(request)
            
            # 检查响应
            if not response.success():
                print(f"❌ 消息发送失败")
                print(f"   错误码: {response.code}")
                print(f"   错误信息: {response.msg}")
                print(f"   请求ID: {response.request_id}")
                return False
            
            print(f"✅ 消息发送成功")
            print(f"   消息ID: {response.data.message_id}")
            return True
        
        except Exception as e:
            print(f"❌ 发送消息异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def reply_message(self, message_id: str, text: str) -> bool:
        """
        回复指定消息
        
        参数：
        - message_id: 要回复的消息 ID
        - text: 回复内容
        
        返回：
        - bool: 是否发送成功
        """
        if not self.client:
            print("❌ 飞书客户端未初始化")
            return False
        
        try:
            # 构建消息内容
            content = lark.JSON.marshal({
                "text": text
            })
            
            print(f"📤 使用飞书 SDK 回复消息 {message_id}")
            print(f"   内容: {text[:100]}...")
            
            # 构建请求
            request = ReplyMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(
                    ReplyMessageRequestBody.builder()
                    .content(content)
                    .msg_type("text")
                    .build()
                ) \
                .build()
            
            # 发送消息
            response = self.client.im.v1.message.reply(request)
            
            # 检查响应
            if not response.success():
                print(f"❌ 回复消息失败")
                print(f"   错误码: {response.code}")
                print(f"   错误信息: {response.msg}")
                print(f"   请求ID: {response.request_id}")
                return False
            
            print(f"✅ 回复消息成功")
            print(f"   消息ID: {response.data.message_id}")
            return True
        
        except Exception as e:
            print(f"❌ 回复消息异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def send_card_message(self, chat_id: str, card_content: dict, message_id: Optional[str] = None) -> bool:
        """
        发送卡片消息到群聊或私聊
        
        参数：
        - chat_id: 群聊或私聊的 ID
        - card_content: 卡片内容（字典格式）
        - message_id: 回复的消息 ID（可选）
        
        返回：
        - bool: 是否发送成功
        """
        if not self.client:
            print("❌ 飞书客户端未初始化")
            return False
        
        try:
            # 确定接收者类型
            if chat_id.startswith("oc_"):
                receive_id_type = "chat_id"
            elif chat_id.startswith("ou_"):
                receive_id_type = "open_id"
            else:
                receive_id_type = "chat_id"
            
            # 构建卡片内容
            content = lark.JSON.marshal(card_content)
            
            print(f"📤 使用飞书 SDK 发送卡片消息到 {chat_id}")
            
            # 构建请求
            request = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type) \
                .request_body(
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("interactive")
                    .content(content)
                    .build()
                ) \
                .build()
            
            # 发送消息
            response = self.client.im.v1.message.create(request)
            
            # 检查响应
            if not response.success():
                print(f"❌ 卡片消息发送失败")
                print(f"   错误码: {response.code}")
                print(f"   错误信息: {response.msg}")
                return False
            
            print(f"✅ 卡片消息发送成功")
            return True
        
        except Exception as e:
            print(f"❌ 发送卡片消息异常: {e}")
            import traceback
            traceback.print_exc()
            return False

