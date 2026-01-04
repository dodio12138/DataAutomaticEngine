"""
Deliveroo 订单详情数据导入脚本
从 raw_orders 表解析 JSON 并导入到订单详情表
"""
import json
import psycopg2
from datetime import datetime
from typing import Dict, List
import os
import sys


def parse_and_insert_order(conn, raw_order_data: Dict, store_code: str = None):
    """
    解析单个订单 JSON 并插入到数据库
    
    参数:
    - conn: 数据库连接
    - raw_order_data: 原始订单 JSON 数据
    - store_code: 店铺代码（从 raw_orders 表传入）
    """
    cursor = conn.cursor()
    
    try:
        # 1. 插入订单主表
        order_id = raw_order_data.get('drn_id') or raw_order_data.get('id')
        restaurant_id = raw_order_data.get('restaurant_id', store_code or 'unknown')
        
        # 金额信息
        amount = raw_order_data.get('amount', {})
        total_amount = amount.get('fractional', 0) / 100.0 if amount else 0.0  # 转换为实际金额
        
        currency_code = amount.get('currency_code', 'GBP') if amount else 'GBP'
        
        # 订单状态
        status = raw_order_data.get('status', 'completed')
        
        # 时间线
        timeline = raw_order_data.get('timeline', {})
        placed_at = timeline.get('placed_at') if timeline else None
        accepted_at = timeline.get('accepted_at') if timeline else None
        delivery_picked_up_at = timeline.get('delivery_picked_up_at') if timeline else None
        
        # 插入订单（匹配实际表结构）
        cursor.execute("""
            INSERT INTO orders (
                order_id, platform, store_code, restaurant_id,
                total_amount, currency_code,
                status,
                placed_at, accepted_at, delivery_picked_up_at,
                raw_data
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s,
                %s, %s, %s,
                %s
            )
            ON CONFLICT (order_id, platform) DO NOTHING
        """, (
            order_id, 'deliveroo', store_code, restaurant_id,
            total_amount, currency_code,
            status,
            placed_at, accepted_at, delivery_picked_up_at,
            json.dumps(raw_order_data)
        ))
        
        # 检查是否真的插入了（如果 rowcount = 0 说明已存在）
        if cursor.rowcount == 0:
            print(f"⚠️  订单 {order_id[:8]} 已存在，跳过")
            return True
        
        # 2. 插入订单菜品和添加项
        items = raw_order_data.get('items', [])
        for item in items:
            item_name = item.get('name')
            category_name = item.get('category_name')
            quantity = item.get('quantity', 1)
            
            # 价格信息
            unit_price_data = item.get('unit_price', {})
            unit_price = unit_price_data.get('fractional', 0) / 100.0
            
            total_price_data = item.get('total_price', {})
            total_price = total_price_data.get('fractional', 0) / 100.0
            
            total_unit_price_data = item.get('total_unit_price', {})
            total_unit_price = total_unit_price_data.get('fractional', 0) / 100.0
            
            # 插入菜品（使用订单的字符串ID，不是数据库自增ID）
            cursor.execute("""
                INSERT INTO order_items (
                    order_id, item_name, category_name, quantity,
                    unit_price, total_price, total_unit_price
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
                RETURNING id
            """, (
                order_id, item_name, category_name, quantity,
                unit_price, total_price, total_unit_price
            ))
            
            order_item_id = cursor.fetchone()[0]
            
            # 3. 插入添加项
            modifiers = item.get('modifiers', [])
            for modifier in modifiers:
                modifier_name = modifier.get('name')
                
                cursor.execute("""
                    INSERT INTO order_item_modifiers (
                        order_item_id, order_id, modifier_name
                    ) VALUES (
                        %s, %s, %s
                    )
                """, (
                    order_item_id, order_id, modifier_name
                ))
        
        conn.commit()
        print(f"✅ 订单 {order_id[:8]} 导入成功")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 订单导入失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cursor.close()


def import_from_raw_orders(db_config: Dict, limit: int = None, days: int = None, start_date: str = None):
    """
    从 raw_orders 表批量导入订单详情
    
    参数:
    - db_config: 数据库配置
    - limit: 限制导入数量（None 表示全部）
    - days: 导入最近N天的订单（None 表示全部）
    - start_date: 从指定日期开始导入（格式：YYYY-MM-DD）
    """
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # 查询 raw_orders 表中的 Deliveroo 订单
        where_clauses = ["platform = 'deliveroo'"]
        
        # 增量导入：只导入最近N天的订单
        if days:
            where_clauses.append(f"created_at >= CURRENT_DATE - INTERVAL '{days} days'")
        elif start_date:
            where_clauses.append(f"DATE(created_at) >= '{start_date}'")
        
        # 排除已导入的订单（根据 order_id）
        where_clauses.append("""
            order_id NOT IN (
                SELECT DISTINCT order_id FROM orders WHERE platform = 'deliveroo'
            )
        """)
        
        query = f"""
            SELECT id, order_id, store_code, payload
            FROM raw_orders
            WHERE {" AND ".join(where_clauses)}
            ORDER BY created_at DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if days:
            print(f"📊 找到 {len(rows)} 条最近 {days} 天的新订单")
        elif start_date:
            print(f"📊 找到 {len(rows)} 条从 {start_date} 开始的新订单")
        else:
            print(f"📊 找到 {len(rows)} 条新订单")
        
        success_count = 0
        fail_count = 0
        
        for row in rows:
            raw_id, order_id, store_code, payload = row
            
            try:
                order_data = json.loads(payload) if isinstance(payload, str) else payload
                if parse_and_insert_order(conn, order_data, store_code):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
                print(f"❌ 订单 {order_id} 解析失败: {e}")
        
        print(f"\n{'='*60}")
        print(f"✅ 导入完成")
        print(f"   成功: {success_count} 条")
        print(f"   失败: {fail_count} 条")
        print(f"{'='*60}\n")
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # 数据库配置（从环境变量读取）
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'delivery_data'),
        'user': os.getenv('DB_USER', 'delivery_user'),
        'password': os.getenv('DB_PASSWORD', 'delivery_pass')
    }
    
    # 获取命令行参数
    limit = None
    days = None
    start_date = None
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # 如果是数字，作为 limit
        if arg.isdigit():
            limit = int(arg)
        # 如果包含 'days=' 作为天数
        elif arg.startswith('days='):
            days = int(arg.split('=')[1])
        # 否则作为起始日期
        elif '-' in arg:
            start_date = arg
    
    # 导入订单
    import_from_raw_orders(DB_CONFIG, limit=limit, days=days, start_date=start_date)
