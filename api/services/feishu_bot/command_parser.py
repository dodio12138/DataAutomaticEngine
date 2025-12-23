"""飞书命令解析器"""
import re
from typing import Optional, Dict
from datetime import datetime, timedelta


class CommandParser:
    """
    命令解析器
    负责解析用户输入的文本，识别命令和参数
    """
    
    def __init__(self):
        # 定义命令模式（可扩展）
        self.patterns = {
            'query_orders': [
                r'查询.*?(\d{4}-\d{2}-\d{2})',  # 查询2025-12-22
                r'(\d{4}-\d{2}-\d{2}).*?订单',  # 2025-12-22订单
            ],
            'daily_summary': [
                r'(昨[天日]|今[天日]|前[天日]).*?(汇总|报告|数据|订单)',
                r'汇总.*?(昨[天日]|今[天日]|前[天日])',
                r'每日汇总',
                r'(昨[天日]|今[天日]|前[天日])',  # 支持单独的时间词
            ],
            'store_summary': [
                r'(.+店|.+店铺).*?(\d{4}-\d{2}-\d{2})',  # 某店铺2025-12-22
                r'(\d{4}-\d{2}-\d{2}).*?(.+店|.+店铺)',  # 2025-12-22某店铺
            ],
            'help': [
                r'(帮助|help|\?|？)',  # 移除^$，允许部分匹配
                r'怎么用',
                r'如何使用',
                r'有什么功能',
                r'指令|命令',
            ],
        }
    
    def parse(self, text: str) -> Optional[Dict]:
        """
        解析用户输入的文本
        
        参数：
        - text: 用户输入的文本
        
        返回：
        - Dict: 解析后的命令字典，包含 type 和 params
        - None: 无法识别的命令
        """
        # 清理文本：移除@提及标记（如 @_user_1）
        text = re.sub(r'@_user_\d+\s*', '', text)
        text = re.sub(r'@\S+\s*', '', text)  # 移除任何@标记
        text = text.strip()
        
        if not text:
            return None
        
        # 尝试匹配各种命令模式
        for command_type, patterns in self.patterns.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    params = self._extract_params(command_type, match, text)
                    return {
                        'type': command_type,
                        'params': params,
                        'raw_text': text
                    }
        
        return None
    
    def _extract_params(self, command_type: str, match, text: str) -> Dict:
        """
        从正则匹配结果中提取命令参数
        
        参数：
        - command_type: 命令类型
        - match: 正则匹配对象
        - text: 原始文本
        
        返回：
        - Dict: 参数字典
        """
        params = {}
        
        if command_type == 'query_orders':
            # 提取日期
            if match.group(1):
                params['date'] = match.group(1)
        
        elif command_type == 'daily_summary':
            # 解析时间关键词
            time_word = match.group(1) if match.groups() else None
            params['date'] = self._parse_time_word(time_word)
        
        elif command_type == 'store_summary':
            # 提取店铺名和日期
            groups = match.groups()
            for group in groups:
                if re.match(r'\d{4}-\d{2}-\d{2}', group):
                    params['date'] = group
                elif '店' in group:
                    params['store_name'] = group.replace('店铺', '').replace('店', '')
        
        return params
    
    def _parse_time_word(self, time_word: Optional[str]) -> str:
        """
        将时间关键词转换为具体日期
        
        参数：
        - time_word: 时间关键词（昨天、今天、前天）
        
        返回：
        - str: YYYY-MM-DD格式的日期
        """
        today = datetime.now().date()
        
        if not time_word:
            # 默认昨天
            date = today - timedelta(days=1)
        elif '昨' in time_word:
            date = today - timedelta(days=1)
        elif '今' in time_word:
            date = today
        elif '前' in time_word:
            date = today - timedelta(days=2)
        else:
            date = today - timedelta(days=1)
        
        return date.strftime('%Y-%m-%d')
