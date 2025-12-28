"""存储后端抽象：提供文件存储实现和数据库保存功能"""
import os
import datetime
import json
from typing import List, Dict, Any, Optional
from utils.db import get_conn


def save_order_details_to_file(data, store_name, start_date, end_date, base_dir='.'):
    """保存订单详情到JSON文件"""
    now = datetime.datetime.now()
    month_folder = now.strftime("%Y-%m")
    filename = f"{store_name}_{start_date}_{end_date}_orders_detail.json"
    folder = os.path.join(base_dir, month_folder)
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, filename)

    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 成功保存订单详情到：{full_path}")
        return full_path
    except Exception as e:
        print(f"❌ 保存 JSON 文件时出错: {e}")
        return None


def save_order_list_to_file(orders, store_name, start_date, end_date, base_dir='.'):
    """保存订单列表到JSON文件"""
    now = datetime.datetime.now()
    month_folder = now.strftime("%Y-%m")
    filename = f"{store_name}_{start_date}_{end_date}_orders_list.json"
    folder = os.path.join(base_dir, month_folder)
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, filename)

    data = {
        'total_orders': len(orders),
        'date_range': {
            'start': start_date,
            'end': end_date
        },
        'orders': orders
    }

    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ 成功保存订单列表到：{full_path}")
        return full_path
    except Exception as e:
        print(f"❌ 保存 JSON 文件时出错: {e}")
        return None


def save_partial_data(orders, store_name, start_date, end_date, base_dir='.'):
    """保存部分数据（用于错误恢复）"""
    now = datetime.datetime.now()
    month_folder = now.strftime("%Y-%m")
    filename = f"{store_name}_{start_date}_{end_date}_orders_partial.json"
    folder = os.path.join(base_dir, month_folder)
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, filename)

    data = {
        'total_orders': len(orders),
        'orders': orders
    }

    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"⚠️ 已保存部分数据到：{full_path}")
        return full_path
    except Exception as e:
        print(f"❌ 保存部分数据时出错: {e}")
        return None


