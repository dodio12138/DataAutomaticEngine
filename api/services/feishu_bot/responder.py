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
        elif command_type == 'store_rating':
            return self.create_store_rating_response(params)
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
    
    def create_store_rating_response(self, params: Dict) -> Dict:
        """
        创建店铺评分响应
        
        参数:
        - params: 参数(包含 store_name)
        
        返回:
        - Dict: 飞书消息响应
        """
        store_name = params.get('store_name', '').strip()
        
        if not store_name or store_name == '':
            return self._create_text_response("❌ 请指定店铺名称")
        
        # 查询店铺评分数据
        result = report_service.query_store_rating(store_name)
        
        if not result['success']:
            return self._create_text_response(f"❌ {result['message']}")
        
        data = result['data']
        
        # 计算提升到下一个0.1等级需要的5星数量
        import math
        current_rating = data['average_rating']
        rating_count = data['rating_count']
        five_star_count = data['five_star_count']
        
        # 计算目标评分(向上取整到下一个0.1)
        # 例如: 4.34 → 4.4, 4.56 → 4.6, 4.62 → 4.7
        target_rating = math.ceil(current_rating * 10) / 10
        
        if target_rating > 5.0:
            target_rating = 5.0
        
        if current_rating >= 5.0:
            needed_five_stars = "已达最高分!"
        elif target_rating == current_rating:
            # 已经是整数级别,计算到下一级
            target_rating = min(target_rating + 0.1, 5.0)
            if target_rating > 5.0:
                needed_five_stars = "已达最高分!"
            else:
                denominator = 5.0 - target_rating
                if denominator <= 0:
                    needed_five_stars = "已接近最高分!"
                else:
                    needed = rating_count * (target_rating - current_rating) / denominator
                    needed_five_stars = f"{int(needed) + 1}个"
        else:
            # 计算公式:(当前评分 * 评论数 + 5 * x) / (评论数 + x) = 目标评分
            # 解方程:x = 评论数 * (目标评分 - 当前评分) / (5 - 目标评分)
            denominator = 5.0 - target_rating
            if denominator <= 0:
                needed_five_stars = "已接近最高分!"
            else:
                needed = rating_count * (target_rating - current_rating) / denominator
                needed_five_stars = f"{int(needed) + 1}个"
        
        # 生成对比信息(如果有前一天数据)
        comparison_text = ""
        if 'previous_data' in data:
            prev = data['previous_data']
            rating_change = current_rating - prev['average_rating']
            review_change = rating_count - prev['rating_count']
            five_star_change = five_star_count - prev['five_star_count']
            one_star_change = data['one_star_count'] - prev['one_star_count']
            
            # 评分变化emoji
            if rating_change > 0:
                rating_emoji = "📈"
                rating_trend = f"+{rating_change:.2f}"
            elif rating_change < 0:
                rating_emoji = "📉"
                rating_trend = f"{rating_change:.2f}"
            else:
                rating_emoji = "➡️"
                rating_trend = "持平"
            
            comparison_text = f"""
📊 昨日变化:
  {rating_emoji} 评分: {rating_trend} (前日 {prev['average_rating']:.2f})
  📝 新增评论: +{review_change} 条
  ⭐ 新增五星: +{five_star_change} 个
  💔 新增一星: +{one_star_change} 个
"""
        
        # 生成响应文本
        response_text = f"""⭐ {data['store_name']} 评分详情

📊 综合评分:{current_rating:.2f} / 5.00
📝 评论总数:{rating_count}
📅 数据日期:{data['date']}{comparison_text}

⭐ 星级分布:
  ⭐⭐⭐⭐⭐ 五星:{five_star_count} ({five_star_count/rating_count*100:.1f}%)
  ⭐⭐⭐⭐ 四星:{data['four_star_count']} ({data['four_star_count']/rating_count*100:.1f}%)
  ⭐⭐⭐ 三星:{data['three_star_count']} ({data['three_star_count']/rating_count*100:.1f}%)
  ⭐⭐ 二星:{data['two_star_count']} ({data['two_star_count']/rating_count*100:.1f}%)
  ⭐ 一星:{data['one_star_count']} ({data['one_star_count']/rating_count*100:.1f}%)

🎯 提升目标:
  当前 {current_rating:.2f} → 下一级 {target_rating:.1f}
  需要 {needed_five_stars} 五星好评 ⭐⭐⭐⭐⭐

🌐 数据平台:{data['platform']}"""
        
        return self._create_text_response(response_text)
    
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

3️⃣ **店铺评分查询**
   • Piccadilly店评分
   • battersea评分
   • 查询 巴特西 评分
   显示:⭐ 综合评分、星级分布、提升到下一等级所需5星数

4️⃣ **查询订单数据**
   • 2025-12-22订单

5️⃣ **帮助信息**
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
