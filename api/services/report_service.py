"""报告生成服务"""
from datetime import datetime, timedelta
from typing import Optional

from utils import get_db_conn


def query_order_summary(start_date: str, end_date: Optional[str] = None, store_name: Optional[str] = None) -> dict:
    """
    查询指定日期或日期范围的订单汇总
    
    参数：
    - start_date: 开始日期字符串 YYYY-MM-DD
    - end_date: 结束日期字符串 YYYY-MM-DD（可选，默认等于 start_date）
    - store_name: 店铺名（可选，支持模糊匹配）
    
    返回：
    - dict: 汇总数据
    """
    if not end_date:
        end_date = start_date
    
    conn = get_db_conn()
    cursor = conn.cursor()
    
    try:
        # 显式检查店铺名是否有效（排除空字符串）
        if store_name and store_name.strip() != '':
            # 先尝试精确匹配（store_code 或完整中文名）
            exact_query = """
                SELECT 
                    COALESCE(s.name_cn, r.store_name) as store_name,
                    r.store_code,
                    COUNT(DISTINCT r.order_id) as order_count,
                    ROUND(SUM(CAST(r.payload->'data'->>'fixedPrice' AS NUMERIC))::numeric, 2) as total_amount,
                    ROUND(SUM(r.print_amount)::numeric, 2) as total_print_amount,
                    ROUND(SUM(r.estimated_revenue)::numeric, 2) as total_revenue,
                    ROUND(CASE WHEN COUNT(DISTINCT r.order_id) > 0 THEN SUM(r.print_amount)::numeric / COUNT(DISTINCT r.order_id) ELSE 0 END, 2) as avg_revenue
                FROM raw_orders r
                LEFT JOIN stores s ON r.store_code = s.code
                WHERE DATE(r.order_date) >= %s AND DATE(r.order_date) <= %s
                  AND (
                      LOWER(r.store_code) = LOWER(%s)
                      OR LOWER(s.name_cn) = LOWER(%s)
                      OR LOWER(r.store_name) = LOWER(%s)
                  )
                GROUP BY COALESCE(s.name_cn, r.store_name), r.store_code
                ORDER BY order_count DESC
            """
            cursor.execute(exact_query, (start_date, end_date, store_name, store_name, store_name))
            results = cursor.fetchall()
            
            # 如果精确匹配没结果，再使用模糊匹配
            if not results:
                fuzzy_query = """
                    SELECT 
                        COALESCE(s.name_cn, r.store_name) as store_name,
                        r.store_code,
                        COUNT(DISTINCT r.order_id) as order_count,
                        ROUND(SUM(CAST(r.payload->'data'->>'fixedPrice' AS NUMERIC))::numeric, 2) as total_amount,
                        ROUND(SUM(r.print_amount)::numeric, 2) as total_print_amount,
                        ROUND(SUM(r.estimated_revenue)::numeric, 2) as total_revenue,
                        ROUND(CASE WHEN COUNT(DISTINCT r.order_id) > 0 THEN SUM(r.print_amount)::numeric / COUNT(DISTINCT r.order_id) ELSE 0 END, 2) as avg_revenue
                    FROM raw_orders r
                    LEFT JOIN stores s ON r.store_code = s.code
                    WHERE DATE(r.order_date) >= %s AND DATE(r.order_date) <= %s
                      AND (
                          LOWER(r.store_name) LIKE LOWER(%s)
                          OR LOWER(r.store_code) LIKE LOWER(%s)
                          OR LOWER(s.name_cn) LIKE LOWER(%s)
                      )
                    GROUP BY COALESCE(s.name_cn, r.store_name), r.store_code
                    ORDER BY order_count DESC
                """
                search_pattern = f"%{store_name}%"
                cursor.execute(fuzzy_query, (start_date, end_date, search_pattern, search_pattern, search_pattern))
                results = cursor.fetchall()
        else:
            # 查询所有店铺
            query = """
                SELECT 
                    COALESCE(s.name_cn, r.store_name) as store_name,
                    r.store_code,
                    COUNT(DISTINCT r.order_id) as order_count,
                    ROUND(SUM(CAST(r.payload->'data'->>'fixedPrice' AS NUMERIC))::numeric, 2) as total_amount,
                    ROUND(SUM(r.print_amount)::numeric, 2) as total_print_amount,
                    ROUND(SUM(r.estimated_revenue)::numeric, 2) as total_revenue,
                    ROUND(CASE WHEN COUNT(DISTINCT r.order_id) > 0 THEN SUM(r.print_amount)::numeric / COUNT(DISTINCT r.order_id) ELSE 0 END, 2) as avg_revenue
                FROM raw_orders r
                LEFT JOIN stores s ON r.store_code = s.code
                WHERE DATE(r.order_date) >= %s AND DATE(r.order_date) <= %s
                GROUP BY COALESCE(s.name_cn, r.store_name), r.store_code
                ORDER BY order_count DESC
            """
            cursor.execute(query, (start_date, end_date))
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
                'order_count': row[2],
                'total_amount': float(row[3]) if row[3] else 0.0,
                'total_print_amount': float(row[4]) if row[4] else 0.0,
                'total_revenue': float(row[5]) if row[5] else 0.0,
                'avg_revenue': float(row[6]) if row[6] else 0.0
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


