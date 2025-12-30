"""报告生成服务"""
from datetime import datetime, timedelta
from typing import Optional

from utils import get_db_conn


def query_order_summary(start_date: str, end_date: Optional[str] = None, store_name: Optional[str] = None, platform: Optional[str] = None) -> dict:
    """
    查询指定日期或日期范围的订单汇总（从 daily_sales_summary 表读取）
    
    参数：
    - start_date: 开始日期字符串 YYYY-MM-DD
    - end_date: 结束日期字符串 YYYY-MM-DD（可选，默认等于 start_date）
    - store_name: 店铺名（可选，支持模糊匹配）
    - platform: 平台名（可选，'panda', 'hungrypanda', 'deliveroo' 或 None 表示所有平台）
    
    返回：
    - dict: 汇总数据
    """
    if not end_date:
        end_date = start_date
    
    # 标准化平台名称
    if platform:
        platform_lower = platform.lower()
        if platform_lower in ['panda', 'hungrypanda']:
            platform = 'panda'
        elif platform_lower == 'deliveroo':
            platform = 'deliveroo'
        else:
            platform = None
    
    conn = get_db_conn()
    cursor = conn.cursor()
    
    try:
        # 显式检查店铺名是否有效（排除空字符串）
        if store_name and store_name.strip() != '':
            # 先尝试精确匹配（store_code 或完整中文名）
            exact_query = """
                SELECT 
                    d.store_name,
                    d.store_code,
                    d.platform,
                    SUM(d.order_count) as order_count,
                    ROUND(SUM(d.gross_sales)::numeric, 2) as total_product_amount,
                    ROUND(SUM(d.net_sales)::numeric, 2) as total_net_sales,
                    ROUND(SUM(d.net_sales)::numeric, 2) as total_revenue,
                    ROUND(CASE WHEN SUM(d.order_count) > 0 THEN SUM(d.net_sales)::numeric / SUM(d.order_count) ELSE 0 END, 2) as avg_revenue
                FROM daily_sales_summary d
                WHERE d.date >= %s AND d.date <= %s
                  AND (
                      LOWER(d.store_code) = LOWER(%s)
                      OR LOWER(d.store_name) = LOWER(%s)
                  )
            """
            params = [start_date, end_date, store_name, store_name]
            if platform:
                exact_query += " AND d.platform = %s"
                params.append(platform)
            exact_query += """
                GROUP BY d.store_name, d.store_code, d.platform
                ORDER BY SUM(d.order_count) DESC
            """
            cursor.execute(exact_query, params)
            results = cursor.fetchall()
            
            # 如果精确匹配没结果，再使用模糊匹配
            if not results:
                search_pattern = f"%{store_name}%"
                fuzzy_query = """
                    SELECT 
                        d.store_name,
                        d.store_code,
                        d.platform,
                        SUM(d.order_count) as order_count,
                        ROUND(SUM(d.gross_sales)::numeric, 2) as total_product_amount,
                        ROUND(SUM(d.net_sales)::numeric, 2) as total_net_sales,
                        ROUND(SUM(d.net_sales)::numeric, 2) as total_revenue,
                        ROUND(CASE WHEN SUM(d.order_count) > 0 THEN SUM(d.net_sales)::numeric / SUM(d.order_count) ELSE 0 END, 2) as avg_revenue
                    FROM daily_sales_summary d
                    WHERE d.date >= %s AND d.date <= %s
                      AND (
                          LOWER(d.store_name) LIKE LOWER(%s)
                          OR LOWER(d.store_code) LIKE LOWER(%s)
                      )
                """
                params = [start_date, end_date, search_pattern, search_pattern]
                if platform:
                    fuzzy_query += " AND d.platform = %s"
                    params.append(platform)
                fuzzy_query += """
                    GROUP BY d.store_name, d.store_code, d.platform
                    ORDER BY SUM(d.order_count) DESC
                """
                cursor.execute(fuzzy_query, params)
                results = cursor.fetchall()
        else:
            # 查询所有店铺
            query = """
                SELECT 
                    d.store_name,
                    d.store_code,
                    d.platform,
                    SUM(d.order_count) as order_count,
                    ROUND(SUM(d.gross_sales)::numeric, 2) as total_product_amount,
                    ROUND(SUM(d.net_sales)::numeric, 2) as total_net_sales,
                    ROUND(SUM(d.net_sales)::numeric, 2) as total_revenue,
                    ROUND(CASE WHEN SUM(d.order_count) > 0 THEN SUM(d.net_sales)::numeric / SUM(d.order_count) ELSE 0 END, 2) as avg_revenue
                FROM daily_sales_summary d
                WHERE d.date >= %s AND d.date <= %s
            """
            params = [start_date, end_date]
            if platform:
                query += " AND d.platform = %s"
                params.append(platform)
            query += """
                GROUP BY d.store_name, d.store_code, d.platform
                ORDER BY SUM(d.order_count) DESC
            """
            cursor.execute(query, params)
            results = cursor.fetchall()
        
        if not results:
            date_label = start_date if start_date == end_date else f"{start_date} 至 {end_date}"
            return {
                'success': False,
                'message': f'未找到 {date_label} 的订单数据'
            }
        
        # 构建店铺列表
        stores = []
        for row in results:
            stores.append({
                'store_name': row[0] or row[1],
                'store_code': row[1],
                'platform': row[2],
                'order_count': row[3],
                'total_product_amount': float(row[4]) if row[4] else 0.0,
                'total_net_sales': float(row[5]) if row[5] else 0.0,
                'total_revenue': float(row[6]) if row[6] else 0.0,
                'avg_revenue': float(row[7]) if row[7] else 0.0
            })
        
        return {
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'stores': stores
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': f'查询出错: {str(e)}'
        }
    finally:
        cursor.close()
        conn.close()


