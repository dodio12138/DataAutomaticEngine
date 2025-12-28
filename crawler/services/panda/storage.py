"""存储后端抽象：目前提供文件存储实现，未来可以扩展为 PostgreSQL 等。

接口：save_raw_json(records, store_name, start_time, end_time, dest='file', **opts)
- records: list of parsed JSON objects or None
- dest: 'file'（当前实现）或 'postgres'（未来实现）
"""
import os
import datetime
import json
from typing import List, Dict, Any, Optional
from utils.db import get_conn


def save_raw_json_to_file(records, store_name, start_time, end_time, base_dir='.'):
    now = datetime.datetime.now()
    month_folder = now.strftime("%Y-%m")
    filename = f"{store_name}_{start_time.date()}_{end_time.date()}_orderdetail_raw.json"
    folder = os.path.join(base_dir, month_folder)
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, filename)

    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        print(f"成功保存 {len(records)} 条原始详情到：{full_path}")
    except Exception as e:
        print(f"保存 JSON 文件时出错: {e}")


def save_raw_json(records, store_name, start_time, end_time, dest='file', **opts):
    if dest == 'file':
        return save_raw_json_to_file(records, store_name, start_time, end_time, base_dir=opts.get('base_dir', '.'))
    else:
        raise NotImplementedError('only file dest implemented')


def _is_previous_day(dt: datetime.datetime, reference: datetime.date = None) -> bool:
    """判断给定 datetime 是否属于 reference 的前一天（默认 reference 为今天）。"""
    if reference is None:
        reference = datetime.datetime.now().date()
    try:
        d = dt.date()
    except Exception:
        return False
    return d == (reference - datetime.timedelta(days=1))


def save_orders_to_db(raw_list: List[Dict[str, Any]], platform: str = 'panda', start_time: Optional[datetime.datetime] = None, end_time: Optional[datetime.datetime] = None, store_code: Optional[str] = None, store_name: Optional[str] = None) -> int:
    """把原始订单数组拆分并写入 PostgreSQL。

    行为：
    - raw_list 是 API 返回的 JSON 数组（每个元素是一个订单 object）
    - 只保存 "前一天" 的订单（根据 createTimeStr 或 createTime 字段解析）
    - 对 (platform, orderSn) 做去重插入（使用 ON CONFLICT DO NOTHING）

    返回写入的记录数。
    """
    if not raw_list:
        return 0

    inserted = 0
    conn = None
    try:
        conn = get_conn()
        cur = conn.cursor()

        # 确保表存在（不在此处创建唯一索引以避免并发/重复创建问题）
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

        # 如果未提供 start/end，则默认为前一天范围
        today = datetime.datetime.now().date()
        if start_time is None and end_time is None:
            # 只选择前一天数据
            start_ref = datetime.datetime.combine(today - datetime.timedelta(days=1), datetime.time.min)
            end_ref = datetime.datetime.combine(today - datetime.timedelta(days=1), datetime.time.max)
        else:
            start_ref = start_time
            end_ref = end_time
        for item in raw_list:
            # 有些响应将真实订单对象包装在 data 字段内，优先取出 data
            obj = item
            if isinstance(item, dict) and 'data' in item and isinstance(item['data'], dict):
                obj = item['data']

            # 解析订单 id 和时间字段（兼容多种字段名）
            # 优先从data对象中获取
            order_id = obj.get('orderSn') or obj.get('order_id') or obj.get('orderId')
            time_str = obj.get('createTimeStr') or obj.get('createTime')
            
            # 如果obj是data，尝试从原item的data路径获取
            if not time_str and isinstance(item, dict) and 'data' in item:
                time_str = item['data'].get('createTimeStr') or item['data'].get('createTime')
            
            # 解析 feeInfoResqDTOList 中的各项费用
            estimated_revenue = None
            product_amount = None
            discount_amount = None
            
            if isinstance(obj, dict) and 'feeInfoResqDTOList' in obj:
                fee_list = obj.get('feeInfoResqDTOList', [])
                if isinstance(fee_list, list):
                    for fee_item in fee_list:
                        if not isinstance(fee_item, dict):
                            continue
                        
                        fee_name = fee_item.get('feeName', '')
                        fee_price = fee_item.get('feePrice', '0')
                        
                        try:
                            if fee_name == 'Estimated revenue':
                                estimated_revenue = float(fee_price)
                            elif fee_name == 'Product breakdown analysis(+)':
                                product_amount = float(fee_price)
                            elif fee_name == 'Discounted value by merchant(-)':
                                discount_amount = float(fee_price)
                        except (ValueError, TypeError):
                            pass
            
            # 计算打印单金额 = 产品金额 - 折扣金额
            print_amount = None
            if product_amount is not None and discount_amount is not None:
                print_amount = product_amount - discount_amount
            elif product_amount is not None:
                print_amount = product_amount
            
            order_dt = None
            if time_str:
                try:
                    # 支持 ISO 格式或常见 'YYYY-MM-DD HH:MM:SS'
                    order_dt = datetime.datetime.fromisoformat(time_str)
                except Exception:
                    try:
                        order_dt = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
                    except Exception:
                        order_dt = None

            # 只处理在 start_ref 到 end_ref 范围内的数据
            if order_dt is None:
                continue
            if start_ref and order_dt < start_ref:
                continue
            if end_ref and order_dt > end_ref:
                continue

            # 检查 order_id 与时间是否可用
            if not order_id:
                # 无法识别订单号，跳过并打印调试信息
                # 保持不抛出以免影响后续记录处理
                # print(f"跳过记录，无法解析 order_id: {obj}")
                continue

            # 使用 ON CONFLICT 实现去重和更新逻辑
            # 当 (platform, order_id) 相同但其他字段不同时，更新为新数据
            try:
                # payload 使用原始 item（保持 data 包装结构），以便后续调试与解析
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
                # 单条插入异常不影响后续
                print(f"插入订单 {order_id} 时出错: {e}")

        conn.commit()
        cur.close()
    except Exception as e:
        print(f"保存订单到 DB 时失败: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

    print(f"保存完成，写入 {inserted} 条记录")
    return inserted

