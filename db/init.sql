CREATE TABLE IF NOT EXISTS raw_orders (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(32),
    order_id VARCHAR(128),
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