def generate_daily_summary_text(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """
    生成订单汇总报告文本（支持日期范围）
    
    参数：
    - start_date: 开始日期字符串（可选，默认为昨天）
    - end_date: 结束日期字符串（可选，默认等于 start_date）
    
    返回：
    - str: 格式化的报告文本
    """
    if not start_date:
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    if not end_date:
        end_date = start_date
    
    date_label = start_date if start_date == end_date else f"{start_date} 至 {end_date}"
    
    conn = get_db_conn()
    cursor = conn.cursor()
    
    try:
        # 1. 总体数据
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT order_id) as total_orders,
                ROUND(SUM(CAST(payload->'data'->>'fixedPrice' AS NUMERIC))::numeric, 2) as total_amount,
                ROUND(SUM(print_amount)::numeric, 2) as total_print_amount,
                ROUND(SUM(estimated_revenue)::numeric, 2) as total_revenue,
                ROUND(CASE WHEN COUNT(DISTINCT order_id) > 0 THEN SUM(print_amount)::numeric / COUNT(DISTINCT order_id) ELSE 0 END, 2) as avg_revenue
            FROM raw_orders
            WHERE DATE(order_date) >= %s AND DATE(order_date) <= %s
        """, (start_date, end_date))
        
        overall = cursor.fetchone()
        if not overall or not overall[0]:
            return f"📊 {date_label} 数据汇总\n\n未找到订单数据"
        
        # 2. 各店铺数据
        cursor.execute("""
            SELECT 
                COALESCE(s.name_cn, r.store_name) as store_name,
                COUNT(DISTINCT r.order_id) as order_count,
                ROUND(SUM(CAST(r.payload->'data'->>'fixedPrice' AS NUMERIC))::numeric, 2) as total_amount,
                ROUND(SUM(r.print_amount)::numeric, 2) as total_print_amount,
                ROUND(SUM(r.estimated_revenue)::numeric, 2) as revenue,
                ROUND(CASE WHEN COUNT(DISTINCT r.order_id) > 0 THEN SUM(r.print_amount)::numeric / COUNT(DISTINCT r.order_id) ELSE 0 END, 2) as avg_revenue
            FROM raw_orders r
            LEFT JOIN stores s ON r.store_code = s.code
            WHERE DATE(r.order_date) >= %s AND DATE(r.order_date) <= %s
            GROUP BY COALESCE(s.name_cn, r.store_name)
            ORDER BY COUNT(DISTINCT r.order_id) DESC
        """, (start_date, end_date))
        
        stores = cursor.fetchall()
        
        # 3. 平台分布
        cursor.execute("""
            SELECT 
                platform,
                COUNT(DISTINCT order_id) as count,
                ROUND(SUM(estimated_revenue)::numeric, 2) as revenue
            FROM raw_orders
            WHERE DATE(order_date) >= %s AND DATE(order_date) <= %s
            GROUP BY platform
            ORDER BY COUNT(DISTINCT order_id) DESC
        """, (start_date, end_date))
        
        platforms = cursor.fetchall()
        
        # 4. 每日趋势（仅多日时查询）
        daily_trend = []
        if start_date != end_date:
            cursor.execute("""
                SELECT 
                    DATE(order_date) as date,
                    COUNT(DISTINCT order_id) as orders,
                    ROUND(SUM(estimated_revenue)::numeric, 2) as revenue,
                    ROUND(CASE WHEN COUNT(DISTINCT order_id) > 0 THEN SUM(print_amount)::numeric / COUNT(DISTINCT order_id) ELSE 0 END, 2) as avg_revenue
                FROM raw_orders
                WHERE DATE(order_date) >= %s AND DATE(order_date) <= %s
                GROUP BY DATE(order_date)
                ORDER BY DATE(order_date)
            """, (start_date, end_date))
            daily_trend = cursor.fetchall()
        
        # 构建报告文本
        lines = [
            f"{'='*40}",
            f"📊 {date_label} 订单数据汇总",
            f"{'='*40}\n",
            f"📈 总体数据",
            f"{'-'*40}",
            f"📦 总订单数：{overall[0]} 单",
            f"💰 实收金额：£{overall[1]:.2f}",
            f"📄 打印单金额：£{overall[2]:.2f}",
            f"💵 预计收入：£{overall[3]:.2f}",
            f"📊 平均客单价：£{overall[4]:.2f}\n",
            f"🏪 各店铺数据",
            f"{'-'*40}"
        ]
        
        for i, store in enumerate(stores, 1):
            lines.append(f"{i}. {store[0]}")
            lines.append(f"   📦 {store[1]} 单 | 💰 £{store[2]:.2f} | 📄 £{store[3]:.2f} | 💵 £{store[4]:.2f} | 📊 £{store[5]:.2f}")
        
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


def generate_store_summary_text(store_name: str, start_date: str, end_date: Optional[str] = None) -> str:
    """
    生成单个店铺的汇总报告文本（支持日期范围）
    
    参数：
    - store_name: 店铺名
    - start_date: 开始日期字符串
    - end_date: 结束日期字符串（可选）
    
    返回：
    - str: 格式化的报告文本
    """
    # 验证店铺名不能为空
    if not store_name or store_name.strip() == '':
        return "❌ 错误：店铺查询必须指定店铺名称\n💡 提示：请使用 '店铺名 日期' 格式查询"
    
    if not end_date:
        end_date = start_date
    
    date_label = start_date if start_date == end_date else f"{start_date} 至 {end_date}"
    
    result = query_order_summary(start_date, end_date, store_name.strip())
    
    if not result['success']:
        return result['message']
    
    stores = result['stores']
    
    if len(stores) == 1:
        store = stores[0]
        lines = [
            f"{'='*40}",
            f"📊 店铺订单查询结果",
            f"{'='*40}\n",
            f"🏪 店铺名称：{store['store_name']}",
            f"📅 查询日期：{date_label}\n",
            f"📊 数据概览",
            f"{'-'*40}",
            f"📦 订单数量：{store['order_count']} 单",
            f"💰 实收金额：£{store['total_amount']:.2f}",
            f"📄 打印单金额：£{store['total_print_amount']:.2f}",
            f"💵 预计收入：£{store['total_revenue']:.2f}",
            f"📊 平均客单价：£{store['avg_revenue']:.2f}"
        ]
        
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
                        ROUND(SUM(CAST(payload->'data'->>'fixedPrice' AS NUMERIC))::numeric, 2) as amount,
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
            f"⚠️  找到 {len(stores)} 个匹配的店铺",
            f"{'='*40}",
            f"📅 查询日期：{date_label}\n",
            f"💡 提示：请使用更精确的店铺名称\n"
        ]
        for i, store in enumerate(stores, 1):
            lines.append(f"{i}. 🏪 {store['store_name']}")
            lines.append(f"{'-'*40}")
            lines.append(f"📦 订单：{store['order_count']} 单")
            lines.append(f"💰 实收：£{store['total_amount']:.2f}")
            lines.append(f"📄 打印单：£{store['total_print_amount']:.2f}")
            lines.append(f"💵 预计收入：£{store['total_revenue']:.2f}")
            lines.append(f"📊 客单：£{store['avg_revenue']:.2f}")
            lines.append("")
        return "\n".join(lines)
