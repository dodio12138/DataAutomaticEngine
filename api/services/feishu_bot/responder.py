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
        elif command_type == 'hot_items':
            return self.create_hot_items_response(params)
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
    
    def create_hot_items_response(self, params: Dict) -> Dict:
        """
        创建热门菜品响应
        
        参数:
        - params: 参数（包含 query_type, store_name, date, platform, limit, days）
          - query_type: 'items'(主产品) / 'modifiers'(添加项) / 'summary'(汇总)
          - store_name: 店铺名称（可选）
          - date: 查询日期（可选）
          - platform: 平台（可选，从文本中提取）
          - limit: 显示前N名（可选，默认10）
          - days: 前P天数据（可选）
        
        返回:
        - Dict: 飞书消息响应
        """
        query_type = params.get('query_type', 'summary')
        store_name = params.get('store_name', '').strip()
        date = params.get('date')
        platform = params.get('platform')
        limit = params.get('limit', 10)  # 默认显示前10
        days = params.get('days')  # 前P天
        
        # 如果有店铺名，需要映射到 store_code
        store_code = None
        if store_name:
            # 调用 report_service 的映射函数
            store_code = report_service.map_store_name_to_code(store_name)
            if not store_code:
                return self._create_text_response(f"❌ 未找到店铺: {store_name}")
        
        # 调用订单统计API查询热门菜品
        try:
            import requests
            from urllib.parse import urlencode
            
            base_url = "http://api:8000"
            
            # 计算日期范围（如果指定了 days）
            if days and not date:
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                date_info = f"最近{days}天 ({start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')})"
            elif date:
                date_info = date
            else:
                date_info = '所有时间'
            
            if query_type == 'summary':
                # 汇总查询：同时获取主产品和添加项
                # summary 模式下，limit 用于 TOP 5
                summary_limit = 5 if limit >= 10 else limit
                items_result = self._query_hot_items(base_url, 'items', store_code, date, platform, summary_limit, days)
                modifiers_result = self._query_hot_items(base_url, 'modifiers', store_code, date, platform, summary_limit, days)
                
                if not items_result['success'] or not modifiers_result['success']:
                    error_msg = items_result.get('message') or modifiers_result.get('message')
                    return self._create_text_response(f"❌ 查询失败: {error_msg}")
                
                # 生成汇总响应
                response_text = self._format_hot_items_summary(
                    items_result['data'], 
                    modifiers_result['data'],
                    store_name or '全部店铺',
                    date_info,
                    platform,
                    summary_limit
                )
            else:
                # 单独查询主产品或添加项
                result = self._query_hot_items(base_url, query_type, store_code, date, platform, limit, days)
                
                if not result['success']:
                    return self._create_text_response(f"❌ 查询失败: {result.get('message')}")
                
                # 生成单一类型响应
                response_text = self._format_hot_items_single(
                    result['data'],
                    query_type,
                    store_name or '全部店铺',
                    date_info,
                    platform,
                    limit
                )
            
            return self._create_text_response(response_text)
            
        except Exception as e:
            return self._create_text_response(f"❌ 查询出错: {str(e)}")
    
    def _query_hot_items(self, base_url: str, query_type: str, store_code: str = None, 
                         date: str = None, platform: str = None, limit: int = 10, days: int = None) -> Dict:
        """
        调用API查询热门菜品数据
        
        参数:
        - base_url: API基础URL
        - query_type: 'items' 或 'modifiers'
        - store_code: 店铺代码（可选）
        - date: 日期（可选）
        - platform: 平台（可选）
        - limit: 返回数量（默认10）
        - days: 前P天数据（可选）
        
        返回:
        - Dict: {'success': bool, 'data': [...], 'message': str}
        """
        import requests
        from urllib.parse import urlencode
        from datetime import datetime, timedelta
        
        try:
            # 构建查询参数
            params = {'limit': limit}
            if store_code:
                params['store_code'] = store_code
            if date:
                params['date'] = date
            elif days:  # 如果没有指定具体日期，但指定了天数范围
                # 计算日期范围
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                params['start_date'] = start_date.strftime('%Y-%m-%d')
                params['end_date'] = end_date.strftime('%Y-%m-%d')
            if platform:
                # 标准化平台名称
                if platform in ['panda', 'hungrypanda']:
                    params['platform'] = 'hungrypanda'
                elif platform in ['deliveroo', 'roo']:
                    params['platform'] = 'deliveroo'
            
            # 确定API端点
            if query_type == 'items':
                endpoint = f"{base_url}/stats/items/top"
            elif query_type == 'modifiers':
                endpoint = f"{base_url}/stats/modifiers/top"
            else:
                return {'success': False, 'message': f'未知查询类型: {query_type}'}
            
            # 发起请求
            url = f"{endpoint}?{urlencode(params)}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'data': data}
            else:
                return {'success': False, 'message': f'API返回错误: {response.status_code}'}
                
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def _format_hot_items_summary(self, items_data: list, modifiers_data: list,
                                   store_name: str, date_info: str, platform: str = None, limit: int = 5) -> str:
        """
        格式化汇总响应（主产品 + 添加项）
        
        参数:
        - items_data: 主产品数据列表
        - modifiers_data: 添加项数据列表
        - store_name: 店铺名称
        - date_info: 日期信息
        - platform: 平台（可选）
        - limit: 显示数量（默认5）
        
        返回:
        - str: 格式化的响应文本
        """
        platform_text = f" ({platform.upper()})" if platform else ""
        
        response_lines = [
            f"🔥 热门菜品汇总{platform_text}",
            f"📍 店铺: {store_name}",
            f"📅 时间: {date_info}",
            "",
            f"🍜 热门主产品 TOP {limit}:"
        ]
        
        # 主产品 TOP N
        emoji_list = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        for i, item in enumerate(items_data[:limit], 1):
            emoji = emoji_list[i-1] if i <= 10 else f"{i}."
            emoji = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][i-1]
            response_lines.append(
                f"{emoji} {item['item_name']}: {item['total_quantity']}份 | "
                f"£{item['total_revenue']:.2f} | {item['order_count']}单"
            )
        
        response_lines.extend([
            "",
            "🎯 热门添加项 TOP 5:"
        ])
        
        # 添加项 TOP 5
        for i, mod in enumerate(modifiers_data[:5], 1):
            emoji = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][i-1]
            response_lines.append(
                f"{emoji} {mod['modifier_name']}: {mod['usage_count']}次 | "
                f"{mod['unique_orders']}单"
            )
        
        response_lines.append("\n💡 发送'热门主产品'或'热门添加项'查看完整榜单")
        
        return "\n".join(response_lines)
    
    def _format_hot_items_single(self, data: list, query_type: str,
                                  store_name: str, date_info: str, platform: str = None, limit: int = 10) -> str:
        """
        格式化单一类型响应（仅主产品或仅添加项）
        
        参数:
        - data: 数据列表
        - query_type: 'items' 或 'modifiers'
        - store_name: 店铺名称
        - date_info: 日期信息
        - platform: 平台（可选）
        - limit: 显示数量（默认10）
        
        返回:
        - str: 格式化的响应文本
        """
        platform_text = f" ({platform.upper()})" if platform else ""
        
        if query_type == 'items':
            title = f"🍜 热门主产品 TOP {limit}{platform_text}"
            emoji_list = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        else:
            title = f"🎯 热门添加项 TOP {limit}{platform_text}"
            emoji_list = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        
        response_lines = [
            title,
            f"📍 店铺: {store_name}",
            f"📅 时间: {date_info}",
            ""
        ]
        
        if not data:
            response_lines.append("❌ 暂无数据")
            return "\n".join(response_lines)
        
        # 显示 TOP N
        for i, item in enumerate(data[:limit], 1):
            emoji = emoji_list[i-1] if i <= 10 else f"{i}."
            
            if query_type == 'items':
                response_lines.append(
                    f"{emoji} {item['item_name']}\n"
                    f"   📦 销量: {item['total_quantity']}份 | "
                    f"💰 营收: £{item['total_revenue']:.2f}\n"
                    f"   📝 订单: {item['order_count']}单 | "
                    f"💵 均价: £{item['avg_price']:.2f}"
                )
            else:
                response_lines.append(
                    f"{emoji} {item['modifier_name']}\n"
                    f"   🔢 使用次数: {item['usage_count']} | "
                    f"📝 订单数: {item['unique_orders']}\n"
                    f"   📊 平均每单: {item['avg_per_order']:.1f}次"
                )
        
        return "\n".join(response_lines)
    
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

