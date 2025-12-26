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
        # 注意：匹配顺序很重要！具体的模式要放在通用模式之前
        self.patterns = {
            'store_summary': [
                # 店铺查询必须放在最前面，避免被其他模式误匹配
                # 支持"查询 店铺名 日期"格式（日期范围）
                r'查询\s*(.+?)\s*(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})',
                r'查询\s*(.+?)\s*(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})',
                r'查询\s*(.+?)\s*(\d{4}-\d{2}-\d{2})\s*到\s*(\d{4}-\d{2}-\d{2})',
                # 支持"查询 店铺名 日期"格式（单日期）
                r'查询\s*(.+?)\s*(\d{4}-\d{2}-\d{2})',
                # 支持"英文店铺名 日期"格式（不带"店"字）- 日期范围
                r'([a-zA-Z]\w+)\s+(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})',
                r'([a-zA-Z]\w+)\s+(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})',
                r'([a-zA-Z]\w+)\s+(\d{4}-\d{2}-\d{2})\s*到\s*(\d{4}-\d{2}-\d{2})',
                # 支持"英文店铺名 日期"格式（不带"店"字）- 单日期
                r'([a-zA-Z]\w+)\s+(\d{4}-\d{2}-\d{2})',
                # 支持日期范围：某店铺 2025-12-20至2025-12-24
                r'(.+店|.+店铺).*?(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})',
                r'(.+店|.+店铺).*?(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})',
                r'(.+店|.+店铺).*?(\d{4}-\d{2}-\d{2})\s*到\s*(\d{4}-\d{2}-\d{2})',
                r'(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2}).*?(.+店|.+店铺)',
                r'(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2}).*?(.+店|.+店铺)',
                r'(\d{4}-\d{2}-\d{2})\s*到\s*(\d{4}-\d{2}-\d{2}).*?(.+店|.+店铺)',
                # 单个日期：某店铺2025-12-22
                r'(.+店|.+店铺).*?(\d{4}-\d{2}-\d{2})',
                r'(\d{4}-\d{2}-\d{2}).*?(.+店|.+店铺)',
            ],
            'query_orders': [
                r'(\d{4}-\d{2}-\d{2}).*?订单',  # 2025-12-22订单
            ],
            'daily_summary': [
                # 支持日期范围：2025-12-20至2025-12-24
                r'(\d{4}-\d{2}-\d{2})\s*至\s*(\d{4}-\d{2}-\d{2})',
                r'(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})',
                r'(\d{4}-\d{2}-\d{2})\s+到\s+(\d{4}-\d{2}-\d{2})',
                # 单个日期：2025-12-24
                r'(\d{4}-\d{2}-\d{2})',
                # 时间关键词
                r'(昨[天日]|今[天日]|前[天日]).*?(汇总|报告|数据|订单)',
                r'汇总.*?(昨[天日]|今[天日]|前[天日])',
                r'每日汇总',
                r'(昨[天日]|今[天日]|前[天日])',  # 支持单独的时间词
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
            groups = match.groups()
            # 检查是否有日期范围（两个日期）
            dates = [g for g in groups if g and re.match(r'\d{4}-\d{2}-\d{2}', g)]
            if len(dates) >= 2:
                params['start_date'] = dates[0]
                params['end_date'] = dates[1]
            elif len(dates) == 1:
                params['start_date'] = dates[0]
                params['end_date'] = dates[0]
            else:
                # 解析时间关键词
                time_word = groups[0] if groups and groups[0] else None
                parsed_date = self._parse_time_word(time_word)
                params['start_date'] = parsed_date
                params['end_date'] = parsed_date
        
        elif command_type == 'store_summary':
            # 提取店铺名和日期（支持日期范围）
            groups = match.groups()
            dates = []
            store_name = None
            
            for group in groups:
                if group and re.match(r'\d{4}-\d{2}-\d{2}', group):
                    dates.append(group)
                elif group and '店' in group:
                    store_name = group.replace('店铺', '').replace('店', '').strip()
                elif group and group.strip() and not re.match(r'\d{4}-\d{2}-\d{2}', group):
                    # 非日期的文本视为店铺名（如英文店铺名或中文店铺名）
                    store_name = group.strip()
            
            if store_name and store_name != '':
                params['store_name'] = store_name
            
            if len(dates) >= 2:
                params['start_date'] = dates[0]
                params['end_date'] = dates[1]
            elif len(dates) == 1:
                params['start_date'] = dates[0]
                params['end_date'] = dates[0]
        
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
