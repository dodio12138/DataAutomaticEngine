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
    payload JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 可按需添加索引
CREATE INDEX IF NOT EXISTS idx_raw_orders_platform_order ON raw_orders(platform, order_id);
CREATE INDEX IF NOT EXISTS idx_raw_orders_store_time ON raw_orders(store_code, created_at);
