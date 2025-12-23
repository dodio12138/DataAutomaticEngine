"""报告生成服务"""
from datetime import datetime, timedelta
from typing import Optional

from utils import get_db_conn


def query_order_summary(date_str: str, store_name: Optional[str] = None) -> dict:
    """
    查询指定日期的订单汇总
    
    参数：
    - date_str: 日期字符串 YYYY-MM-DD
    - store_name: 店铺名（可选，支持模糊匹配）
    
    返回：
    - dict: 汇总数据
    """
    conn = get_db_conn()
    cursor = conn.cursor()
    
    try:
        if store_name:
            # 查询指定店铺
            query = """
                SELECT 
                    store_name,
                    store_code,
                    COUNT(*) as order_count,
                    SUM(CAST(payload->'data'->>'fixedPrice' AS NUMERIC)) as total_amount,
                    SUM(estimated_revenue) as total_revenue,
                    SUM(print_amount) as total_print_amount
                FROM raw_orders
                WHERE DATE(order_date) = %s
                  AND (
                      LOWER(store_name) LIKE LOWER(%s)
                      OR LOWER(store_code) LIKE LOWER(%s)
                  )
                GROUP BY store_name, store_code
                ORDER BY order_count DESC
            """
            search_pattern = f"%{store_name}%"
            cursor.execute(query, (date_str, search_pattern, search_pattern))
        else:
            # 查询所有店铺
            query = """
                SELECT 
                    store_name,
                    store_code,
                    COUNT(*) as order_count,
                    SUM(CAST(payload->'data'->>'fixedPrice' AS NUMERIC)) as total_amount,
                    SUM(estimated_revenue) as total_revenue,
                    SUM(print_amount) as total_print_amount
                FROM raw_orders
                WHERE DATE(order_date) = %s
                GROUP BY store_name, store_code
                ORDER BY order_count DESC
            """
            cursor.execute(query, (date_str,))
        
        results = cursor.fetchall()
        
        if not results:
            return {
                'success': False,
                'message': f'未找到 {date_str} 的订单数据'
            }
        
        # 构建店铺列表
        stores = []
        for row in results:
            stores.append({
                'store_name': row[0] or row[1],
                'store_code': row[1],
                'order_count': row[2],
                'total_amount': float(row[3]) if row[3] else 0.0,
                'total_revenue': float(row[4]) if row[4] else 0.0,
                'total_print_amount': float(row[5]) if row[5] else 0.0
            })
        
        return {
            'success': True,
            'date': date_str,
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


def generate_daily_summary_text(date_str: Optional[str] = None) -> str:
    """
    生成每日订单汇总报告文本
    
    参数：
    - date_str: 日期字符串（可选，默认为昨天）
    
    返回：
    - str: 格式化的报告文本
    """
    if not date_str:
        date_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    result = query_order_summary(date_str)
    
    if not result['success']:
        return f"📊 熊猫外卖 {date_str} 数据汇总\n\n{result['message']}"
    
    # 生成报告文本
    lines = [
        f"📊 熊猫外卖 {date_str} 订单数据汇总",
        f"{'='*40}\n"
    ]
    
    total_orders = 0
    total_amount = 0.0
    total_revenue = 0.0
    total_print = 0.0
    
    for store in result['stores']:
        store_name = store['store_name']
        order_count = store['order_count']
        amount = store['total_amount']
        revenue = store.get('total_revenue', 0.0)
        print_amt = store.get('total_print_amount', 0.0)
        
        total_orders += order_count
        total_amount += amount
        total_revenue += revenue
        total_print += print_amt
        
        lines.append(f"🏪 {store_name}")
        lines.append(f"   📦 订单：{order_count} 单")
        lines.append(f"   💰 实收金额：£{amount:.2f}")
        lines.append(f"   💵 打印单金额：£{print_amt:.2f}")
        lines.append(f"   💸 预计收入：£{revenue:.2f}\n")
    
    lines.append(f"{'='*40}")
    lines.append(f"📈 总计：{total_orders} 单")
    lines.append(f"💷 实收总额：£{total_amount:.2f}")
    lines.append(f"📤 打印单总额：£{total_print:.2f}")
    lines.append(f"💹 预计总收入：£{total_revenue:.2f}")
    
    return "\n".join(lines)


def generate_store_summary_text(store_name: str, date_str: str) -> str:
    """
    生成单个店铺的汇总报告文本
    
    参数：
    - store_name: 店铺名
    - date_str: 日期字符串
    
    返回：
    - str: 格式化的报告文本
    """
    result = query_order_summary(date_str, store_name)
    
    if not result['success']:
        return result['message']
    
    stores = result['stores']
    
    if len(stores) == 1:
        store = stores[0]
        return f"""📊 订单查询结果

🏪 店铺：{store['store_name']}
📅 日期：{date_str}
📦 订单数量：{store['order_count']} 单
💰 实收金额：£{store['total_amount']:.2f}
📤 打印单金额：£{store.get('total_print_amount', 0.0):.2f}
💵 预计收入：£{store.get('total_revenue', 0.0):.2f}"""
    else:
        # 多个店铺匹配
        lines = [f"📊 找到 {len(stores)} 个匹配的店铺\n📅 日期：{date_str}\n"]
        for store in stores:
            lines.append(f"\n🏪 {store['store_name']}")
            lines.append(f"   📦 订单：{store['order_count']} 单")
            lines.append(f"   💰 实收金额：£{store['total_amount']:.2f}")
            lines.append(f"   📤 打印单金额：£{store.get('total_print_amount', 0.0):.2f}")
            lines.append(f"   💵 预计收入：£{store.get('total_revenue', 0.0):.2f}")
        return "\n".join(lines)
