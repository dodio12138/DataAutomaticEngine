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
    WITH base_orders AS (
        SELECT platform, payload
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
    panda_orders AS (
        SELECT payload
        FROM base_orders
        WHERE platform = 'panda'
    ),
    panda_item_objects AS (
        SELECT jsonb_path_query(payload, '$.data.details[*]') AS item
        FROM panda_orders
        WHERE payload ? 'data' AND (payload->'data') ? 'details'
        UNION ALL
        SELECT jsonb_path_query(
            payload,
            '$.** ? (@.productCount != null || @.quantity != null || @.qty != null)'
        ) AS item
        FROM panda_orders
        WHERE NOT (payload ? 'data' AND (payload->'data') ? 'details')
    ),
    panda_item_fields AS (
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
        FROM panda_item_objects
    ),
    panda_matched AS (
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
        FROM panda_item_fields
    ),
    panda_total AS (
        SELECT COALESCE(SUM(product_count * name_multiplier), 0)::bigint AS cnt
        FROM panda_matched
        WHERE name_multiplier > 0
    ),
    other_total AS (
        SELECT COUNT(*)::bigint AS cnt
        FROM base_orders
        WHERE platform <> 'panda'
    )
    SELECT CASE
        WHEN p_platform = 'panda' THEN (SELECT cnt FROM panda_total)
        WHEN p_platform IS NULL THEN (SELECT cnt FROM panda_total) + (SELECT cnt FROM other_total)
        ELSE (SELECT cnt FROM other_total)
    END;
$$;
