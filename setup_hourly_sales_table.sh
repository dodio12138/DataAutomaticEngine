#!/bin/bash
# 一键创建 hourly_sales 表

echo "🔧 创建 hourly_sales 表..."
echo "=============================="
echo ""

# 执行迁移脚本
docker exec delivery_postgres psql -U delivery_user -d delivery_data -f /docker-entrypoint-initdb.d/../../../db/migrations/20260106_add_hourly_sales_table.sql

# 或者直接通过挂载的路径
docker exec delivery_postgres bash -c "psql -U delivery_user -d delivery_data < /docker-entrypoint-initdb.d/20260106_add_hourly_sales_table.sql" 2>/dev/null

# 检查表是否创建成功
echo ""
echo "🔍 验证表结构..."
docker exec delivery_postgres psql -U delivery_user -d delivery_data -c "\d hourly_sales"

echo ""
echo "✅ 表创建完成！"
