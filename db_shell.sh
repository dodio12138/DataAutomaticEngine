#!/bin/bash

# 直接连接到数据库的交互式命令行
# 用法: ./db_shell.sh

show_help() {
    cat << 'EOF'
数据库交互式命令行工具 (db_shell.sh)

功能说明：
  启动 PostgreSQL 交互式命令行（psql），直接连接到
  delivery_data 数据库，支持执行任意 SQL 查询和管理命令。

用法：
  ./db_shell.sh [选项]

选项：
  --help, -h    显示此帮助信息

执行模式：
  交互式 psql 会话，可执行任意 SQL 语句和 psql 元命令。

常用 psql 元命令：
  \dt              列出所有表
  \d [表名]        查看表结构
  \d+ [表名]       查看表结构（详细）
  \l               列出所有数据库
  \du              列出所有用户
  \q               退出 psql
  \?               显示所有 psql 命令帮助
  \h [SQL命令]     显示 SQL 命令帮助

常用 SQL 查询示例：
  SELECT * FROM raw_orders LIMIT 10;
  SELECT COUNT(*) FROM raw_orders WHERE platform='hungrypanda';
  SELECT DISTINCT store_code FROM raw_orders;
  SELECT DATE(created_at), COUNT(*) FROM raw_orders GROUP BY DATE(created_at);

示例：
  ./db_shell.sh         # 启动交互式命令行
  # 然后在 psql 中执行：
  # delivery_data=# SELECT COUNT(*) FROM raw_orders;
  # delivery_data=# \d raw_orders
  # delivery_data=# \q

高级用法：
  执行单条 SQL（非交互式）：
  docker exec -it delivery_postgres psql -U delivery_user -d delivery_data \
    -c "SELECT COUNT(*) FROM raw_orders;"

注意事项：
  - 输入 \q 或按 Ctrl+D 退出
  - 所有 SQL 语句需以分号结尾
  - psql 命令（\dt 等）不需要分号
  - 可以使用方向键查看历史命令
  - 支持 Tab 键自动补全表名和列名

数据库信息：
  数据库名：delivery_data
  用户名：delivery_user
  字符集：UTF-8
  时区：UTC

依赖：
  - Docker
  - delivery_postgres 容器运行中
  - psql 客户端（容器内置）

相关工具：
  - db_schema.sh - 快速查看表结构
  - db_stats.sh - 查看数据统计
  - db_view_orders.sh - 查看订单数据
  - db_daily_summary.sh - 查看日期汇总

PostgreSQL 文档：
  https://www.postgresql.org/docs/current/app-psql.html

EOF
    exit 0
}

# 检查帮助选项
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
fi

# 颜色定义
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  🔧 PostgreSQL 交互式命令行${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查数据库容器
if ! docker ps | grep -q delivery_postgres; then
    echo -e "${YELLOW}❌ 数据库容器未运行${NC}"
    exit 1
fi

echo -e "${GREEN}常用命令:${NC}"
echo -e "  ${YELLOW}\\dt${NC}          - 查看所有表"
echo -e "  ${YELLOW}\\d orders${NC}    - 查看 orders 表结构"
echo -e "  ${YELLOW}\\q${NC}           - 退出"
echo ""
echo -e "${GREEN}已连接到数据库: delivery_data${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 进入交互式命令行
docker exec -it delivery_postgres psql -U delivery_user -d delivery_data
