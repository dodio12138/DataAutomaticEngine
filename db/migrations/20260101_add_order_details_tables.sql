-- 订单详情表结构设计
-- 用于存储 Deliveroo 订单的详细信息，支持菜品和添加项统计

-- 1. 订单主表
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) NOT NULL,           -- Deliveroo 订单 ID (drn_id)
    short_drn VARCHAR(50),                    -- 短订单号 (如 gb:880649)
    order_number VARCHAR(50),                 -- 店铺订单号 (如 183)
    restaurant_id VARCHAR(50) NOT NULL,       -- 店铺 ID
    store_code VARCHAR(50),                   -- 店铺英文代码
    platform VARCHAR(20) DEFAULT 'deliveroo', -- 平台
    
    -- 金额信息
    total_amount DECIMAL(10,2),               -- 订单总金额
    paid_in_cash DECIMAL(10,2),               -- 现金支付金额
    currency_code VARCHAR(10) DEFAULT 'GBP',  -- 货币代码
    
    -- 订单状态
    status VARCHAR(50),                       -- 订单状态 (delivered, cancelled 等)
    rejection_reason TEXT,                    -- 拒绝原因
    
    -- 时间线
    placed_at TIMESTAMP,                      -- 下单时间
    accepted_at TIMESTAMP,                    -- 接单时间
    confirmed_at TIMESTAMP,                   -- 确认时间
    prepare_for TIMESTAMP,                    -- 准备时间
    delivery_picked_up_at TIMESTAMP,          -- 取餐时间
    
    -- 客户信息
    customer_id INTEGER,                      -- 客户 ID
    
    -- 原始数据
    raw_data JSONB,                           -- 完整原始 JSON
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_deliveroo_order UNIQUE (order_id, platform)
);

CREATE INDEX idx_orders_restaurant_id ON orders(restaurant_id);
CREATE INDEX idx_orders_store_code ON orders(store_code);
CREATE INDEX idx_orders_placed_at ON orders(placed_at);
CREATE INDEX idx_orders_status ON orders(status);


-- 2. 订单菜品表（主菜品）
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(100) NOT NULL,           -- 关联订单 ID
    item_name VARCHAR(500) NOT NULL,          -- 菜品名称
    category_name VARCHAR(255),               -- 菜品分类
    quantity INTEGER DEFAULT 1,               -- 数量
    
    -- 价格信息
    unit_price DECIMAL(10,2),                 -- 单价
    total_price DECIMAL(10,2),                -- 总价（含添加项）
    total_unit_price DECIMAL(10,2),           -- 单品总价
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_item_name ON order_items(item_name);
CREATE INDEX idx_order_items_category_name ON order_items(category_name);


-- 3. 菜品添加项表（配料、加料等）
CREATE TABLE IF NOT EXISTS order_item_modifiers (
    id SERIAL PRIMARY KEY,
    order_item_id INTEGER NOT NULL,           -- 关联订单菜品 ID
    order_id VARCHAR(100) NOT NULL,           -- 关联订单 ID（冗余，方便查询）
    modifier_name VARCHAR(500) NOT NULL,      -- 添加项名称
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (order_item_id) REFERENCES order_items(id) ON DELETE CASCADE
);

CREATE INDEX idx_order_item_modifiers_order_item_id ON order_item_modifiers(order_item_id);
CREATE INDEX idx_order_item_modifiers_order_id ON order_item_modifiers(order_id);
CREATE INDEX idx_order_item_modifiers_modifier_name ON order_item_modifiers(modifier_name);


-- 4. 创建统计视图：主菜品销量统计（支持按店铺统计）
CREATE OR REPLACE VIEW v_item_sales_stats AS
SELECT 
    o.store_code,                             -- 店铺代码
    o.restaurant_id,                          -- 店铺ID
    oi.item_name,
    oi.category_name,
    COUNT(*) as order_count,                  -- 被点次数
    SUM(oi.quantity) as total_quantity,       -- 总数量
    ROUND(AVG(oi.total_price)::numeric, 2) as avg_price,      -- 平均价格
    ROUND(SUM(oi.total_price)::numeric, 2) as total_revenue,  -- 总收入
    COUNT(DISTINCT oi.order_id) as unique_orders -- 不同订单数
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'delivered'
GROUP BY o.store_code, o.restaurant_id, oi.item_name, oi.category_name
ORDER BY order_count DESC;


-- 5. 创建统计视图：添加项销量统计（支持按店铺统计）
CREATE OR REPLACE VIEW v_modifier_sales_stats AS
SELECT 
    o.store_code,                             -- 店铺代码
    o.restaurant_id,                          -- 店铺ID
    oim.modifier_name,
    COUNT(*) as order_count,                  -- 被添加次数
    COUNT(DISTINCT oim.order_id) as unique_orders, -- 不同订单数
    ROUND(COUNT(*)::numeric / COUNT(DISTINCT oim.order_id), 2) as avg_per_order -- 平均每单添加次数
