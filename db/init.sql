-- 店铺表：用于管理店铺元数据与平台映射
CREATE TABLE IF NOT EXISTS stores (
    id SERIAL PRIMARY KEY,
    code VARCHAR(64) UNIQUE NOT NULL,
    name_cn VARCHAR(128) NOT NULL,
    platform VARCHAR(32) NOT NULL,
    platform_store_id VARCHAR(64) NOT NULL,
    login_user VARCHAR(64),
    login_password VARCHAR(128),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(platform, platform_store_id)
);

-- 原始订单表：增加店铺标识字段，便于按店铺聚合
CREATE TABLE IF NOT EXISTS raw_orders (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(32) NOT NULL,
    store_code VARCHAR(64),
    store_name VARCHAR(128),
    order_id VARCHAR(128) NOT NULL,
    order_date TIMESTAMP,
    estimated_revenue NUMERIC(10,2),
    product_amount NUMERIC(10,2),
    discount_amount NUMERIC(10,2),
    print_amount NUMERIC(10,2),
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 可按需添加索引
CREATE INDEX IF NOT EXISTS idx_raw_orders_platform_order ON raw_orders(platform, order_id);
CREATE INDEX IF NOT EXISTS idx_raw_orders_store_time ON raw_orders(store_code, created_at);
CREATE INDEX IF NOT EXISTS idx_raw_orders_order_date ON raw_orders(order_date);

-- 每日销售汇总表：用于存储每个店铺每天的销售汇总数据
CREATE TABLE IF NOT EXISTS daily_sales_summary (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    store_code VARCHAR(64) NOT NULL,
    store_name VARCHAR(128),
    platform VARCHAR(32) NOT NULL,
    gross_sales NUMERIC(10,2),
    net_sales NUMERIC(10,2),
    order_count INTEGER,
    avg_order_value NUMERIC(10,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(date, store_code, platform)
);

-- 每日汇总索引
CREATE INDEX IF NOT EXISTS idx_daily_sales_date ON daily_sales_summary(date);
CREATE INDEX IF NOT EXISTS idx_daily_sales_store ON daily_sales_summary(store_code);
CREATE INDEX IF NOT EXISTS idx_daily_sales_platform ON daily_sales_summary(platform);
