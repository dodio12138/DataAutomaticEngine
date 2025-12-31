-- 创建店铺评分表
-- 存储 Deliveroo 店铺评分数据

CREATE TABLE IF NOT EXISTS store_ratings (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    store_code VARCHAR(100) NOT NULL,
    store_name VARCHAR(255),
    platform VARCHAR(50) NOT NULL DEFAULT 'deliveroo',
    branch_drn_id VARCHAR(255),
    
    -- 评分数据
    average_rating DECIMAL(4,2),
    rating_count INTEGER DEFAULT 0,
    
    -- 星级细则
    five_star_count INTEGER DEFAULT 0,
    four_star_count INTEGER DEFAULT 0,
    three_star_count INTEGER DEFAULT 0,
    two_star_count INTEGER DEFAULT 0,
    one_star_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一约束：同一店铺同一天只有一条记录
    UNIQUE(date, store_code, platform)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_store_ratings_date ON store_ratings(date);
CREATE INDEX IF NOT EXISTS idx_store_ratings_store ON store_ratings(store_code);
CREATE INDEX IF NOT EXISTS idx_store_ratings_platform ON store_ratings(platform);
CREATE INDEX IF NOT EXISTS idx_store_ratings_date_platform ON store_ratings(date, platform);

-- 添加注释
COMMENT ON TABLE store_ratings IS '店铺评分数据表';
COMMENT ON COLUMN store_ratings.average_rating IS '平均评分（1-5）';
COMMENT ON COLUMN store_ratings.rating_count IS '总评价数';
COMMENT ON COLUMN store_ratings.branch_drn_id IS 'Deliveroo 店铺唯一标识';

SELECT 'store_ratings 表创建成功' AS status;
