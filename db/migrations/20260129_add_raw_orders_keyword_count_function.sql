-- 用于统计 raw_orders 在指定日期范围内的关键词数量（可选平台过滤）
CREATE OR REPLACE FUNCTION raw_orders_keyword_count(
    p_keyword TEXT,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL,
    p_platform TEXT DEFAULT NULL,
    p_store_code TEXT DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE SQL
AS $$
    SELECT COUNT(*)
    FROM raw_orders
    WHERE (
        COALESCE(order_date::date, created_at::date) BETWEEN
            COALESCE(p_start_date, date_trunc('month', CURRENT_DATE)::date)
            AND COALESCE(
                p_end_date,
                (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month - 1 day')::date
            )
    )
    AND (
        p_platform IS NULL OR platform = p_platform
    )
    AND (
        p_store_code IS NULL OR store_code = p_store_code
    )
    AND payload::text ILIKE ('%' || p_keyword || '%');
$$;

-- 复购率统计：可按平台/店铺/日期范围过滤（日期默认本月）
CREATE OR REPLACE FUNCTION raw_orders_repeat_rate(
    p_platform TEXT,
    p_store_code TEXT DEFAULT NULL,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE(
    platform TEXT,
    store_code TEXT,
    repeat_users BIGINT,
    total_users BIGINT,
    repeat_rate NUMERIC
)
LANGUAGE SQL
AS $$
    WITH base_orders AS (
        SELECT
            platform,
            store_code,
            COALESCE(order_date::date, created_at::date) AS order_day,
            CASE
                WHEN platform = 'panda' THEN payload->'data'->'merchantOrderAddressResVO'->>'consigneeTelMask'
                WHEN platform = 'deliveroo' THEN payload->'customer'->>'id'
                ELSE NULL
            END AS user_id
        FROM raw_orders
        WHERE platform = p_platform
          AND (p_store_code IS NULL OR store_code = p_store_code)
    ),
    filtered_orders AS (
        SELECT *
        FROM base_orders
        WHERE order_day BETWEEN
            COALESCE(p_start_date, date_trunc('month', CURRENT_DATE)::date)
            AND COALESCE(
                p_end_date,
                (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month - 1 day')::date
            )
          AND user_id IS NOT NULL
    ),
    user_counts AS (
        SELECT platform, store_code, user_id, COUNT(*) AS orders
        FROM filtered_orders
        GROUP BY platform, store_code, user_id
    )
    SELECT
        p_platform AS platform,
        p_store_code AS store_code,
        COUNT(*) FILTER (WHERE orders >= 2) AS repeat_users,
        COUNT(*) AS total_users,
        ROUND(COUNT(*) FILTER (WHERE orders >= 2)::numeric / NULLIF(COUNT(*), 0), 4) AS repeat_rate
    FROM user_counts;
$$;

-- 统计两个店铺在各平台的交叉顾客数（日期默认本月）
CREATE OR REPLACE FUNCTION raw_orders_cross_store_customers(
    p_store_code_a TEXT,
    p_store_code_b TEXT,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
)
RETURNS TABLE(
    platform TEXT,
    shared_customers BIGINT
)
LANGUAGE SQL
AS $$
    WITH base_orders AS (
        SELECT
            platform,
            store_code,
            COALESCE(order_date::date, created_at::date) AS order_day,
            CASE
                WHEN platform = 'panda' THEN payload->'data'->'merchantOrderAddressResVO'->>'consigneeTelMask'
                WHEN platform = 'deliveroo' THEN payload->'customer'->>'id'
                ELSE NULL
            END AS user_id
        FROM raw_orders
        WHERE store_code IN (p_store_code_a, p_store_code_b)
    ),
    filtered_orders AS (
        SELECT *
        FROM base_orders
        WHERE order_day BETWEEN
            COALESCE(p_start_date, date_trunc('month', CURRENT_DATE)::date)
            AND COALESCE(
                p_end_date,
                (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month - 1 day')::date
            )
          AND user_id IS NOT NULL
    ),
    users_by_store AS (
        SELECT DISTINCT platform, store_code, user_id
        FROM filtered_orders
    ),
    cross_users AS (
        SELECT a.platform, a.user_id
        FROM users_by_store a
        JOIN users_by_store b
          ON a.platform = b.platform
         AND a.user_id = b.user_id
        WHERE a.store_code = p_store_code_a
          AND b.store_code = p_store_code_b
    )
    SELECT platform, COUNT(DISTINCT user_id) AS shared_customers
    FROM cross_users
    GROUP BY platform
    ORDER BY platform;
$$;