"""飞书响应生成器"""
from typing import Dict, Optional
from services import report_service


class Responder:
    """
    响应生成器
    负责根据命令执行结果生成飞书消息响应
    """
    
    def generate_response(self, command: Optional[Dict]) -> Optional[Dict]:
        """
        根据命令生成响应（统一入口）
        
        参数：
        - command: 命令字典，包含 type 和 params
        
        返回：
        - Dict: 飞书消息响应，如果失败返回 None
        """
        if not command:
            return self.create_unknown_command_response()
        
        command_type = command.get('type')
        params = command.get('params', {})
        
        # 根据命令类型调用对应的响应生成器
        if command_type == 'query_orders':
            return self.create_order_query_response(params)
        elif command_type == 'daily_summary':
            return self.create_daily_summary_response(params)
        elif command_type == 'store_summary':
            return self.create_store_summary_response(params)
        elif command_type == 'help':
            return self.create_help_response()
        else:
            return self.create_unknown_command_response()
    
    def create_order_query_response(self, params: Dict) -> Dict:
        """
        创建订单查询响应
        
        参数：
        - params: 查询参数（包含date, platform等）
        
        返回：
        - Dict: 飞书消息响应
        """
        date = params.get('date')
        platform = params.get('platform')
        
        if not date:
            return self._create_text_response("❌ 请指定查询日期，例如：查询2025-12-22")
        
        # 查询订单数据
        result = report_service.query_order_summary(date, platform=platform)
        
        if not result['success']:
            return self._create_text_response(f"❌ {result['message']}")
        
        # 生成汇总文本
        summary_text = report_service.generate_daily_summary_text(date, platform=platform)
        
        return self._create_text_response(summary_text)
    
    def create_daily_summary_response(self, params: Dict) -> Dict:
        """
        创建每日汇总响应
        
        参数：
        - params: 参数（包含 start_date, end_date, platform 或 date）
        
        返回：
        - Dict: 飞书消息响应
        """
        # 支持新的 start_date/end_date 和旧的 date 参数
        start_date = params.get('start_date') or params.get('date')
        end_date = params.get('end_date')
        platform = params.get('platform')
        
        # 生成汇总报告
        summary_text = report_service.generate_daily_summary_text(start_date, end_date, platform)
        
        return self._create_text_response(summary_text)
    
    def create_store_summary_response(self, params: Dict) -> Dict:
        """
        创建店铺汇总响应
        
        参数：
        - params: 参数（包含 store_name, start_date, end_date, platform 或 date）
        
        返回：
        - Dict: 飞书消息响应
        """
        store_name = params.get('store_name', '').strip()
        start_date = params.get('start_date') or params.get('date')
        end_date = params.get('end_date')
        platform = params.get('platform')
        
        if not store_name or store_name == '':
            return self._create_text_response("❌ 请指定店铺名称")
        
        if not start_date:
            return self._create_text_response("❌ 请指定查询日期")
        
        # 生成店铺汇总
        summary_text = report_service.generate_store_summary_text(store_name, start_date, end_date, platform)
        
        return self._create_text_response(summary_text)
    
    def create_help_response(self) -> Dict:
        """
        创建帮助信息响应
        
        返回：
        - Dict: 飞书消息响应
        """
        help_text = """🤖 海底捞订单查询机器人

📌 支持的命令：

1️⃣ **每日汇总（支持日期范围）**
   • 昨天汇总 / 今天数据
   • 2025-12-24 （单日汇总）
   • 2025-12-20至2025-12-24 （多日汇总）
   • 2025-12-20-2025-12-24
   • 2025-12-20到2025-12-24

2️⃣ **店铺查询（支持日期范围）**
   单日查询：
   • Piccadilly店 2025-12-22
   • battersea 2025-12-22
   • 查询 Piccadilly 2025-12-22
   
   多日查询：
   • Battersea店 2025-12-20至2025-12-24
   • battersea 2025-12-20-2025-12-24
   • 查询 巴特西 2025-12-20到2025-12-24
   • 2025-12-20至2025-12-24 Battersea店

3️⃣ **查询订单数据**
   • 2025-12-22订单

4️⃣ **帮助信息**
   • 帮助 / help

🌐 **平台筛选（可选）**
   在任何查询命令后添加平台关键词：
   • panda / 熊猫 / 🐼 → 仅查询 HungryPanda
   • deliveroo / roo / 袋鼠 / 🦘 → 仅查询 Deliveroo
   • 不指定 → 查询所有平台
   
   示例：
   • 昨天汇总 panda （仅 HungryPanda）
   • Battersea店 2025-12-24 deliveroo （仅 Deliveroo）
   • 2025-12-24 （所有平台）

💡 提示：
   • 日期格式：YYYY-MM-DD
   • 多日查询会显示数据汇总和每日趋势
   • 支持中文/英文店铺名模糊匹配
   • 日期分隔符：至、-、到
   • 平台筛选支持多种关键词

🐼 数据来源：HungryPanda / 🦘 Deliveroo"""
        
        return self._create_text_response(help_text)
    
    def create_error_response(self, error_msg: str) -> Dict:
        """
        创建错误响应
        
        参数：
        - error_msg: 错误消息
        
        返回：
        - Dict: 飞书消息响应
        """
        return self._create_text_response(f"❌ 处理出错：{error_msg}")
    
    def create_unknown_command_response(self) -> Dict:
        """
        创建未知命令响应
        
        返回：
        - Dict: 飞书消息响应
        """
        return self._create_text_response(
            "❓ 无法识别的命令，发送「帮助」查看支持的命令"
        )
    
    def _create_text_response(self, text: str) -> Dict:
        """
        创建文本消息响应（即时回复格式）
        
        参数：
        - text: 响应文本
        
        返回：
        - Dict: 飞书即时回复格式
        
        飞书即时回复格式说明：
        - 必须在 1 秒内返回
        - 返回格式：{"content": {"text": "消息内容"}}
        - 注意：不需要 msg_type 字段
        """
        return {
            "content": {
                "text": text
            }
        }
