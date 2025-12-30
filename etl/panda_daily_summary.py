#!/usr/bin/env python3
"""
HungryPanda 每日销售汇总计算
- 从 orders 和 order_items 表读取原始订单数据
- 按店铺和日期聚合计算 gross_sales, net_sales, order_count, avg_order_value
- 客单价按折后价（实际支付金额）计算
- 插入到 daily_sales_summary 表
"""
import os
import sys
from datetime import datetime, timedelta
from typing import List
import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_conn():
    """获取数据库连接"""
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "db"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "delivery_data"),
        user=os.environ.get("DB_USER", "delivery_user"),
        password=os.environ.get("DB_PASSWORD", "delivery_pass"),
        connect_timeout=5,
    )


def get_store_codes() -> List[str]:
    """从数据库获取所有 HungryPanda 店铺代码"""
    conn = get_db_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DISTINCT store_code 
            FROM raw_orders 
            WHERE platform = 'panda' 
              AND store_code IS NOT NULL
            ORDER BY store_code
        """)
        codes = [row[0] for row in cursor.fetchall()]
        return codes
    finally:
        cursor.close()
        conn.close()


def calculate_daily_summary(store_codes: List[str], dates: List[str]) -> dict:
    """
    计算指定店铺和日期的每日汇总
    
    从 raw_orders 表直接读取字段聚合：
    - gross_sales = SUM(product_amount)  # 商品原价总和（折前）
    - net_sales = SUM(print_amount)      # 实际支付总和（折后 = product - 折扣）
    - order_count = COUNT(DISTINCT order_id)
    - avg_order_value = net_sales / order_count（客单价按折后价）
    """
    conn = get_db_conn()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    results = {"success": 0, "failed": 0, "details": []}
    
    try:
        for code in store_codes:
            for date_str in dates:
                print(f"\n{'='*60}")
                print(f"🏪 店铺: {code}, 📅 日期: {date_str}")
                print(f"{'='*60}")
                
                # 直接从 raw_orders 表聚合计算
                cursor.execute("""
                    SELECT 
                        store_code,
                        store_name,
                        COUNT(DISTINCT order_id) as order_count,
                        SUM(COALESCE(product_amount, 0)) as gross_sales,
                        SUM(COALESCE(print_amount, 0)) as net_sales
                    FROM raw_orders
                    WHERE platform = 'panda'
                      AND store_code = %s
                      AND DATE(order_date) = %s
                    GROUP BY store_code, store_name
                """, (code, date_str))
                
                row = cursor.fetchone()
                
                if not row or row['order_count'] == 0:
                    print(f"   ℹ️ 无订单数据")
                    results["details"].append({
                        "store_code": code,
                        "date": date_str,
                        "status": "NO_DATA"
                    })
                    continue
                
                store_name = row['store_name'] or code
                order_count = int(row['order_count'])
                gross_sales = float(row['gross_sales'] or 0)
                net_sales = float(row['net_sales'] or 0)
                avg_order_value = round(net_sales / order_count, 2) if order_count > 0 else 0.0
                
                print(f"   📊 订单数: {order_count}")
                print(f"   💰 商品总额（折前）: £{gross_sales:.2f}")
                print(f"   💵 实际支付（折后）: £{net_sales:.2f}")
                print(f"   📈 平均客单价: £{avg_order_value:.2f}")
                
                # 插入或更新 daily_sales_summary
                try:
                    cursor.execute("""
                        INSERT INTO daily_sales_summary (
                            date, store_code, store_name, platform,
                            gross_sales, net_sales, order_count, avg_order_value,
                            created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, 'panda',
                            %s, %s, %s, %s,
                            NOW(), NOW()
                        )
                        ON CONFLICT (date, store_code, platform)
                        DO UPDATE SET
                            store_name = EXCLUDED.store_name,
                            gross_sales = EXCLUDED.gross_sales,
                            net_sales = EXCLUDED.net_sales,
                            order_count = EXCLUDED.order_count,
                            avg_order_value = EXCLUDED.avg_order_value,
                            updated_at = NOW()
                    """, (
                        date_str,
                        code,
                        store_name,
                        gross_sales,
                        net_sales,
                        order_count,
                        avg_order_value
                    ))
                    conn.commit()
                    print(f"   ✅ 入库完成")
                    results["success"] += 1
                    results["details"].append({
                        "store_code": code,
                        "date": date_str,
                        "status": "OK"
                    })
                except Exception as e:
                    conn.rollback()
                    print(f"   ❌ 入库失败: {e}")
                    results["failed"] += 1
                    results["details"].append({
                        "store_code": code,
                        "date": date_str,
                        "status": "FAILED",
                        "error": str(e)
                    })
        
        return results
    
    finally:
        cursor.close()
        conn.close()


def main():
    """主函数，支持命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="HungryPanda 每日销售汇总计算")
    parser.add_argument("--stores", type=str, default="all", help="店铺代码（逗号分隔）或 'all'（默认）")
    parser.add_argument("--dates", type=str, help="日期 YYYY-MM-DD 或范围 'YYYY-MM-DD,YYYY-MM-DD'（默认昨天）")
    
    args = parser.parse_args()
    
    # 解析店铺
    if args.stores.lower() == "all":
        print("🔍 获取所有 HungryPanda 店铺...")
        store_codes = get_store_codes()
        if not store_codes:
            print("❌ 未找到任何 HungryPanda 店铺数据")
            sys.exit(1)
    else:
        store_codes = [s.strip() for s in args.stores.split(",") if s.strip()]
    
    # 解析日期
    if args.dates:
        dates_arg = args.dates.strip()
        if "," in dates_arg:
            # 日期范围
            start_str, end_str = [d.strip() for d in dates_arg.split(",", 1)]
            start = datetime.strptime(start_str, "%Y-%m-%d")
            end = datetime.strptime(end_str, "%Y-%m-%d")
            dates = []
            cur = start
            while cur <= end:
                dates.append(cur.strftime("%Y-%m-%d"))
                cur += timedelta(days=1)
        else:
            # 单日
            datetime.strptime(dates_arg, "%Y-%m-%d")  # 校验格式
            dates = [dates_arg]
    else:
        # 默认昨天
        yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        dates = [yesterday]
    
    print("\n" + "="*60)
    print("HungryPanda 每日销售汇总计算")
    print("="*60)
    print(f"📦 店铺: {store_codes}")
    print(f"📅 日期: {dates}")
    print("="*60 + "\n")
    
    try:
        result = calculate_daily_summary(store_codes, dates)
        
        print("\n" + "="*60)
        print("✅ 执行完成")
        print("="*60)
        print(f"📊 成功: {result['success']} 条")
        print(f"❌ 失败: {result['failed']} 条")
        print("="*60 + "\n")
        
        if result['failed'] > 0:
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