def generate_daily_summary_text(start_date: Optional[str] = None, end_date: Optional[str] = None, platform: Optional[str] = None) -> str:
    """
    生成订单汇总报告文本（支持日期范围和平台筛选）
    
    参数：
    - start_date: 开始日期字符串（可选，默认为昨天）
    - end_date: 结束日期字符串（可选，默认等于 start_date）
    - platform: 平台名（可选，'panda', 'deliveroo' 或 None 表示所有平台）
    
    返回：
    - str: 格式化的报告文本
    """
    if not start_date:
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = start_date
    
    # 标准化平台名称
    if platform:
        platform_lower = platform.lower()
        if platform_lower in ['panda', 'hungrypanda']:
            platform = 'panda'
        elif platform_lower == 'deliveroo':
            platform = 'deliveroo'
        else:
            platform = None
    
    date_label = start_date if start_date == end_date else f"{start_date} 至 {end_date}"
    platform_label = ""
    if platform == 'panda':
        platform_label = " (🐼 HungryPanda)"
    elif platform == 'deliveroo':
        platform_label = " (🦘 Deliveroo)"
    else:
        platform_label = " (所有平台)"
    
    conn = get_db_conn()
    cursor = conn.cursor()
    
    try:
        # 1. 总体数据（从 daily_sales_summary 汇总）
        query = """
            SELECT 
                SUM(order_count) as total_orders,
                ROUND(SUM(gross_sales)::numeric, 2) as total_gross_sales,
                ROUND(SUM(net_sales)::numeric, 2) as total_net_sales,
                ROUND(SUM(net_sales)::numeric, 2) as total_revenue,
                ROUND(CASE WHEN SUM(order_count) > 0 THEN SUM(net_sales)::numeric / SUM(order_count) ELSE 0 END, 2) as avg_revenue
            FROM daily_sales_summary
            WHERE date >= %s AND date <= %s
        """
        params = [start_date, end_date]
        if platform:
            query += " AND platform = %s"
            params.append(platform)
        cursor.execute(query, params)
        
        overall = cursor.fetchone()
        if not overall or not overall[0]:
            return f"📊 {date_label}{platform_label} 数据汇总\n\n未找到订单数据"
        
        # 2. 各店铺数据（从 daily_sales_summary 汇总）
        query = """
            SELECT 
                store_name,
                platform,
                SUM(order_count) as order_count,
                ROUND(SUM(gross_sales)::numeric, 2) as total_gross_sales,
                ROUND(SUM(net_sales)::numeric, 2) as total_net_sales,
                ROUND(SUM(net_sales)::numeric, 2) as revenue,
                ROUND(CASE WHEN SUM(order_count) > 0 THEN SUM(net_sales)::numeric / SUM(order_count) ELSE 0 END, 2) as avg_revenue
            FROM daily_sales_summary
            WHERE date >= %s AND date <= %s
        """
        params = [start_date, end_date]
        if platform:
            query += " AND platform = %s"
            params.append(platform)
        query += """
            GROUP BY store_name, platform
            ORDER BY SUM(order_count) DESC
        """
        cursor.execute(query, params)
        
        stores = cursor.fetchall()
        
        # 3. 平台分布（从 daily_sales_summary 汇总）
        query = """
            SELECT 
                platform,
                SUM(order_count) as count,
                ROUND(SUM(net_sales)::numeric, 2) as revenue
            FROM daily_sales_summary
            WHERE date >= %s AND date <= %s
        """
        params = [start_date, end_date]
        if platform:
            query += " AND platform = %s"
            params.append(platform)
        query += """
            GROUP BY platform
            ORDER BY SUM(order_count) DESC
        """
        cursor.execute(query, params)
        
        platforms = cursor.fetchall()
        
        # 4. 每日趋势（仅多日时查询，从 daily_sales_summary 汇总）
        daily_trend = []
        if start_date != end_date:
            query = """
                SELECT 
                    date,
                    SUM(order_count) as orders,
                    ROUND(SUM(net_sales)::numeric, 2) as revenue,
                    ROUND(CASE WHEN SUM(order_count) > 0 THEN SUM(net_sales)::numeric / SUM(order_count) ELSE 0 END, 2) as avg_revenue
                FROM daily_sales_summary
                WHERE date >= %s AND date <= %s
            """
            params = [start_date, end_date]
            if platform:
                query += " AND platform = %s"
                params.append(platform)
            query += """
                GROUP BY date
                ORDER BY date
            """
            cursor.execute(query, params)
            daily_trend = cursor.fetchall()
        
        # 构建报告文本
        lines = [
            f"{'='*40}",
            f"📊 {date_label}{platform_label} 订单数据汇总",
            f"📅 数据日期：{date_label}",
            f"{'='*40}\n",
            f"📈 总体数据",
            f"{'-'*40}",
            f"📦 总订单数：{overall[0]} 单",
            f"💰 总销售额(折前)：£{overall[1]:.2f}",
            f"💵 净销售额(折后)：£{overall[2]:.2f}",
            f"📊 平均客单价：£{overall[4]:.2f}\n",
            f"🏪 各店铺数据",
            f"{'-'*40}"
        ]
        
        for i, store in enumerate(stores, 1):
            store_name = store[0]
            store_platform = store[1]
            order_count = store[2]
            gross_sales = store[3]
            net_sales = store[4]
            revenue = store[5]
            avg_revenue = store[6]
            
            platform_emoji = "🐼" if store_platform == "panda" else "🦘"
            lines.append(f"{i}. {platform_emoji} {store_name}")
            lines.append(f"   📦 {order_count} 单 | 💰 £{gross_sales:.2f}(折前) | 💵 £{net_sales:.2f}(折后) | 📊 £{avg_revenue:.2f}")
        
        lines.append(f"\n📱 平台分布")
        lines.append(f"{'-'*40}")
        for platform in platforms:
            platform_emoji = "🐼" if platform[0].lower() == "hungrypanda" else "🍔"
            lines.append(f"{platform_emoji} {platform[0]}：{platform[1]} 单 | £{platform[2]:.2f}")
        
        # 每日趋势（多日时显示）
        if daily_trend:
            lines.append(f"\n📅 每日数据趋势")
            lines.append(f"{'-'*40}")
            for day in daily_trend:
                lines.append(f"📆 {day[0]}")
                lines.append(f"   📦 {day[1]} 单 | 💰 £{day[2]:.2f} | 📊 £{day[3]:.2f}")
        
        lines.append(f"\n{'='*40}")
        lines.append(f"✅ 汇总查询完成")
        
        return "\n".join(lines)
        
    except Exception as e:
        return f"📊 {date_label} 数据汇总\n\n查询出错: {str(e)}"
    finally:
        cursor.close()
        conn.close()


