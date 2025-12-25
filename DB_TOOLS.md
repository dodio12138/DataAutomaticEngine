# 数据库查询工具使用指南

快速查看订单数据的 Shell 脚本工具集

---

## 📋 工具列表

### 1. `db_stats.sh` - 数据库统计概览
**用途：** 查看整体数据统计信息

```bash
./db_stats.sh
```

**显示内容：**
- ✅ 订单总数
- ✅ 原始订单数量
- ✅ 各店铺订单统计（订单数、总营收、平均客单价）
- ✅ 最近7天订单趋势
- ✅ 订单状态分布
- ✅ 数据时间范围

---

### 2. `db_view_orders.sh` - 查看订单详情
**用途：** 查看具体订单数据

```bash
# 查看最近10条订单
./db_view_orders.sh

# 查看指定日期所有订单
./db_view_orders.sh 2025-12-24

# 查看指定日期指定店铺订单
./db_view_orders.sh 2025-12-24 battersea_maocai

# 查看指定日期并限制条数
./db_view_orders.sh 2025-12-24 battersea_maocai 20
```

**显示字段：**
- 订单ID
- 店铺名称
- 订单时间
- 订单状态
- 营收金额
- 商品金额
- 顾客姓名

---

### 3. `db_daily_summary.sh` - 每日汇总
**用途：** 查看某一天的详细汇总数据

```bash
# 查看昨天汇总
./db_daily_summary.sh

# 查看指定日期汇总
./db_daily_summary.sh 2025-12-24
```

**显示内容：**
- ✅ 当天总体数据（总订单数、总营收、平均客单价、商品金额、优惠金额）
- ✅ 各店铺数据明细
- ✅ 订单状态分布
- ✅ 订单时段分布（按小时统计）

---

### 4. `db_view_raw.sh` - 查看原始订单JSON
**用途：** 查看未经处理的原始订单数据

```bash
# 查看最近5条原始订单
./db_view_raw.sh

# 查看指定平台最近10条
./db_view_raw.sh hungrypanda

# 查看指定平台和店铺的原始JSON（含完整内容）
./db_view_raw.sh hungrypanda battersea_maocai 3
```

**使用场景：**
- 调试爬虫数据
- 检查ETL处理前的原始数据
- 排查数据解析问题

---

### 5. `db_schema.sh` - 查看表结构
**用途：** 查看数据库表结构和统计

```bash
# 查看所有表列表和行数
./db_schema.sh

# 查看指定表的详细结构
./db_schema.sh orders
./db_schema.sh stores
./db_schema.sh raw_orders
./db_schema.sh order_items
```

**显示内容：**
- 表结构（字段名、类型、约束）
- 表大小
- 行数统计

---

### 6. `db_shell.sh` - 交互式数据库命令行
**用途：** 直接连接到 PostgreSQL 进行自定义查询

```bash
./db_shell.sh
```

**常用命令：**
```sql
-- 查看所有表
\dt

-- 查看表结构
\d orders

-- 自定义查询
SELECT * FROM orders WHERE order_date > '2025-12-20' LIMIT 10;

-- 退出
\q
```

---

## 📊 使用示例

### 场景1：快速了解整体数据情况
```bash
./db_stats.sh
```

### 场景2：查看昨天各店铺业绩
```bash
./db_daily_summary.sh
```

### 场景3：查找某个订单
```bash
# 先查看某天所有订单
./db_view_orders.sh 2025-12-24

# 或查看某店铺某天订单
./db_view_orders.sh 2025-12-24 battersea_maocai
```

### 场景4：调试爬虫问题
```bash
# 查看原始数据格式
./db_view_raw.sh hungrypanda battersea_maocai 1
```

### 场景5：复杂查询
```bash
# 进入交互式命令行
./db_shell.sh

# 执行自定义SQL
SELECT 
    DATE(order_date) as date,
    COUNT(*) as orders,
    SUM(estimated_revenue) as revenue
FROM orders 
WHERE order_date >= '2025-12-01'
GROUP BY DATE(order_date)
ORDER BY date DESC;
```

---

## 💡 提示

1. **所有脚本需要数据库容器运行** 
   - 确保容器已启动：`docker ps | grep delivery_postgres`
   - 如未启动：`docker compose up -d db`

2. **日期格式统一使用 YYYY-MM-DD**
   ```bash
   ./db_view_orders.sh 2025-12-24  # ✅ 正确
   ./db_view_orders.sh 12-24       # ❌ 错误
   ```

3. **店铺代码参考**
   - `battersea_maocai` - Battersea 冒菜店
   - `piccadilly_maocai` - Piccadilly 冒菜店
   - `towerbridge_maocai` - Tower Bridge 冒菜店

4. **查看帮助**
   ```bash
   # 大多数脚本不带参数运行会显示用法
   ./db_view_orders.sh
   ```

---

## 🔧 故障排查

### 问题：提示数据库容器未运行
```bash
# 检查容器状态
docker compose ps

# 启动数据库
docker compose up -d db
```

### 问题：权限不足
```bash
# 添加执行权限
chmod +x db_*.sh
```

### 问题：查询结果为空
- 检查日期是否有数据
- 检查店铺代码是否正确
- 使用 `./db_stats.sh` 查看数据时间范围

---

## 📚 相关文档

- [部署文档](DEPLOYMENT.md)
- [API 文档](http://localhost:8000/docs)
- [数据库初始化脚本](db/init.sql)

---

**最后更新：** 2025-12-25
