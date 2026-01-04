"""快速测试版：从 raw_orders 导入到订单详情表"""
import json
import psycopg2
import os
import sys

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'delivery_data'),
    'user': os.getenv('DB_USER', 'delivery_user'),
    'password': os.getenv('DB_PASSWORD', 'delivery_pass')
}


def parse_and_insert_order(conn, raw_order_data):
    """解析并插入单个订单"""
    cursor = conn.cursor()
    
    try:
        # 1. 插入订单主表
        order_id = raw_order_data.get('drn_id')
        restaurant_id = raw_order_data.get('restaurant_id')
        
        # 金额
        amount = raw_order_data.get('amount', {})
        total_amount = amount.get('fractional', 0) / 100.0
        
        # 状态
        status = raw_order_data.get('status')
        
        # 时间线
        timeline = raw_order_data.get('timeline', {})
        placed_at = timeline.get('placed_at')
        
        cursor.execute("""
            INSERT INTO orders (
                order_id, restaurant_id, total_amount, status, placed_at, raw_data
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (order_id, platform) DO UPDATE SET
                status = EXCLUDED.status
            RETURNING id
        """, (
            order_id, restaurant_id, total_amount, status, placed_at,
            json.dumps(raw_order_data)
        ))
        
        # 2. 插入订单菜品和添加项
        items = raw_order_data.get('items', [])
        for item in items:
            item_name = item.get('name')
            category_name = item.get('category_name')
            quantity = item.get('quantity', 1)
            
            unit_price = item.get('unit_price', {}).get('fractional', 0) / 100.0
            total_price = item.get('total_price', {}).get('fractional', 0) / 100.0
            
            cursor.execute("""
                INSERT INTO order_items (
                    order_id, item_name, category_name, quantity,
                    unit_price, total_price
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                order_id, item_name, category_name, quantity,
                unit_price, total_price
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
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 订单 {raw_order_data.get('drn_id', 'unknown')} 导入失败: {e}")
        return False
    finally:
        cursor.close()


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT order_id, payload
            FROM raw_orders
            WHERE platform = 'deliveroo'
            ORDER BY created_at DESC
        """
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        print(f"📊 找到 {len(rows)} 条 Deliveroo 订单")
        print("")
        
        success = 0
        fail = 0
        
        for order_id, payload in rows:
            try:
                order_data = json.loads(payload) if isinstance(payload, str) else payload
                if parse_and_insert_order(conn, order_data):
                    success += 1
                    print(f"✅ {order_data.get('drn_id', order_id)[:8]}... ({success}/{len(rows)})")
                else:
                    fail += 1
            except Exception as e:
                fail += 1
                print(f"❌ {order_id} 解析失败: {e}")
        
        print("")
        print("="*60)
        print(f"✅ 导入完成: 成功 {success} 条, 失败 {fail} 条")
        print("="*60)
        
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
