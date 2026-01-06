-- 创建每小时销售数据表
-- 用于分析店铺每天每小时的订单量和销售额

CREATE TABLE IF NOT EXISTS hourly_sales (
    id SERIAL PRIMARY KEY,
    date_time TIMESTAMP NOT NULL,           -- 日期时间（如 2026-01-06 14:00:00）
    date DATE NOT NULL,                     -- 日期（冗余但便于查询）
    hour INTEGER NOT NULL,                  -- 小时（0-23）
    store_code VARCHAR(64) NOT NULL,        -- 店铺代码
    store_name VARCHAR(128),                -- 店铺名称
    platform VARCHAR(32) NOT NULL,          -- 平台（deliveroo/hungrypanda）
    order_count INTEGER DEFAULT 0,          -- 订单量
    total_sales DECIMAL(10,2) DEFAULT 0,    -- 销售额
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一约束：同一店铺同一平台同一小时只有一条记录
    UNIQUE(date_time, store_code, platform)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_hourly_sales_date ON hourly_sales(date);
CREATE INDEX IF NOT EXISTS idx_hourly_sales_datetime ON hourly_sales(date_time);
CREATE INDEX IF NOT EXISTS idx_hourly_sales_store ON hourly_sales(store_code);
CREATE INDEX IF NOT EXISTS idx_hourly_sales_platform ON hourly_sales(platform);
CREATE INDEX IF NOT EXISTS idx_hourly_sales_hour ON hourly_sales(hour);
CREATE INDEX IF NOT EXISTS idx_hourly_sales_date_store ON hourly_sales(date, store_code);

-- 添加注释
COMMENT ON TABLE hourly_sales IS '每小时销售数据表';
COMMENT ON COLUMN hourly_sales.date_time IS '日期时间（整点时间）';
COMMENT ON COLUMN hourly_sales.date IS '日期（冗余字段，便于按日查询）';
COMMENT ON COLUMN hourly_sales.hour IS '小时（0-23）';
COMMENT ON COLUMN hourly_sales.order_count IS '该小时的订单数量';
COMMENT ON COLUMN hourly_sales.total_sales IS '该小时的总销售额';

SELECT '✅ hourly_sales 表创建成功' AS status;
