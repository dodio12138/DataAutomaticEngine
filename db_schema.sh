#!/bin/bash

# 查看数据库表结构
# 用法: ./db_schema.sh [表名]

show_help() {
    cat << 'EOF'
数据库表结构查看工具 (db_schema.sh)

功能说明：
  显示 PostgreSQL 数据库中表的结构信息，包括列名、数据类型、
  约束、索引等。支持查看单个表或所有表的列表。

用法：
  ./db_schema.sh [选项] [表名]

选项：
  --help, -h    显示此帮助信息

参数：
  表名          要查看结构的表名（可选）
                省略则显示所有表的列表

查询模式：
  - 无参数：显示数据库中所有表及其记录数
  - 指定表名：显示该表的详细结构（列名、类型、约束、索引）

示例：
  ./db_schema.sh              # 列出所有表及记录数
  ./db_schema.sh raw_orders   # 查看 raw_orders 表的详细结构
  ./db_schema.sh stores       # 查看 stores 表的结构
  ./db_schema.sh orders       # 查看 orders 表的结构

输出内容（无参数）：
  - 表名
  - 记录总数
  - 按表名排序

输出内容（指定表名）：
  - 列名（Column）
  - 数据类型（Type）
  - 是否可空（Nullable）
  - 默认值（Default）
  - 主键信息
  - 索引信息

核心表说明：
  stores       - 店铺配置表（平台、店铺代码、登录凭证）
  raw_orders   - 原始订单表（JSON 格式）
  orders       - 标准化订单表（ETL 处理后）
  order_items  - 订单菜品明细表（ETL 处理后）

注意事项：
  - 表名区分大小写
  - orders 和 order_items 表需要先运行 ETL 才会创建
  - raw_orders 表在数据库初始化时自动创建

依赖：
  - Docker
  - delivery_postgres 容器运行中
  - PostgreSQL 客户端（容器内置）

相关工具：
  - db_stats.sh - 查看数据统计信息
  - db_view_orders.sh - 查看订单数据
  - db/init.sql - 数据库初始化脚本

EOF
    exit 0
}

# 检查帮助选项
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
fi

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

TABLE="${1}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  📋 数据库表结构${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${YELLOW}❌ 数据库容器未运行${NC}"
    exit 1
fi

if [ -n "$TABLE" ]; then
    # 查看指定表的详细结构
    echo -e "${CYAN}📊 表: ${TABLE}${NC}"
    echo ""
    
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "\\d $TABLE"
    
    echo ""
    echo -e "${CYAN}📈 行数:${NC}"
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -t -c "SELECT COUNT(*) FROM $TABLE;"
    
else
    # 查看所有表
    echo -e "${CYAN}📚 所有表列表:${NC}"
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
        SELECT 
            schemaname as 架构,
            tablename as 表名,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as 大小
        FROM pg_tables
        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY tablename;
    "
    
    echo ""
    echo -e "${CYAN}📊 各表行数统计:${NC}"
    docker exec -it delivery_postgres psql -U delivery_user -d delivery_data -c "
        SELECT 
            'stores' as 表名,
            COUNT(*) as 行数
        FROM stores
        UNION ALL
        SELECT 'raw_orders', COUNT(*) FROM raw_orders;
    "
fi

echo ""
echo -e "${GREEN}✅ 查询完成${NC}"
echo ""
echo -e "${YELLOW}💡 提示: 使用 ./db_schema.sh orders 查看 orders 表详细结构${NC}"