FROM order_item_modifiers oim
JOIN orders o ON oim.order_id = o.order_id
WHERE o.status = 'delivered'
GROUP BY o.store_code, o.restaurant_id, oim.modifier_name
ORDER BY order_count DESC;


-- 6. 创建统计视图：主菜品与添加项组合统计（支持按店铺统计）
CREATE OR REPLACE VIEW v_item_modifier_combination AS
SELECT 
    o.store_code,                             -- 店铺代码
    o.restaurant_id,                          -- 店铺ID
    oi.item_name,
    oim.modifier_name,
    COUNT(*) as combination_count,            -- 组合出现次数
    COUNT(DISTINCT oim.order_id) as unique_orders
FROM order_items oi
JOIN order_item_modifiers oim ON oi.id = oim.order_item_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'delivered'
GROUP BY o.store_code, o.restaurant_id, oi.item_name, oim.modifier_name
ORDER BY combination_count DESC;


-- 7. 创建统计视图：按日期统计菜品销量（支持按店铺统计）
CREATE OR REPLACE VIEW v_daily_item_sales AS
SELECT 
    o.store_code,                             -- 店铺代码
    o.restaurant_id,                          -- 店铺ID
    DATE(o.placed_at) as order_date,
    oi.item_name,
    oi.category_name,
    COUNT(*) as order_count,
    SUM(oi.quantity) as total_quantity,
    ROUND(SUM(oi.total_price)::numeric, 2) as total_revenue
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'delivered'
GROUP BY o.store_code, o.restaurant_id, DATE(o.placed_at), oi.item_name, oi.category_name
ORDER BY order_date DESC, order_count DESC;


-- 8. 创建订单详情视图：完整的订单+菜品信息（支持按时间、店铺、订单ID检索）
CREATE OR REPLACE VIEW v_order_details AS
SELECT 
    o.order_id,
    o.short_drn,
    o.order_number,
    o.store_code,
    o.restaurant_id,
    o.platform,
    o.total_amount,
    o.status,
    o.placed_at,
    o.accepted_at,
    o.confirmed_at,
    o.delivery_picked_up_at,
    DATE(o.placed_at) as order_date,
    EXTRACT(HOUR FROM o.placed_at) as order_hour,
    oi.id as order_item_id,
    oi.item_name,
    oi.category_name,
    oi.quantity,
    oi.unit_price,
    oi.total_price,
    -- 添加项汇总（数组形式）
    ARRAY_AGG(DISTINCT oim.modifier_name) FILTER (WHERE oim.modifier_name IS NOT NULL) as modifiers
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN order_item_modifiers oim ON oi.id = oim.order_item_id
GROUP BY 
    o.order_id, o.short_drn, o.order_number, o.store_code, o.restaurant_id,
    o.platform, o.total_amount, o.status, o.placed_at, o.accepted_at,
    o.confirmed_at, o.delivery_picked_up_at,
    oi.id, oi.item_name, oi.category_name, oi.quantity, oi.unit_price, oi.total_price
ORDER BY o.placed_at DESC;


-- 9. 创建按小时统计视图（支持分析高峰时段）
CREATE OR REPLACE VIEW v_hourly_sales AS
SELECT 
    o.store_code,
    o.restaurant_id,
    DATE(o.placed_at) as order_date,
    EXTRACT(HOUR FROM o.placed_at) as order_hour,
    COUNT(DISTINCT o.order_id) as order_count,
    ROUND(SUM(o.total_amount)::numeric, 2) as total_revenue,
    ROUND(AVG(o.total_amount)::numeric, 2) as avg_order_value
FROM orders o
WHERE o.status = 'delivered'
GROUP BY o.store_code, o.restaurant_id, DATE(o.placed_at), EXTRACT(HOUR FROM o.placed_at)
ORDER BY order_date DESC, order_hour;


COMMENT ON TABLE orders IS '订单主表，存储 Deliveroo 订单基本信息';
COMMENT ON TABLE order_items IS '订单菜品表，存储订单中的主菜品信息';
COMMENT ON TABLE order_item_modifiers IS '菜品添加项表，存储菜品的配料、加料等';
COMMENT ON VIEW v_item_sales_stats IS '主菜品销量统计视图（按店铺分组）';
COMMENT ON VIEW v_modifier_sales_stats IS '添加项销量统计视图（按店铺分组）';
COMMENT ON VIEW v_item_modifier_combination IS '主菜品与添加项组合统计视图（按店铺分组）';
COMMENT ON VIEW v_daily_item_sales IS '按日期统计菜品销量视图（按店铺分组）';
COMMENT ON VIEW v_order_details IS '订单详情视图，包含完整订单+菜品+添加项信息';
COMMENT ON VIEW v_hourly_sales IS '按小时统计销售视图，用于分析高峰时段';