def generate_store_summary_text(store_name: str, start_date: str, end_date: Optional[str] = None, platform: Optional[str] = None) -> str:
    """
    生成单个店铺的汇总报告文本（支持日期范围和平台筛选）
    
    参数：
    - store_name: 店铺名
    - start_date: 开始日期字符串
    - end_date: 结束日期字符串（可选）
    - platform: 平台名（可选）
    
    返回：
    - str: 格式化的报告文本
    """
    # 验证店铺名不能为空
    if not store_name or store_name.strip() == '':
        return "❌ 错误：店铺查询必须指定店铺名称\n💡 提示：请使用 '店铺名 日期' 格式查询"
    
    if not end_date:
        end_date = start_date
    
    # 标准化平台名称
    if platform:
        platform_lower = platform.lower()
        if platform_lower in ['panda', 'hungrypanda']:
            platform = 'panda'
        elif platform_lower == 'deliveroo':
            platform = 'deliveroo'
        else:
            platform = None
    
    date_label = start_date if start_date == end_date else f"{start_date} 至 {end_date}"
    platform_label = ""
    if platform == 'panda':
        platform_label = " (🐼 HungryPanda)"
    elif platform == 'deliveroo':
        platform_label = " (🦘 Deliveroo)"
    
    result = query_order_summary(start_date, end_date, store_name.strip(), platform)
    
    if not result['success']:
        return result['message']
    
    stores = result['stores']
    
    if len(stores) == 1:
        store = stores[0]
        store_platform = store.get('platform', 'panda')
        platform_emoji = "🐼" if store_platform == "panda" else "🦘"
        
        lines = [
            f"{'='*40}",
            f"📊 店铺订单查询结果{platform_label}",
            f"📅 数据日期：{date_label}",
            f"{'='*40}\n",
            f"{platform_emoji} 店铺名称：{store['store_name']}",
            f"\n📊 数据概览",
            f"{'-'*40}",
            f"📦 订单数量：{store['order_count']} 单",
            f"💰 商品销售额：£{store['total_product_amount']:.2f}",
        ]
        
        # 熊猫平台显示折扣后销售额和预计收入
        if store_platform == 'panda':
            lines.append(f"📄 折扣后销售额：£{store['total_print_amount']:.2f}")
            lines.append(f"💵 预计收入：£{store['total_revenue']:.2f}")
        # Deliveroo 不显示预计收入
        
        lines.append(f"📊 平均客单价：£{store['avg_revenue']:.2f}")
        
        # 如果是日期范围查询，添加每日趋势
        if start_date != end_date:
            conn = get_db_conn()
            cursor = conn.cursor()
            try:
                # 使用 store_code 精确查询每日趋势
                cursor.execute("""
                    SELECT 
                        DATE(order_date) as date,
                        COUNT(DISTINCT order_id) as orders,
                        ROUND(SUM(product_amount)::numeric, 2) as product_amount,
                        ROUND(SUM(estimated_revenue)::numeric, 2) as revenue,
                        ROUND(CASE WHEN COUNT(DISTINCT order_id) > 0 THEN SUM(print_amount)::numeric / COUNT(DISTINCT order_id) ELSE 0 END, 2) as avg_revenue
                    FROM raw_orders
                    WHERE DATE(order_date) >= %s AND DATE(order_date) <= %s
                      AND store_code = %s
                    GROUP BY DATE(order_date)
                    ORDER BY DATE(order_date)
                """, (start_date, end_date, store['store_code']))
                daily_trend = cursor.fetchall()
                
                if daily_trend:
                    lines.append(f"\n📅 每日数据趋势")
                    lines.append(f"{'-'*40}")
                    for day in daily_trend:
                        lines.append(f"📆 {day[0]}")
                        lines.append(f"   📦 {day[1]} 单 | 💰 £{day[2]:.2f} | 💵 £{day[3]:.2f} | 📊 £{day[4]:.2f}")
            except Exception as e:
                lines.append(f"\n⚠️  每日趋势查询失败: {str(e)}")
            finally:
                cursor.close()
                conn.close()
        
        lines.append(f"\n{'='*40}")
        lines.append(f"✅ 查询完成")
        return "\n".join(lines)
    else:
        # 多个店铺匹配
        lines = [
            f"{'='*40}",
            f"⚠️  找到 {len(stores)} 个匹配的店铺{platform_label}",
            f"📅 数据日期：{date_label}",
            f"{'='*40}\n",
            f"💡 提示：请使用更精确的店铺名称\n"
        ]
        for i, store in enumerate(stores, 1):
            platform_emoji = "🐼" if store.get('platform') == "panda" else "🦘"
            store_platform = store.get('platform', 'panda')
            
            lines.append(f"{i}. {platform_emoji} {store['store_name']}")
            lines.append(f"{'-'*40}")
            lines.append(f"📦 订单：{store['order_count']} 单")
            lines.append(f"💰 商品销售额：£{store['total_product_amount']:.2f}")
            
            # 熊猫平台显示折扣后销售额和预计收入
            if store_platform == 'panda':
                lines.append(f"📄 折扣后：£{store['total_print_amount']:.2f}")
                lines.append(f"💵 预计收入：£{store['total_revenue']:.2f}")
            # Deliveroo 不显示预计收入
            
            lines.append(f"📊 客单：£{store['avg_revenue']:.2f}")
            lines.append("")
        return "\n".join(lines)