def save_orders_to_db(raw_list: List[Dict[str, Any]], platform: str = 'deliveroo', 
                     start_time: Optional[datetime.datetime] = None, 
                     end_time: Optional[datetime.datetime] = None, 
                     store_code: Optional[str] = None, 
                     store_name: Optional[str] = None) -> int:
    """把原始订单数组写入 PostgreSQL raw_orders 表。

    参数：
    - raw_list: API 返回的 JSON 数组（每个元素是一个订单 object）
    - platform: 平台标识 'deliveroo'
    - start_time/end_time: 可选的时间范围过滤
    - store_code: 英文店铺代码
    - store_name: 中文店铺名

    行为：
    - 根据订单时间字段 (timeline.placed_at 或 created_at) 进行时间过滤
    - 对 (platform, order_id) 做去重插入（使用 ON CONFLICT DO NOTHING）
    - 返回实际写入的记录数

    Deliveroo订单结构参考：
    {
        "order_id": "...",
        "timeline": {
            "placed_at": "2025-12-20T10:30:00Z",
            ...
        },
        "pricing": {
            "total": {...},
            "subtotal": {...},
            ...
        },
        ...
    }
    """
    if not raw_list:
        return 0

    inserted = 0
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 确保表存在
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_orders (
                id SERIAL PRIMARY KEY,
                platform TEXT NOT NULL,
                store_code TEXT,
                store_name TEXT,
                order_id TEXT NOT NULL,
                order_date TIMESTAMP,
                estimated_revenue NUMERIC(10,2),
                product_amount NUMERIC(10,2),
                discount_amount NUMERIC(10,2),
                print_amount NUMERIC(10,2),
                payload JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            );
            """
        )

        # 如果未提供 start/end，则使用前一天范围
        today = datetime.datetime.now().date()
        if start_time is None and end_time is None:
            start_ref = datetime.datetime.combine(today - datetime.timedelta(days=1), datetime.time.min)
            end_ref = datetime.datetime.combine(today - datetime.timedelta(days=1), datetime.time.max)
        else:
            start_ref = start_time
            end_ref = end_time

        for item in raw_list:
            # Deliveroo 订单结构
            obj = item
            
            # 解析订单 ID
            order_id = obj.get('order_id') or obj.get('id')
            
            # 解析订单时间（从 timeline.placed_at 或其他字段）
            time_str = None
            timeline = obj.get('timeline', {})
            if isinstance(timeline, dict):
                time_str = (timeline.get('placed_at') or 
                           timeline.get('created_at') or 
                           timeline.get('accepted_at'))
            
            if not time_str:
                time_str = obj.get('created_at') or obj.get('placed_at')
            
            order_dt = None
            if time_str:
                try:
                    # Deliveroo 使用 ISO 格式，移除时区信息保持与 panda 一致
                    dt = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    # 转换为不带时区的本地时间
                    order_dt = dt.replace(tzinfo=None)
                except Exception as e:
                    try:
                        order_dt = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    except Exception as e2:
                        order_dt = None

            # 时间范围过滤（添加调试信息）
            if order_dt is None:
                continue
            
            # 打印前3条订单的时间信息用于调试
            if inserted < 3:
                print(f"📅 订单 {order_id}: 时间={order_dt}, 范围={start_ref} 到 {end_ref}")
            
            if start_ref and order_dt < start_ref:
                continue
            if end_ref and order_dt > end_ref:
                continue

            # 解析金额字段（从 amount 对象）
            estimated_revenue = None
            product_amount = None
            discount_amount = None
            print_amount = None
            
            # Deliveroo 实际使用 amount 字段而不是 pricing
            # JSON 结构：{"amount": {"fractional": 1899, "formatted": "£18.99", "currency_code": "GBP"}}
            amount_obj = obj.get('amount', {})
            if isinstance(amount_obj, dict):
                try:
                    # 订单总金额（fractional 单位是便士）
                    fractional_amount = amount_obj.get('fractional', 0)
                    if fractional_amount:
                        estimated_revenue = float(fractional_amount) / 100  # 转换为英镑
                        product_amount = float(fractional_amount) / 100
                    
                    # 查找折扣（如果有 discounts 或 adjustments 字段）
                    discounts = obj.get('discounts', [])
                    adjustments = obj.get('adjustments', [])
                    
                    total_discount = 0
                    if isinstance(discounts, list):
                        for d in discounts:
                            if isinstance(d, dict):
                                d_fractional = d.get('amount', {}).get('fractional', 0)
                                total_discount += float(d_fractional)
                    
                    if isinstance(adjustments, list):
                        for a in adjustments:
                            if isinstance(a, dict):
                                a_fractional = a.get('amount', {}).get('fractional', 0)
                                total_discount += float(a_fractional)
                    
                    if total_discount > 0:
                        discount_amount = total_discount / 100
                    
                    # 计算打印金额（产品金额 - 折扣）
                    if product_amount is not None:
                        if discount_amount is not None:
                            print_amount = product_amount - discount_amount
                        else:
                            print_amount = product_amount
                    
                except (ValueError, TypeError, KeyError) as e:
                    print(f"解析金额字段失败: {e}")

            if not order_id:
                continue

            # 使用 ON CONFLICT 实现去重和更新逻辑
            # 当 (platform, order_id) 相同但其他字段不同时，更新为新数据
            try:
                # 插入数据，冲突时更新
                if store_code or store_name:
                    cur.execute(
                        """INSERT INTO raw_orders 
                           (platform, store_code, store_name, order_id, order_date, 
                            estimated_revenue, product_amount, discount_amount, print_amount, payload) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (platform, order_id) 
                           DO UPDATE SET
                               store_code = EXCLUDED.store_code,
                               store_name = EXCLUDED.store_name,
                               order_date = EXCLUDED.order_date,
                               estimated_revenue = EXCLUDED.estimated_revenue,
                               product_amount = EXCLUDED.product_amount,
                               discount_amount = EXCLUDED.discount_amount,
                               print_amount = EXCLUDED.print_amount,
                               payload = EXCLUDED.payload
                           WHERE raw_orders.store_code IS DISTINCT FROM EXCLUDED.store_code
                              OR raw_orders.store_name IS DISTINCT FROM EXCLUDED.store_name
                              OR raw_orders.order_date IS DISTINCT FROM EXCLUDED.order_date
                              OR raw_orders.estimated_revenue IS DISTINCT FROM EXCLUDED.estimated_revenue
                              OR raw_orders.product_amount IS DISTINCT FROM EXCLUDED.product_amount
                              OR raw_orders.discount_amount IS DISTINCT FROM EXCLUDED.discount_amount
                              OR raw_orders.print_amount IS DISTINCT FROM EXCLUDED.print_amount
                              OR raw_orders.payload IS DISTINCT FROM EXCLUDED.payload""",
                        (platform, store_code, store_name, order_id, order_dt, 
                         estimated_revenue, product_amount, discount_amount, print_amount, 
                         json.dumps(item))
                    )
                else:
                    cur.execute(
                        """INSERT INTO raw_orders 
                           (platform, order_id, order_date, estimated_revenue, 
                            product_amount, discount_amount, print_amount, payload) 
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (platform, order_id) 
                           DO UPDATE SET
                               order_date = EXCLUDED.order_date,
                               estimated_revenue = EXCLUDED.estimated_revenue,
                               product_amount = EXCLUDED.product_amount,
                               discount_amount = EXCLUDED.discount_amount,
                               print_amount = EXCLUDED.print_amount,
                               payload = EXCLUDED.payload
                           WHERE raw_orders.order_date IS DISTINCT FROM EXCLUDED.order_date
                              OR raw_orders.estimated_revenue IS DISTINCT FROM EXCLUDED.estimated_revenue
                              OR raw_orders.product_amount IS DISTINCT FROM EXCLUDED.product_amount
                              OR raw_orders.discount_amount IS DISTINCT FROM EXCLUDED.discount_amount
                              OR raw_orders.print_amount IS DISTINCT FROM EXCLUDED.print_amount
                              OR raw_orders.payload IS DISTINCT FROM EXCLUDED.payload""",
                        (platform, order_id, order_dt, estimated_revenue, 
                         product_amount, discount_amount, print_amount, json.dumps(item))
                    )
                
                if cur.rowcount > 0:
                    inserted += cur.rowcount
            except Exception as e:
                print(f"插入订单 {order_id} 时出错: {e}")

        conn.commit()
        cur.close()
    except Exception as e:
        print(f"保存 Deliveroo 订单到 DB 时失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

    print(f"保存完成，写入 {inserted} 条 Deliveroo 订单记录")
    return inserted

