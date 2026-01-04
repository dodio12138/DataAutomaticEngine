#!/bin/bash

# 订单详情表一键部署脚本
# 用途：在新服务器上添加订单详情相关的数据库表和视图
# 
# 使用方法：
#   1. 确保 Docker 容器正在运行：docker ps | grep delivery_postgres
#   2. 运行此脚本：./setup_order_details_tables.sh
#
# 功能：
#   - 创建 orders（订单表）
#   - 创建 order_items（订单项表）
#   - 创建 order_item_modifiers（订单项添加项表）
#   - 创建 6 个统计视图（销售统计、热门菜品、组合分析等）
#   - 验证表结构和索引

set -e

echo ""
echo "========================================="
echo "🚀 订单详情表部署脚本"
echo "========================================="
echo ""

# 检查 PostgreSQL 容器是否运行
if ! docker ps | grep -q delivery_postgres; then
    echo "❌ PostgreSQL 容器未运行！"
    echo "请先启动容器: docker compose up -d"
    exit 1
fi

echo "✅ PostgreSQL 容器运行正常"
echo ""

# 创建 SQL 脚本
SQL_FILE="/tmp/order_details_schema.sql"

cat > "$SQL_FILE" << 'EOF'
-- =========================================
-- 订单详情表结构（Orders, Items, Modifiers）
-- =========================================

-- 1. 订单表（解析自 raw_orders.payload）
CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(128) PRIMARY KEY,           -- 订单唯一ID
    platform VARCHAR(32) NOT NULL,                -- 平台（deliveroo/hungrypanda）
    store_code VARCHAR(64) NOT NULL,              -- 店铺代码
    store_name VARCHAR(128),                      -- 店铺名称
    
    -- 订单状态
    status VARCHAR(32),                           -- 订单状态
    currency VARCHAR(8),                          -- 货币类型
    
    -- 金额信息
    subtotal_amount NUMERIC(10,2),                -- 小计金额
    discount_amount NUMERIC(10,2),                -- 折扣金额
    total_amount NUMERIC(10,2),                   -- 总金额
    tip_amount NUMERIC(10,2),                     -- 小费
    delivery_fee NUMERIC(10,2),                   -- 配送费
    service_fee NUMERIC(10,2),                    -- 服务费
    
    -- 时间信息
    placed_at TIMESTAMP,                          -- 下单时间
    accepted_at TIMESTAMP,                        -- 接单时间
    ready_at TIMESTAMP,                           -- 准备完成时间
    delivered_at TIMESTAMP,                       -- 送达时间
    
    -- 其他信息
    customer_note TEXT,                           -- 顾客备注
    restaurant_note TEXT,                         -- 餐厅备注
    delivery_type VARCHAR(32),                    -- 配送类型
    
    -- 原始数据
    raw_data JSONB,                               -- 完整的 JSON 数据（备份）
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 订单表索引
CREATE INDEX IF NOT EXISTS idx_orders_platform ON orders(platform);
CREATE INDEX IF NOT EXISTS idx_orders_store ON orders(store_code);
CREATE INDEX IF NOT EXISTS idx_orders_placed_at ON orders(placed_at);
CREATE INDEX IF NOT EXISTS idx_orders_store_date ON orders(store_code, DATE(placed_at));
CREATE INDEX IF NOT EXISTS idx_orders_platform_date ON orders(platform, DATE(placed_at));

-- 2. 订单项表（订单中的菜品）
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(128) NOT NULL,               -- 关联订单ID
    
    item_name VARCHAR(512) NOT NULL,              -- 菜品名称
    category_name VARCHAR(128),                   -- 分类名称
    
    quantity INTEGER NOT NULL,                    -- 数量
    unit_price NUMERIC(10,2),                     -- 单价
    total_price NUMERIC(10,2),                    -- 总价
    total_unit_price NUMERIC(10,2),               -- 单品总价（含添加项）
    
    item_data JSONB,                              -- 完整的菜品数据
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- 订单项索引
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_name ON order_items(item_name);
CREATE INDEX IF NOT EXISTS idx_order_items_category ON order_items(category_name);

