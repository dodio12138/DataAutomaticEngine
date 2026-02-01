-- 修正关键词统计：避免 panda payload 多路径重复计数（触发同步更新）
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
    WITH filtered_orders AS (
        SELECT payload
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
        AND payload::text ILIKE ('%' || p_keyword || '%')
    ),
    item_objects AS (
        SELECT jsonb_path_query(payload, '$.data.details[*]') AS item
        FROM filtered_orders
        WHERE payload ? 'data' AND (payload->'data') ? 'details'
        UNION ALL
        SELECT jsonb_path_query(
            payload,
            '$.** ? (@.productCount != null || @.quantity != null || @.qty != null)'
        ) AS item
        FROM filtered_orders
        WHERE NOT (payload ? 'data' AND (payload->'data') ? 'details')
    ),
    item_fields AS (
        SELECT
            COALESCE(
                item->>'productName',
                item->>'itemName',
                item->>'name',
                item->>'title'
            ) AS item_name,
            COALESCE(
                NULLIF(item->>'productCount', '')::int,
                NULLIF(item->>'quantity', '')::int,
                NULLIF(item->>'qty', '')::int,
                1
            ) AS product_count
        FROM item_objects
    ),
    matched AS (
        SELECT
            item_name,
            product_count,
            CASE
                WHEN item_name IS NULL THEN 0
                WHEN strpos(lower(item_name), lower(p_keyword)) = 0 THEN 0
                ELSE COALESCE(
                    NULLIF(
                        substring(
                            lower(
                                substring(
                                    item_name FROM (strpos(lower(item_name), lower(p_keyword)) + length(p_keyword))
                                )
                            ) FROM 'x([0-9]+)'
                        ),
                        ''
                    )::int,
                    1
                )
            END AS name_multiplier
        FROM item_fields
    )
    SELECT COALESCE(SUM(product_count * name_multiplier), 0)::bigint
    FROM matched
    WHERE name_multiplier > 0;
$$;
