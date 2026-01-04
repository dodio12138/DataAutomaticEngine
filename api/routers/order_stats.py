"""订单详情统计查询路由"""
from fastapi import APIRouter
from utils import get_db_conn

router = APIRouter(prefix="/stats", tags=["statistics"])


@router.get("/orders/summary")
def get_orders_summary(store_code: str = None):
    """获取订单统计概览"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    where = f"WHERE store_code = '{store_code}'" if store_code else ""
    
    # 基础统计
    cur.execute(f"SELECT COUNT(*) FROM orders {where}")
    total_orders = cur.fetchone()[0]
    
    cur.execute(f"SELECT COUNT(*) FROM order_items oi JOIN orders o ON oi.order_id = o.order_id {where}")
    total_items = cur.fetchone()[0]
    
    cur.execute(f"SELECT COUNT(*) FROM order_item_modifiers oim JOIN orders o ON oim.order_id = o.order_id {where}")
    total_modifiers = cur.fetchone()[0]
    
    # 店铺分布
    cur.execute("SELECT store_code, COUNT(*) FROM orders GROUP BY store_code ORDER BY COUNT(*) DESC")
    stores = [{"store_code": row[0], "count": row[1]} for row in cur.fetchall()]
    
    # 最新订单
    cur.execute(f"""
        SELECT order_id, store_code, total_amount, placed_at
        FROM orders
        {where}
        ORDER BY placed_at DESC
        LIMIT 5
    """)
    recent_orders = [{
        "order_id": row[0],
        "store_code": row[1],
        "total_amount": float(row[2]) if row[2] else 0,
        "placed_at": row[3].isoformat() if row[3] else None
    } for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return {
        "total_orders": total_orders,
        "total_items": total_items,
        "total_modifiers": total_modifiers,
        "stores": stores,
        "recent_orders": recent_orders
    }


@router.get("/items/top")
def get_top_items(store_code: str = None, limit: int = 20, platform: str = None, date: str = None, start_date: str = None, end_date: str = None):
    """
    获取畅销菜品
    
    参数：
    - store_code: 店铺代码（可选）
    - limit: 返回数量（默认20）
    - platform: 平台筛选（hungrypanda/deliveroo，可选）
    - date: 日期筛选（YYYY-MM-DD，可选）
    - start_date: 起始日期（YYYY-MM-DD，可选）
    - end_date: 结束日期（YYYY-MM-DD，可选）
    """
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 构建 WHERE 子句
    where_clauses = []
    params = []
    
    if store_code:
        where_clauses.append("o.store_code = %s")
        params.append(store_code)
    
    if platform:
        # 标准化平台名称
        if platform.lower() in ['panda', 'hungrypanda']:
            where_clauses.append("o.platform = 'hungrypanda'")
        elif platform.lower() == 'deliveroo':
            where_clauses.append("o.platform = 'deliveroo'")
    
    # 日期筛选（支持单日或日期范围）
    if date:
        where_clauses.append("DATE(o.placed_at) = %s")
        params.append(date)
    elif start_date and end_date:
        where_clauses.append("DATE(o.placed_at) BETWEEN %s AND %s")
        params.append(start_date)
        params.append(end_date)
    elif start_date:
        where_clauses.append("DATE(o.placed_at) >= %s")
        params.append(start_date)
    
    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # 使用原始 JOIN 查询而不是视图，支持更灵活的筛选
    query = f"""
        SELECT 
            o.store_code,
            oi.item_name,
            COUNT(DISTINCT o.order_id) as order_count,
            SUM(oi.quantity) as total_quantity,
            AVG(oi.unit_price) as avg_price,
            SUM(oi.total_price) as total_revenue
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        {where}
        GROUP BY o.store_code, oi.item_name
        ORDER BY total_revenue DESC
        LIMIT %s
    """
    params.append(limit)
    
    cur.execute(query, params)
    
    items = [{
        "store_code": row[0],
        "item_name": row[1],
        "order_count": row[2],
        "total_quantity": row[3],
        "avg_price": float(row[4]) if row[4] else 0,
        "total_revenue": float(row[5]) if row[5] else 0
    } for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return items


@router.get("/modifiers/top")
def get_top_modifiers(store_code: str = None, limit: int = 20, platform: str = None, date: str = None, start_date: str = None, end_date: str = None):
    """
    获取热门添加项
    
    参数：
    - store_code: 店铺代码（可选）
    - limit: 返回数量（默认20）
    - platform: 平台筛选（hungrypanda/deliveroo，可选）
    - date: 日期筛选（YYYY-MM-DD，可选）
    - start_date: 起始日期（YYYY-MM-DD，可选）
    - end_date: 结束日期（YYYY-MM-DD，可选）
    """
    conn = get_db_conn()
    cur = conn.cursor()
    
    # 构建 WHERE 子句
    where_clauses = []
    params = []
    
    if store_code:
        where_clauses.append("o.store_code = %s")
        params.append(store_code)
    
    if platform:
        # 标准化平台名称
        if platform.lower() in ['panda', 'hungrypanda']:
            where_clauses.append("o.platform = 'hungrypanda'")
        elif platform.lower() == 'deliveroo':
            where_clauses.append("o.platform = 'deliveroo'")
    
    # 日期筛选（支持单日或日期范围）
    if date:
        where_clauses.append("DATE(o.placed_at) = %s")
        params.append(date)
    elif start_date and end_date:
        where_clauses.append("DATE(o.placed_at) BETWEEN %s AND %s")
        params.append(start_date)
        params.append(end_date)
    elif start_date:
        where_clauses.append("DATE(o.placed_at) >= %s")
        params.append(start_date)
    
    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # 查询热门添加项
    query = f"""
        SELECT 
            o.store_code,
            oim.modifier_name,
            COUNT(*) as usage_count,
            COUNT(DISTINCT oim.order_id) as unique_orders,
            CAST(COUNT(*) AS FLOAT) / COUNT(DISTINCT oim.order_id) as avg_per_order
        FROM order_item_modifiers oim
        JOIN orders o ON oim.order_id = o.order_id
        {where}
        GROUP BY o.store_code, oim.modifier_name
        ORDER BY usage_count DESC
        LIMIT %s
    """
    params.append(limit)
    
    cur.execute(query, params)
    
    modifiers = [{
        "store_code": row[0],
        "modifier_name": row[1],
        "usage_count": row[2],
        "unique_orders": row[3],
        "avg_per_order": float(row[4]) if row[4] else 0
    } for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return modifiers


@router.get("/orders/details")
def get_order_details(store_code: str = None, date: str = None, limit: int = 30):
    """获取订单详情列表"""
    conn = get_db_conn()
    cur = conn.cursor()
    
    where_clauses = []
    if store_code:
        where_clauses.append(f"store_code = '{store_code}'")
    if date:
        where_clauses.append(f"DATE(placed_at) = '{date}'")
    
    where = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    cur.execute(f"""
        SELECT order_id, short_drn, order_number, store_code,
               total_amount, status, placed_at,
               item_name, quantity, total_price, modifiers
        FROM v_order_details
        {where}
        ORDER BY placed_at DESC
        LIMIT {limit}
    """)
    
    orders = [{
        "order_id": row[0],
        "short_drn": row[1],
        "order_number": row[2],
        "store_code": row[3],
        "total_amount": float(row[4]) if row[4] else 0,
        "status": row[5],
        "placed_at": row[6].isoformat() if row[6] else None,
        "item_name": row[7],
        "quantity": row[8],
        "total_price": float(row[9]) if row[9] else 0,
        "modifiers": row[10] if row[10] else []
    } for row in cur.fetchall()]
    
    cur.close()
    conn.close()
    
    return {"orders": orders, "total": len(orders)}
