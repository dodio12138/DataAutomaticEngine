-- 用于统计 raw_orders 在指定日期范围内的关键词数量（可选平台过滤）
CREATE OR REPLACE FUNCTION raw_orders_keyword_count(
    p_keyword TEXT,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL,
    p_platform TEXT DEFAULT NULL
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
    AND payload::text ILIKE ('%' || p_keyword || '%');
$$;