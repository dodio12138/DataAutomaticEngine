"""飞书请求签名验证器"""
import hashlib
import hmac
import os
from typing import Optional


class SignatureVerifier:
    """
    飞书请求签名验证器
    用于验证飞书推送的事件是否真实可信
    """
    
    def __init__(self, encrypt_key: Optional[str] = None):
        """
        初始化签名验证器
        
        参数：
        - encrypt_key: 飞书应用的 Encrypt Key（可选，默认从环境变量读取）
        """
        self.encrypt_key = encrypt_key or os.environ.get("FEISHU_ENCRYPT_KEY", "")
    
    def verify(self, timestamp: str, nonce: str, encrypt_key: str, signature: str, body: str = "") -> bool:
        """
        验证飞书请求签名
        
        参数：
        - timestamp: 时间戳（从请求头 X-Lark-Request-Timestamp 获取）
        - nonce: 随机字符串（从请求头 X-Lark-Request-Nonce 获取）
        - encrypt_key: Encrypt Key
        - signature: 签名（从请求头 X-Lark-Signature 获取）
        - body: 请求体（加密消息需要包含在签名中）
        
        返回：
        - bool: 签名是否有效
        """
        if not encrypt_key:
            # 如果没有配置 Encrypt Key，跳过验证（开发环境）
            print("⚠️  未配置 FEISHU_ENCRYPT_KEY，跳过签名验证")
            return True
        
        # 拼接签名字符串（加密消息需要加上body）
        if body:
            sign_string = f"{timestamp}{nonce}{encrypt_key}{body}"
        else:
            sign_string = f"{timestamp}{nonce}{encrypt_key}"
        
        # 计算签名
        calculated_signature = hashlib.sha256(sign_string.encode()).hexdigest()
        
        # 验证签名
        is_valid = calculated_signature == signature
        
        if not is_valid:
            print(f"❌ 签名验证失败")
            print(f"   签名字符串: {sign_string[:50]}... (长度: {len(sign_string)})")
            print(f"   计算签名: {calculated_signature}")
            print(f"   接收签名: {signature}")
        
        return is_valid
    
    def verify_from_headers(self, headers: dict, body: str) -> bool:
        """
        从请求头和请求体验证签名（便捷方法）
        
        参数：
        - headers: 请求头字典
        - body: 请求体字符串
        
        返回：
        - bool: 签名是否有效
        """
        # 获取签名相关的请求头（兼容小写和标准格式）
        timestamp = headers.get("x-lark-request-timestamp") or headers.get("X-Lark-Request-Timestamp", "")
        nonce = headers.get("x-lark-request-nonce") or headers.get("X-Lark-Request-Nonce", "")
        signature = headers.get("x-lark-signature") or headers.get("X-Lark-Signature", "")
        
        # 如果没有签名信息，可能是开发测试环境
        if not timestamp or not nonce or not signature:
            print("⚠️  请求中缺少签名信息，跳过验证（可能是测试请求）")
            return True
        
        # 打印验证信息（用于调试）
        print(f"🔐 开始验证签名:")
        print(f"   Timestamp: {timestamp}")
        print(f"   Nonce: {nonce}")
        print(f"   Signature: {signature}")
        print(f"   Body Length: {len(body)}")
        print(f"   Encrypt Key: {self.encrypt_key[:10]}..." if len(self.encrypt_key) > 10 else f"   Encrypt Key: {self.encrypt_key}")
        
        result = self.verify(timestamp, nonce, self.encrypt_key, signature, body)
        
        if result:
            print("✅ 签名验证通过")
        
        return result
