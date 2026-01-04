#!/bin/bash

# 订单详情表字段补丁脚本
# 用途：添加导入脚本所需的缺失字段
# 
# 使用方法：
#   ./patch_order_details_fields.sh

set -e

echo ""
echo "========================================="
echo "🔧 订单详情表字段补丁"
echo "========================================="
echo ""

# 检查 PostgreSQL 容器是否运行
if ! docker ps | grep -q delivery_postgres; then
    echo "❌ PostgreSQL 容器未运行！"
    exit 1
fi

echo "✅ PostgreSQL 容器运行正常"
echo ""

echo "📝 添加缺失字段..."
echo ""

# 执行补丁 SQL
docker exec delivery_postgres psql -U delivery_user -d delivery_data << 'EOSQL'

-- =========================================
-- 添加 Deliveroo 特定字段到 orders 表
-- =========================================

-- 添加 short_drn 字段（如果不存在）
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='short_drn'
    ) THEN
        ALTER TABLE orders ADD COLUMN short_drn VARCHAR(32);
        \echo '✅ 已添加字段: short_drn';
    ELSE
        \echo '⏭️  字段已存在: short_drn';
    END IF;
END $$;

-- 添加 order_number 字段
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='order_number'
    ) THEN
        ALTER TABLE orders ADD COLUMN order_number VARCHAR(64);
        \echo '✅ 已添加字段: order_number';
    ELSE
        \echo '⏭️  字段已存在: order_number';
    END IF;
END $$;

-- 添加 restaurant_id 字段
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='restaurant_id'
    ) THEN
        ALTER TABLE orders ADD COLUMN restaurant_id VARCHAR(64);
        \echo '✅ 已添加字段: restaurant_id';
    ELSE
        \echo '⏭️  字段已存在: restaurant_id';
    END IF;
END $$;

-- 添加 paid_in_cash 字段
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='paid_in_cash'
    ) THEN
        ALTER TABLE orders ADD COLUMN paid_in_cash NUMERIC(10,2);
        \echo '✅ 已添加字段: paid_in_cash';
    ELSE
        \echo '⏭️  字段已存在: paid_in_cash';
    END IF;
END $$;

-- 添加 currency_code 字段
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='currency_code'
    ) THEN
        ALTER TABLE orders ADD COLUMN currency_code VARCHAR(8) DEFAULT 'GBP';
        \echo '✅ 已添加字段: currency_code';
    ELSE
        \echo '⏭️  字段已存在: currency_code';
    END IF;
END $$;

-- 添加 rejection_reason 字段
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='rejection_reason'
    ) THEN
        ALTER TABLE orders ADD COLUMN rejection_reason TEXT;
        \echo '✅ 已添加字段: rejection_reason';
    ELSE
        \echo '⏭️  字段已存在: rejection_reason';
    END IF;
END $$;

-- 添加 confirmed_at 字段
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='confirmed_at'
    ) THEN
        ALTER TABLE orders ADD COLUMN confirmed_at TIMESTAMP;
        \echo '✅ 已添加字段: confirmed_at';
    ELSE
        \echo '⏭️  字段已存在: confirmed_at';
    END IF;
END $$;

-- 添加 prepare_for 字段
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='prepare_for'
    ) THEN
        ALTER TABLE orders ADD COLUMN prepare_for TIMESTAMP;
        \echo '✅ 已添加字段: prepare_for';
    ELSE
        \echo '⏭️  字段已存在: prepare_for';
    END IF;
END $$;

-- 添加 delivery_picked_up_at 字段
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='delivery_picked_up_at'
    ) THEN
        ALTER TABLE orders ADD COLUMN delivery_picked_up_at TIMESTAMP;
        \echo '✅ 已添加字段: delivery_picked_up_at';
    ELSE
        \echo '⏭️  字段已存在: delivery_picked_up_at';
    END IF;
END $$;

-- 添加 customer_id 字段
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='customer_id'
    ) THEN
        ALTER TABLE orders ADD COLUMN customer_id VARCHAR(64);
        \echo '✅ 已添加字段: customer_id';
    ELSE
        \echo '⏭️  字段已存在: customer_id';
    END IF;
END $$;

-- 修改主键约束（如果需要）
-- 原来的主键只有 order_id，需要改为 (order_id, platform)
DO $$ 
BEGIN
    -- 检查是否需要添加 platform 字段（如果表是新建的可能没有）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='orders' AND column_name='platform'
    ) THEN
        ALTER TABLE orders ADD COLUMN platform VARCHAR(32) DEFAULT 'deliveroo';
        \echo '✅ 已添加字段: platform';
    END IF;
    
    -- 如果 platform 字段存在但没有默认值，设置现有记录的默认值
    UPDATE orders SET platform = 'deliveroo' WHERE platform IS NULL;
    ALTER TABLE orders ALTER COLUMN platform SET NOT NULL;
    
    -- 删除旧主键（如果存在）
    IF EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'orders_pkey' AND contype = 'p'
    ) THEN
        BEGIN
            -- 尝试删除旧主键
            ALTER TABLE orders DROP CONSTRAINT orders_pkey;
            \echo '✅ 已删除旧主键: orders_pkey';
        EXCEPTION WHEN OTHERS THEN
            \echo '⏭️  主键约束处理跳过';
        END;
    END IF;
    
    -- 创建新的复合主键（如果不存在）
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'orders_pkey' AND contype = 'p'
    ) THEN
        BEGIN
            ALTER TABLE orders ADD PRIMARY KEY (order_id, platform);
            \echo '✅ 已创建复合主键: (order_id, platform)';
        EXCEPTION WHEN OTHERS THEN
            \echo '⚠️  主键创建失败，可能已存在';
        END;
    END IF;
END $$;

-- 添加索引
CREATE INDEX IF NOT EXISTS idx_orders_short_drn ON orders(short_drn);
CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_restaurant_id ON orders(restaurant_id);

\echo ''
\echo '========================================='
\echo '✅ 字段补丁完成！'
\echo '========================================='

EOSQL

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 字段补丁应用成功！"
    echo ""
    echo "📊 验证表结构..."
    echo ""
    
    # 显示 orders 表的所有字段
    docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "
    SELECT 
        column_name as \"字段名\",
        data_type as \"数据类型\",
        character_maximum_length as \"长度\",
        is_nullable as \"可为空\"
    FROM information_schema.columns
    WHERE table_name = 'orders'
    ORDER BY ordinal_position;
    "
    
    echo ""
    echo "✅ 所有补丁已应用完成！"
    echo ""
    echo "💡 现在可以运行导入脚本："
    echo "   ./import_orders.sh"
    echo "   ./import_orders.sh --days 7"
    echo ""
else
    echo ""
    echo "❌ 补丁应用失败"
    exit 1
fi
