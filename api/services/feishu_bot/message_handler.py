"""飞书消息处理器"""
import json
from typing import Dict, Optional
from .command_parser import CommandParser
from .responder import Responder
from .message_sender import FeishuMessageSender


class MessageHandler:
    """
    飞书消息处理器
    负责接收飞书回调事件，解析消息内容，并协调命令执行和响应
    """
    
    def __init__(self):
        self.command_parser = CommandParser()
        self.responder = Responder()
        self.message_sender = FeishuMessageSender()
    
    def handle_event(self, event_data: Dict) -> Optional[Dict]:
        """
        处理飞书事件回调
        
        参数：
        - event_data: 飞书推送的事件数据
        
        返回：
        - Dict: 响应数据（用于即时回复）或 None
        """
        # 兼容两种事件格式：
        # 1. 新版格式（schema 2.0）：event_type 在 header 中
        # 2. 旧版格式（加密消息解密后）：type 在根级别
        
        # 获取事件类型（兼容新旧格式）
        event_type = event_data.get('type', '')  # 旧版格式
        if not event_type:
            event_type = event_data.get('header', {}).get('event_type', '')  # 新版格式
        
        # URL验证事件（飞书webhook配置时的验证）
        if event_type == 'url_verification':
            return self._handle_url_verification(event_data)
        
        # 接收消息事件
        if event_type == 'im.message.receive_v1':
            return self._handle_message_receive(event_data)
        
        # 其他事件类型可以在这里扩展
        print(f"⚠️  未处理的事件类型: {event_type}")
        return None
    
    def _handle_url_verification(self, event_data: Dict) -> Dict:
        """
        处理URL验证（飞书webhook配置时触发）
        
        参数：
        - event_data: 验证事件数据
        
        返回：
        - Dict: 包含challenge的响应
        """
        challenge = event_data.get('challenge', '')
        return {'challenge': challenge}
    
    def _handle_message_receive(self, event_data: Dict) -> Optional[Dict]:
        """
        处理接收到的消息
        
        参数：
        - event_data: 消息事件数据
        
        返回：
        - Dict: 空响应（消息通过 API 主动发送）
        """
        try:
            event = event_data.get('event', {})
            
            # 打印事件结构（用于调试）
            print(f"📩 处理消息事件，event 字段: {json.dumps(event, ensure_ascii=False)[:200]}...")
            
            # 获取消息内容
            message = event.get('message', {})
            message_type = message.get('message_type', '')
            content = message.get('content', '{}')
            chat_id = message.get('chat_id', '')
            
            print(f"📝 消息类型: {message_type}, Chat ID: {chat_id}")
            print(f"   内容: {content[:100]}...")
            
            # 解析消息内容
            if message_type == 'text':
                content_data = json.loads(content)
                text = content_data.get('text', '').strip()
                print(f"💬 解析后的文本: {text}")
            else:
                # 暂不处理其他类型消息
                print(f"⚠️  跳过非文本消息: {message_type}")
                return None
            
            # 获取发送者信息
            sender = event.get('sender', {})
            sender_id = sender.get('sender_id', {}).get('user_id', '')
            
            # 获取消息ID（用于回复）
            message_id = message.get('message_id', '')
            
            print(f"👤 发送者: {sender_id}, 消息ID: {message_id}")
            
            # 解析命令
            command = self.command_parser.parse(text)
            
            if not command:
                # 无法识别的命令，发送帮助信息
                print(f"❓ 无法识别的命令: {text}")
                response_content = self.responder.create_help_response()
                response_text = response_content.get('content', {}).get('text', '帮助信息')
                self.message_sender.send_text_message(chat_id, response_text, message_id)
                return None
            
            print(f"✅ 识别命令: {command}")
            
            # 执行命令并生成响应
            response_content = self._execute_command(command, sender_id, message_id)
            
            # 提取响应文本
            response_text = response_content.get('content', {}).get('text', '')
            
            if response_text:
                # 主动发送消息到群聊
                self.message_sender.send_text_message(chat_id, response_text, message_id)
            
            # 返回空响应（已通过 API 发送消息）
            return None
            
        except Exception as e:
            print(f"❌ 处理消息时出错: {e}")
            import traceback
            traceback.print_exc()
            
            # 尝试发送错误消息
            try:
                error_response = self.responder.create_error_response(str(e))
                error_text = error_response.get('content', {}).get('text', f'处理出错：{e}')
                if chat_id:
                    self.message_sender.send_text_message(chat_id, error_text)
            except:
                pass
            
            return None
    
    def _execute_command(self, command: Dict, sender_id: str, message_id: str) -> Dict:
        """
        执行命令并生成响应
        
        参数：
        - command: 解析后的命令字典
        - sender_id: 发送者ID
        - message_id: 消息ID
        
        返回：
        - Dict: 响应消息
        """
        command_type = command.get('type')
        params = command.get('params', {})
        
        # 根据命令类型分发处理
        if command_type == 'query_orders':
            return self.responder.create_order_query_response(params)
        
        elif command_type == 'daily_summary':
            return self.responder.create_daily_summary_response(params)
        
        elif command_type == 'store_summary':
            return self.responder.create_store_summary_response(params)
        
        elif command_type == 'help':
            return self.responder.create_help_response()
        
        else:
            return self.responder.create_unknown_command_response()