-- 3. 订单项添加项表（菜品的配料、调料等）
CREATE TABLE IF NOT EXISTS order_item_modifiers (
    id SERIAL PRIMARY KEY,
    order_item_id INTEGER NOT NULL,               -- 关联订单项ID
    order_id VARCHAR(128) NOT NULL,               -- 关联订单ID（冗余，便于查询）
    
    modifier_name VARCHAR(256) NOT NULL,          -- 添加项名称
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    FOREIGN KEY (order_item_id) REFERENCES order_items(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- 添加项索引
CREATE INDEX IF NOT EXISTS idx_modifiers_order_item ON order_item_modifiers(order_item_id);
CREATE INDEX IF NOT EXISTS idx_modifiers_order ON order_item_modifiers(order_id);
CREATE INDEX IF NOT EXISTS idx_modifiers_name ON order_item_modifiers(modifier_name);

-- =========================================
-- 统计视图（6个分析视图）
-- =========================================

-- 视图 1: 菜品销售统计（按菜品汇总）
CREATE OR REPLACE VIEW v_item_sales_stats AS
SELECT 
    o.store_code,
    o.platform,
    oi.item_name,
    oi.category_name,
    COUNT(DISTINCT o.order_id) as order_count,           -- 订单数
    SUM(oi.quantity) as total_quantity,                  -- 总数量
    AVG(oi.unit_price) as avg_unit_price,               -- 平均单价
    SUM(oi.total_price) as total_revenue,               -- 总营收
    COUNT(DISTINCT DATE(o.placed_at)) as days_sold      -- 销售天数
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
GROUP BY o.store_code, o.platform, oi.item_name, oi.category_name
ORDER BY total_revenue DESC;

-- 视图 2: 添加项统计（按添加项汇总）
CREATE OR REPLACE VIEW v_modifier_sales_stats AS
SELECT 
    o.store_code,
    o.platform,
    oim.modifier_name,
    COUNT(*) as usage_count,                             -- 使用次数
    COUNT(DISTINCT o.order_id) as unique_orders,        -- 出现在多少个订单中
    COUNT(DISTINCT DATE(o.placed_at)) as days_used     -- 使用天数
FROM order_item_modifiers oim
JOIN orders o ON oim.order_id = o.order_id
GROUP BY o.store_code, o.platform, oim.modifier_name
ORDER BY usage_count DESC;

-- 视图 3: 菜品+添加项组合分析
CREATE OR REPLACE VIEW v_item_modifier_combination AS
SELECT 
    o.store_code,
    o.platform,
    oi.item_name,
    oim.modifier_name,
    COUNT(*) as combination_count,                       -- 组合次数
    COUNT(DISTINCT o.order_id) as unique_orders
FROM order_items oi
JOIN order_item_modifiers oim ON oi.id = oim.order_item_id
JOIN orders o ON oi.order_id = o.order_id
GROUP BY o.store_code, o.platform, oi.item_name, oim.modifier_name
ORDER BY combination_count DESC;

-- 视图 4: 每日菜品销售趋势
CREATE OR REPLACE VIEW v_daily_item_sales AS
SELECT 
    DATE(o.placed_at) as sale_date,
    o.store_code,
    o.platform,
    oi.item_name,
    SUM(oi.quantity) as daily_quantity,
    SUM(oi.total_price) as daily_revenue,
    COUNT(DISTINCT o.order_id) as daily_orders
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
GROUP BY DATE(o.placed_at), o.store_code, o.platform, oi.item_name
ORDER BY sale_date DESC, daily_revenue DESC;

-- 视图 5: 订单详情视图（完整订单信息）
CREATE OR REPLACE VIEW v_order_details AS
SELECT 
    o.order_id,
    o.platform,
    o.store_code,
    o.store_name,
    o.placed_at,
    o.total_amount,
    o.status,
    COUNT(DISTINCT oi.id) as item_count,
    SUM(oi.quantity) as total_items,
    ARRAY_AGG(DISTINCT oi.item_name ORDER BY oi.item_name) as items,
    COUNT(DISTINCT oim.id) as modifier_count,
    ARRAY_AGG(DISTINCT oim.modifier_name ORDER BY oim.modifier_name) as modifiers
FROM orders o
LEFT JOIN order_items oi ON o.order_id = oi.order_id
LEFT JOIN order_item_modifiers oim ON o.order_id = oim.order_id
GROUP BY o.order_id, o.platform, o.store_code, o.store_name, o.placed_at, o.total_amount, o.status
ORDER BY o.placed_at DESC;

-- 视图 6: 小时销售分布（分析高峰时段）
CREATE OR REPLACE VIEW v_hourly_sales AS
SELECT 
    o.store_code,
    o.platform,
    EXTRACT(HOUR FROM o.placed_at) as hour_of_day,
    COUNT(DISTINCT o.order_id) as order_count,
    SUM(o.total_amount) as total_sales,
    AVG(o.total_amount) as avg_order_value
FROM orders o
GROUP BY o.store_code, o.platform, EXTRACT(HOUR FROM o.placed_at)
ORDER BY o.store_code, hour_of_day;

-- =========================================
-- 完成提示
-- =========================================
\echo '✅ 订单详情表结构创建完成！'
\echo ''
\echo '📊 已创建：'
\echo '  • 3 张数据表：orders, order_items, order_item_modifiers'
\echo '  • 6 个统计视图：v_item_sales_stats, v_modifier_sales_stats 等'
\echo '  • 多个优化索引'
\echo ''

EOF

echo "📝 执行数据库脚本..."
echo ""

# 执行 SQL 脚本
docker exec -i delivery_postgres psql -U delivery_user -d delivery_data < "$SQL_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo "✅ 数据库表结构部署成功！"
    echo "========================================="
    echo ""
else
    echo ""
    echo "❌ 部署失败，请检查错误信息"
    echo ""
    rm "$SQL_FILE"
    exit 1
fi

# 清理临时文件
rm "$SQL_FILE"

# 验证表是否创建成功
echo "🔍 验证表结构..."
echo ""

docker exec delivery_postgres psql -U delivery_user -d delivery_data << 'EOSQL'
-- 检查表
SELECT 
    tablename as "表名",
    schemaname as "Schema"
FROM pg_tables 
WHERE tablename IN ('orders', 'order_items', 'order_item_modifiers')
ORDER BY tablename;

\echo ''
\echo '📊 检查视图:'
\echo ''

-- 检查视图
SELECT 
    viewname as "视图名",
    schemaname as "Schema"
FROM pg_views 
WHERE viewname LIKE 'v_%'
ORDER BY viewname;

\echo ''
\echo '🔑 检查索引（orders表）:'
\echo ''

-- 检查索引
SELECT 
    indexname as "索引名",
    tablename as "表名"
FROM pg_indexes 
WHERE tablename IN ('orders', 'order_items', 'order_item_modifiers')
ORDER BY tablename, indexname;

EOSQL

echo ""
echo "========================================="
echo "✅ 部署完成！"
echo "========================================="
echo ""

echo "💡 后续步骤："
echo "  1. 导入订单详情数据:"
echo "     ./import_orders.sh                    # 全量导入"
echo "     ./import_orders.sh --days 7           # 导入最近7天"
echo ""
echo "  2. 查看表数据:"
echo "     ./db_shell.sh"
echo "     SELECT COUNT(*) FROM orders;"
echo "     SELECT COUNT(*) FROM order_items;"
echo ""
echo "  3. 测试统计查询:"
echo "     curl http://localhost:8000/stats/items/top?limit=10"
echo "     curl http://localhost:8000/stats/modifiers/top?limit=10"
echo ""
echo "  4. 在飞书查询热门菜品:"
echo "     Top 10 7                              # 最近7天TOP 10"
echo "     Top 5 7 Battersea deliveroo main      # 指定店铺、平台、类型"
echo ""
