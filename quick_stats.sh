#!/bin/bash
# 快速查看订单统计
docker exec delivery_api python3 << 'PYEOF'
import psycopg2
conn = psycopg2.connect(host='db', database='delivery_data', user='delivery_user', password='delivery_pass')
cur = conn.cursor()

print("\n📊 订单统计")
print("="*60)

cur.execute("SELECT COUNT(*) FROM orders")
print(f"订单总数: {cur.fetchone()[0]}")

cur.execute("SELECT store_code, COUNT(*) FROM orders GROUP BY store_code ORDER BY store_code")
print("\n按店铺分布:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]} 条")

cur.execute("SELECT COUNT(*) FROM order_items")
print(f"\n菜品记录: {cur.fetchone()[0]}")

cur.execute("SELECT COUNT(*) FROM order_item_modifiers")
print(f"添加项记录: {cur.fetchone()[0]}")

print("\n最新5条订单:")
cur.execute("""
    SELECT order_id, store_code, total_amount, 
           TO_CHAR(placed_at, 'YYYY-MM-DD HH24:MI') as time
    FROM orders 
    ORDER BY placed_at DESC 
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"  {row[0][:12]}... | {row[1]} | £{row[2]} | {row[3]}")

conn.close()
print("="*60 + "\n")
PYEOF
