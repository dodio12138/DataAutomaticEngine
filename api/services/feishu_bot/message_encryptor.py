"""飞书消息加密解密器"""
import base64
import hashlib
import json
import os
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from typing import Optional


class MessageEncryptor:
    """
    飞书消息加密解密器
    用于处理飞书发送的加密消息
    
    飞书加密算法：AES-256-CBC
    - Key: SHA256(Encrypt Key)
    - IV: Key 的前 16 字节
    """
    
    def __init__(self, encrypt_key: Optional[str] = None):
        """
        初始化加密解密器
        
        参数：
        - encrypt_key: 飞书应用的 Encrypt Key（可选，默认从环境变量读取）
        """
        self.encrypt_key = encrypt_key or os.environ.get("FEISHU_ENCRYPT_KEY", "")
        
        if self.encrypt_key:
            # 计算 AES Key（SHA256 哈希）
            self.aes_key = hashlib.sha256(self.encrypt_key.encode()).digest()
        else:
            self.aes_key = None
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        解密飞书加密消息
        
        飞书加密格式：base64(iv + encrypted_event)
        - 前 16 字节是随机生成的 IV
        - 后续是 AES-256-CBC 加密的事件内容
        
        参数：
        - encrypted_text: Base64 编码的加密文本
        
        返回：
        - str: 解密后的明文 JSON 字符串
        
        异常：
        - ValueError: 解密失败时抛出
        """
        if not self.encrypt_key:
            raise ValueError("未配置 FEISHU_ENCRYPT_KEY，无法解密消息")
        
        try:
            # Base64 解码
            encrypted_data = base64.b64decode(encrypted_text)
            
            # 提取 IV（前 16 字节）
            iv = encrypted_data[:16]
            
            # 提取加密的事件内容（剩余字节）
            encrypted_event = encrypted_data[16:]
            
            # AES-256-CBC 解密
            cipher = AES.new(self.aes_key, AES.MODE_CBC, iv)
            decrypted_bytes = cipher.decrypt(encrypted_event)
            
            # 去除 PKCS7 填充
            decrypted_bytes = unpad(decrypted_bytes, AES.block_size)
            
            # 转换为字符串
            decrypted_text = decrypted_bytes.decode('utf-8')
            
            print(f"✅ 解密成功，明文长度: {len(decrypted_text)} 字符")
            
            return decrypted_text
        
        except Exception as e:
            print(f"❌ 解密详细错误: {type(e).__name__}: {e}")
            raise ValueError(f"消息解密失败: {e}")
    
    def decrypt_event(self, event_data: dict) -> dict:
        """
        解密飞书事件数据
        
        如果事件包含 encrypt 字段，则解密；否则原样返回
        
        参数：
        - event_data: 飞书事件数据字典
        
        返回：
        - dict: 解密后的事件数据
        """
        # 检查是否是加密消息
        if "encrypt" not in event_data:
            # 明文消息，直接返回
            return event_data
        
        # 加密消息，需要解密
        encrypted_text = event_data["encrypt"]
        
        print(f"🔓 检测到加密消息，正在解密...")
        print(f"   加密文本长度: {len(encrypted_text)} 字符")
        
        try:
            # 解密
            decrypted_text = self.decrypt(encrypted_text)
            
            # 解析 JSON
            decrypted_data = json.loads(decrypted_text)
            
            print(f"✅ 消息解密成功")
            
            return decrypted_data
        
        except Exception as e:
            print(f"❌ 消息解密失败: {e}")
            raise
    
    def verify_and_decrypt(self, headers: dict, body: str, event_data: dict) -> dict:
        """
        验证签名并解密消息（组合操作）
        
        参数：
        - headers: 请求头
        - body: 原始请求体字符串（完整的 JSON 字符串）
        - event_data: 解析后的事件数据
        
        返回：
        - dict: 解密后的事件数据
        """
        # 对于加密消息，签名算法：SHA256(timestamp + nonce + encrypt_key + body)
        # 注意：body 是完整的 JSON 字符串，不是只有 encrypt 字段
        
        timestamp = headers.get("x-lark-request-timestamp") or headers.get("X-Lark-Request-Timestamp", "")
        nonce = headers.get("x-lark-request-nonce") or headers.get("X-Lark-Request-Nonce", "")
        signature = headers.get("x-lark-signature") or headers.get("X-Lark-Signature", "")
        
        if timestamp and nonce and signature and "encrypt" in event_data:
            # 有签名信息，且是加密消息
            
            # 计算签名：timestamp + nonce + encrypt_key + body（完整JSON）
            sign_string = f"{timestamp}{nonce}{self.encrypt_key}{body}"
            calculated_signature = hashlib.sha256(sign_string.encode()).hexdigest()
            
            print(f"🔐 验证加密消息签名:")
            print(f"   Timestamp: {timestamp}")
            print(f"   Nonce: {nonce}")
            print(f"   Body 长度: {len(body)}")
            print(f"   签名字符串长度: {len(sign_string)}")
            
            if calculated_signature != signature:
                print(f"❌ 签名验证失败")
                print(f"   计算签名: {calculated_signature}")
                print(f"   接收签名: {signature}")
                raise ValueError("签名验证失败")
            
            print(f"✅ 签名验证通过")
        
        # 解密消息
        return self.decrypt_event(event_data)
