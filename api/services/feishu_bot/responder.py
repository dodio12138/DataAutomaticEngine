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
        - params: 查询参数（包含date等）
        
        返回：
        - Dict: 飞书消息响应
        """
        date = params.get('date')
        
        if not date:
            return self._create_text_response("❌ 请指定查询日期，例如：查询2025-12-22")
        
        # 查询订单数据
        result = report_service.query_order_summary(date)
        
        if not result['success']:
            return self._create_text_response(f"❌ {result['message']}")
        
        # 生成汇总文本
        summary_text = report_service.generate_daily_summary_text(date)
        
        return self._create_text_response(summary_text)
    
    def create_daily_summary_response(self, params: Dict) -> Dict:
        """
        创建每日汇总响应
        
        参数：
        - params: 参数（包含date等）
        
        返回：
        - Dict: 飞书消息响应
        """
        date = params.get('date')
        
        # 生成汇总报告
        summary_text = report_service.generate_daily_summary_text(date)
        
        return self._create_text_response(summary_text)
    
    def create_store_summary_response(self, params: Dict) -> Dict:
        """
        创建店铺汇总响应
        
        参数：
        - params: 参数（包含store_name和date）
        
        返回：
        - Dict: 飞书消息响应
        """
        store_name = params.get('store_name')
        date = params.get('date')
        
        if not store_name:
            return self._create_text_response("❌ 请指定店铺名称")
        
        if not date:
            return self._create_text_response("❌ 请指定查询日期")
        
        # 生成店铺汇总
        summary_text = report_service.generate_store_summary_text(store_name, date)
        
        return self._create_text_response(summary_text)
    
    def create_help_response(self) -> Dict:
        """
        创建帮助信息响应
        
        返回：
        - Dict: 飞书消息响应
        """
        help_text = """🤖 海底捞订单查询机器人

📌 支持的命令：

1️⃣ **查询订单数据**
   • 查询2025-12-22
   • 2025-12-22订单

2️⃣ **每日汇总**
   • 昨天汇总
   • 今天数据
   • 每日汇总

3️⃣ **店铺查询**
   • Piccadilly店2025-12-22
   • 2025-12-22 Battersea店

4️⃣ **帮助信息**
   • 帮助
   • help

💡 提示：日期格式为 YYYY-MM-DD
🐼 数据来源：熊猫外卖"""
        
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