4️⃣ **热门菜品查询** 🆕
   
   📌 新格式（推荐）：Top N [P] [店铺] [平台] [类型]
   • Top 5 - 显示前5名（汇总：主产品+添加项各5）
   • Top 10 - 显示前10名（汇总：主产品+添加项各10）
   • Top 5 7 - 显示前5名，最近7天数据
   • Top 10 30 - 显示前10名，最近30天数据
   • Top 5 7 Battersea - 巴特西店，最近7天，前5名
   • Top 5 10 Battersea deliveroo - 巴特西店，最近10天，Deliveroo平台，前5名
   • Top 5 10 Battersea deliveroo main - 巴特西店，最近10天，Deliveroo平台，主产品，前5名
   • Top 8 14 piccadilly panda modifier - Piccadilly店，最近14天，Panda平台，添加项，前8名
   
   参数说明：
   • N - 显示数量（必填，1-50）
   • P - 前P天数据（可选，不填则查询所有时间）
   • 店铺 - 店铺名称（可选，支持英文/中文）
   • 平台 - deliveroo/panda/roo/熊猫（可选）
   • 类型 - main/modifier/summary（可选，默认summary）
     * main/主产品 - 仅主菜品
     * modifier/添加项 - 仅配料/加料
     * summary/汇总 - 主产品+添加项
   
   📌 旧格式（兼容）：
   • 热门菜品（汇总：主产品+添加项 TOP5）
   • 热门主产品（完整TOP10榜单）
   • 热门添加项（完整TOP10榜单）
   • Piccadilly店 热门菜品
   • 2025-12-24 热门主产品

5️⃣ **查询订单数据**
   • 2025-12-22订单

6️⃣ **帮助信息**
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
