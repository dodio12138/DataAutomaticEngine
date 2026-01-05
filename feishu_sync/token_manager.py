#!/usr/bin/env python3
"""
飞书 Tenant Access Token 管理器（应用权限）
"""
import os
import time
import requests
from typing import Optional, Dict


class FeishuTokenManager:
    """飞书 Token 管理器，使用应用权限（tenant_access_token）"""
    
    def __init__(self):
        self.app_id = os.environ.get("FEISHU_APP_ID")
        self.app_secret = os.environ.get("FEISHU_APP_SECRET")
        
        if not self.app_id or not self.app_secret:
            raise ValueError("缺少飞书配置：FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        
        # Token 缓存
        self._access_token = None
        self._token_expire_time = 0
    
    def get_access_token(self) -> str:
        """
        获取有效的 tenant_access_token（应用权限）
        自动缓存并在过期前刷新
        """
        # 检查是否有缓存的 token 且未过期（提前 5 分钟刷新）
        if self._access_token and time.time() < self._token_expire_time - 300:
            return self._access_token
        
        # 获取新的 tenant_access_token
        return self._get_tenant_access_token()
    
    def _get_tenant_access_token(self) -> str:
        """获取 tenant_access_token（应用身份）"""
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json"}
        data = {
            "app_id": self.app_id,
            "app_secret": self.app_secret
        }
        
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        if result.get("code") != 0:
            raise Exception(f"获取 tenant_access_token 失败: {result}")
        
        tenant_token = result.get("tenant_access_token")
        expire_time = result.get("expire", 7200)
        
        self._access_token = tenant_token
        self._token_expire_time = time.time() + expire_time
        
        print(f"✅ 获取应用 token 成功，有效期: {expire_time}秒")
        return tenant_token
