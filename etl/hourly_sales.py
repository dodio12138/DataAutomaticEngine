#!/usr/bin/env python3
"""
每小时销售数据聚合 ETL
从 orders 表（Deliveroo 详情）和 raw_orders（HungryPanda）聚合每小时订单量和销售额
"""
import os
import sys
from datetime import datetime, timedelta, date
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "delivery_data"),
        user=os.environ.get("DB_USER", "delivery_user"),
        password=os.environ.get("DB_PASSWORD", "delivery_pass"),
        cursor_factory=RealDictCursor
    )


def aggregate_hourly_sales(start_date: str = None, end_date: str = None):
    """
    聚合每小时销售数据
    
    Args:
        start_date: 开始日期 YYYY-MM-DD，不传则默认为昨天
        end_date: 结束日期 YYYY-MM-DD，不传则默认为昨天
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 如果都不传参数，默认聚合昨天的数据
    if start_date is None and end_date is None:
        yesterday = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        start_date = yesterday
        end_date = yesterday
    elif end_date is None:
        end_date = start_date
    
    print(f"📊 聚合每小时销售数据")
    print(f"时间范围: {start_date} ~ {end_date}")
    print("=" * 60)
    print()
    
    # 1. 聚合 Deliveroo 数据（从 orders 表）
    # 使用总营业额 total_amount
    print("🔄 处理 Deliveroo 数据...")
    deliveroo_query = """
        INSERT INTO hourly_sales (date_time, date, hour, store_code, store_name, platform, order_count, total_sales)
        SELECT 
            DATE_TRUNC('hour', placed_at) AS date_time,
            DATE(placed_at) AS date,
            EXTRACT(HOUR FROM placed_at)::INTEGER AS hour,
            store_code,
            MAX(s.name_cn) AS store_name,
            'deliveroo' AS platform,
            COUNT(*) AS order_count,
            SUM(total_amount) AS total_sales
        FROM orders o
        LEFT JOIN stores s ON o.store_code = s.code
        WHERE 
            DATE(placed_at) >= %s
            AND DATE(placed_at) <= %s
            AND status = 'delivered'
            AND store_code IS NOT NULL
        GROUP BY DATE_TRUNC('hour', placed_at), DATE(placed_at), EXTRACT(HOUR FROM placed_at), store_code
        ON CONFLICT (date_time, store_code, platform) 
        DO UPDATE SET
            order_count = EXCLUDED.order_count,
            total_sales = EXCLUDED.total_sales,
            store_name = EXCLUDED.store_name,
            updated_at = CURRENT_TIMESTAMP
    """
    
    cur.execute(deliveroo_query, (start_date, end_date))
    deliveroo_count = cur.rowcount
    print(f"  ✅ Deliveroo: {deliveroo_count} 条小时记录")
    
    # 2. 聚合 HungryPanda 数据（从 raw_orders 表）
    # 使用总营业额 fixedPrice（从 payload 提取）
    print("🔄 处理 HungryPanda 数据...")
    panda_query = """
        INSERT INTO hourly_sales (date_time, date, hour, store_code, store_name, platform, order_count, total_sales)
        SELECT 
            DATE_TRUNC('hour', order_date) AS date_time,
            DATE(order_date) AS date,
            EXTRACT(HOUR FROM order_date)::INTEGER AS hour,
            store_code,
            MAX(s.name_cn) AS store_name,
            'hungrypanda' AS platform,
            COUNT(*) AS order_count,
            SUM((payload->'data'->>'fixedPrice')::numeric) AS total_sales
        FROM raw_orders ro
        LEFT JOIN stores s ON ro.store_code = s.code
        WHERE 
            DATE(order_date) >= %s
            AND DATE(order_date) <= %s
            AND ro.platform = 'panda'
            AND ro.store_code IS NOT NULL
            AND (payload->'data'->>'orderStatus')::int != 8
        GROUP BY DATE_TRUNC('hour', order_date), DATE(order_date), EXTRACT(HOUR FROM order_date), store_code
        ON CONFLICT (date_time, store_code, platform) 
        DO UPDATE SET
            order_count = EXCLUDED.order_count,
            total_sales = EXCLUDED.total_sales,
            store_name = EXCLUDED.store_name,
            updated_at = CURRENT_TIMESTAMP
    """
    
    cur.execute(panda_query, (start_date, end_date))
    panda_count = cur.rowcount
    print(f"  ✅ HungryPanda: {panda_count} 条小时记录")
    
    conn.commit()
    
    # 3. 查看聚合结果统计
    print()
    print("📈 聚合结果统计:")
    print("-" * 60)
    
    stats_query = """
        SELECT 
            date,
            store_code,
            platform,
            COUNT(*) as hour_count,
            SUM(order_count) as total_orders,
            SUM(total_sales) as total_sales
        FROM hourly_sales
        WHERE date >= %s AND date <= %s
        GROUP BY date, store_code, platform
        ORDER BY date DESC, store_code, platform
    """
    
    cur.execute(stats_query, (start_date, end_date))
    stats = cur.fetchall()
    
    if stats:
        print(f"{'日期':<12} {'店铺':<20} {'平台':<12} {'时段数':<8} {'订单数':<8} {'销售额':<10}")
        print("-" * 60)
        for row in stats:
            print(f"{row['date']} {row['store_code']:<20} {row['platform']:<12} "
                  f"{row['hour_count']:<8} {row['total_orders']:<8} £{float(row['total_sales']):.2f}")
    else:
        print("⚠️  没有数据被聚合（可能该时间段内没有订单）")
    
    cur.close()
    conn.close()
    
    print()
    print(f"✅ 完成！共处理 {deliveroo_count + panda_count} 条小时记录")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="聚合每小时销售数据")
    parser.add_argument("--start-date", help="开始日期 YYYY-MM-DD（默认昨天）")
    parser.add_argument("--end-date", help="结束日期 YYYY-MM-DD（默认昨天）")
    parser.add_argument("--date", help="单个日期 YYYY-MM-DD（默认昨天）")
    
    args = parser.parse_args()
    
    start_date = args.start_date or args.date
    end_date = args.end_date or args.date
    
    try:
        aggregate_hourly_sales(start_date, end_date)
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
