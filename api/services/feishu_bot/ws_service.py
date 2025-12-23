"""飞书长链接（WebSocket）事件订阅服务"""
import os
import asyncio
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
from .command_parser import CommandParser
from .responder import Responder
from .message_sender import FeishuMessageSender


class FeishuWebSocketService:
    """
    飞书长链接服务
    通过 WebSocket 订阅事件，实时接收用户消息
    """
    
    def __init__(self):
        self.app_id = os.environ.get("FEISHU_APP_ID", "")
        self.app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        self.encrypt_key = os.environ.get("FEISHU_ENCRYPT_KEY", "")
        self.verification_token = os.environ.get("FEISHU_VERIFICATION_TOKEN", "")
        
        # 初始化消息处理组件
        self.command_parser = CommandParser()
        self.responder = Responder()
        self.message_sender = FeishuMessageSender()
        
        # 初始化飞书客户端（用于发送消息）
        if self.app_id and self.app_secret:
            self.client = lark.Client.builder() \
                .app_id(self.app_id) \
                .app_secret(self.app_secret) \
                .log_level(lark.LogLevel.DEBUG) \
                .build()
            
            # 定义消息接收处理函数
            def do_p2_im_message_receive_v1(data: P2ImMessageReceiveV1) -> None:
                """处理接收到的消息事件"""
                print(f"\n{'='*60}")
                print(f"📨 收到飞书消息事件（长链接）")
                
                try:
                    # 获取消息内容
                    message = data.event.message
                    sender = data.event.sender
                    
                    message_id = message.message_id
                    chat_id = message.chat_id
                    chat_type = message.chat_type
                    message_type = message.message_type
                    content_json = message.content
                    
                    print(f"   消息ID: {message_id}")
                    print(f"   群聊ID: {chat_id}")
                    print(f"   聊天类型: {chat_type}")
                    print(f"   消息类型: {message_type}")
                    
                    # 只处理文本消息
                    if message_type != "text":
                        print(f"⚠️  忽略非文本消息: {message_type}")
                        return
                    
                    # 解析消息内容
                    import json
                    try:
                        content_dict = json.loads(content_json)
                        text = content_dict.get("text", "").strip()
                        print(f"   内容: {text}")
                    except:
                        print(f"❌ 无法解析消息内容")
                        return
                    
                    if not text:
                        print(f"⚠️  消息内容为空")
                        return
                    
                    # 解析命令
                    print(f"🔍 解析命令...")
                    command = self.command_parser.parse(text)
                    
                    if not command:
                        print(f"⚠️  未识别的命令")
                        # 回复帮助信息
                        response_text = "我没听懂呢 🤔 发送「帮助」查看可用命令"
                    else:
                        print(f"✅ 识别命令: {command}")
                        
                        # 生成响应
                        print(f"💭 生成响应...")
                        response = self.responder.generate_response(command)
                        
                        if not response:
                            print(f"❌ 无法生成响应")
                            response_text = "抱歉，处理您的请求时出现了问题 😢"
                        else:
                            # 提取响应文本
                            response_text = response.get("content", {}).get("text", "")
                            if not response_text:
                                print(f"❌ 响应内容为空")
                                response_text = "抱歉，生成响应时出现了问题 😢"
                    
                    # 发送响应
                    print(f"📤 发送响应...")
                    print(f"   响应内容: {response_text[:100]}...")
                    
                    # 构建响应内容
                    content = json.dumps({"text": response_text})
                    
                    # 根据聊天类型选择发送方式
                    if chat_type == "p2p":
                        # 私聊：使用 create message API
                        request = CreateMessageRequest.builder() \
                            .receive_id_type("chat_id") \
                            .request_body(
                                CreateMessageRequestBody.builder()
                                .receive_id(chat_id)
                                .msg_type("text")
                                .content(content)
                                .build()
                            ) \
                            .build()
                        
                        response_obj = self.client.im.v1.message.create(request)
                        
                        if not response_obj.success():
                            print(f"❌ 消息发送失败")
                            print(f"   错误码: {response_obj.code}")
                            print(f"   错误信息: {response_obj.msg}")
                        else:
                            print(f"✅ 消息已发送")
                    
                    else:
                        # 群聊：使用 reply message API
                        request = ReplyMessageRequest.builder() \
                            .message_id(message_id) \
                            .request_body(
                                ReplyMessageRequestBody.builder()
                                .content(content)
                                .msg_type("text")
                                .build()
                            ) \
                            .build()
                        
                        response_obj = self.client.im.v1.message.reply(request)
                        
                        if not response_obj.success():
                            print(f"❌ 消息回复失败")
                            print(f"   错误码: {response_obj.code}")
                            print(f"   错误信息: {response_obj.msg}")
                        else:
                            print(f"✅ 消息已回复")
                    
                    print(f"{'='*60}\n")
                
                except Exception as e:
                    print(f"❌ 处理消息异常: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 构建事件分发器
            event_handler = lark.EventDispatcherHandler.builder(
                self.verification_token if self.verification_token else "",
                self.encrypt_key if self.encrypt_key else ""
            ).register_p2_im_message_receive_v1(
                do_p2_im_message_receive_v1
            ).build()
            
            # 创建 WebSocket 客户端
            self.ws_client = lark.ws.Client(
                self.app_id,
                self.app_secret,
                event_handler=event_handler,
                log_level=lark.LogLevel.DEBUG
            )
            
            print(f"✅ 飞书长链接服务初始化成功")
        else:
            self.client = None
            self.ws_client = None
            print(f"❌ 未配置 FEISHU_APP_ID 或 FEISHU_APP_SECRET")
    
    def start(self):
        """
        启动长链接服务
        阻塞式运行，保持 WebSocket 连接
        """
        if not self.ws_client:
            print(f"❌ 无法启动长链接服务：客户端未初始化")
            return
        
        print(f"\n{'='*60}")
        print(f"🚀 启动飞书长链接服务...")
        print(f"   App ID: {self.app_id}")
        print(f"   监听事件: im.message.receive_v1")
        print(f"{'='*60}\n")
        
        try:
            # 启动长链接（阻塞调用）
            self.ws_client.start()
            
        except Exception as e:
            print(f"❌ 长链接服务异常: {e}")
            import traceback
            traceback.print_exc()
    
    async def start_async(self):
        """
        异步启动长链接服务
        用于在 FastAPI 后台任务中运行
        """
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.start)


# 全局长链接服务实例
ws_service = FeishuWebSocketService()

