# 店铺评分数据飞书同步功能使用指南

## 功能概述

将数据库中的 `store_ratings` 表数据自动同步到飞书多维表格，支持：
- ✅ 自动增量同步（默认昨天的数据）
- ✅ 手动指定日期范围同步
- ✅ 自动检测重复记录（按"日期_店铺代码_平台"唯一键）
- ✅ 定时任务自动同步（每天凌晨1:10执行）

## 快速开始

### 1. 环境配置

确保 `.env` 文件中配置了飞书多维表格相关信息：

```bash
# 飞书应用配置（用于获取 access_token）
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxx

# 飞书评分数据表格配置
FEISHU_RATINGS_APP_TOKEN=Bd6rbEhmSa9CwBsLTjxc0PRPngg  # 多维表格 app_token
FEISHU_RATINGS_TABLE_ID=tblKAB54LB9zAHYP             # 数据表 table_id
```

### 2. 飞书表格字段配置

在飞书多维表格中创建以下字段：

| 字段名称 | 字段类型 | 说明 |
|---------|---------|------|
| 日期 | 日期 | 评分记录日期 |
| 店铺代码 | 文本 | 店铺英文代码（如 battersea_maocai） |
| 店铺名称 | 文本 | 店铺中文名称 |
| 平台 | 文本 | 平台名称（deliveroo） |
| 分店ID | 文本 | Deliveroo 的 branch_drn_id |
| 平均评分 | 数字 | 平均评分（1-5） |
| 评价数 | 数字 | 总评价数 |
| 五星 | 数字 | 五星评价数 |
| 四星 | 数字 | 四星评价数 |
| 三星 | 数字 | 三星评价数 |
| 二星 | 数字 | 二星评价数 |
| 一星 | 数字 | 一星评价数 |

## 使用方式

### 方式一：使用便捷脚本（推荐）

```bash
# 同步昨天的评分数据
./sync_store_ratings.sh

# 同步指定日期的评分数据
./sync_store_ratings.sh 2026-01-15

# 同步日期范围
./sync_store_ratings.sh --start-date 2026-01-10 --end-date 2026-01-15
```

### 方式二：直接调用 API

```bash
# 同步昨天的评分数据（默认）
curl -X POST http://localhost:8000/run/store-ratings/sync-feishu \
  -H "Content-Type: application/json" \
  -d '{}'

# 同步指定日期
curl -X POST http://localhost:8000/run/store-ratings/sync-feishu \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-01-15"}'

# 同步日期范围
curl -X POST http://localhost:8000/run/store-ratings/sync-feishu \
  -H "Content-Type: application/json" \
  -d '{"start_date":"2026-01-10","end_date":"2026-01-15"}'
```

## 定时任务

已在 `scheduler/scheduler.cron` 中配置：

```cron
# 每天凌晨1点执行店铺评分爬虫
0 1 * * * curl -X POST http://api:8000/run/store-ratings ...

# 每天凌晨1点10分同步评分数据到飞书（等待爬取完成）
10 1 * * * curl -X POST http://api:8000/run/store-ratings/sync-feishu ...
```

## 同步逻辑

1. **唯一键识别**：使用"日期_店铺代码_平台"作为唯一键
2. **增量更新**：
   - 如果飞书表格中已存在该记录 → 更新
   - 如果不存在 → 创建新记录
3. **默认行为**：API 不传参数时，默认同步昨天的数据

## 数据流程

```
店铺评分爬虫 (1:00 AM)
    ↓
store_ratings 表（数据库）
    ↓
飞书同步服务 (1:10 AM)
    ↓
飞书多维表格
```

## 日志查看

同步日志保存在 `api/logs/store_ratings_sync_*.log`：

```bash
# 查看最新日志
ls -lt api/logs/store_ratings_sync_*.log | head -1

# 查看日志内容
tail -100 api/logs/store_ratings_sync_20260118_010000.log
```

## 故障排查

### 1. 同步失败 - 缺少飞书配置

**错误信息：**
```
❌ 初始化失败: 缺少飞书配置：FEISHU_RATINGS_APP_TOKEN, FEISHU_RATINGS_TABLE_ID
```

**解决方案：**
检查 `.env` 文件是否包含：
- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_RATINGS_APP_TOKEN`
- `FEISHU_RATINGS_TABLE_ID`

### 2. 同步失败 - 权限问题

**错误信息：**
```
⚠️ 创建失败: {"code":99991668,"msg":"无权限访问该资源"}
```

**解决方案：**
1. 访问飞书开放平台：https://open.feishu.cn
2. 选择你的应用 → **权限管理**
3. 申请 `bitable:app` 权限（读写多维表格）
4. 等待审核通过后重试

### 3. 数据库无数据

**错误信息：**
```
⚠️ 未找到评分数据
```

**解决方案：**
1. 检查评分爬虫是否成功执行
2. 查看数据库中是否有数据：
```bash
./db_view_ratings.sh
```

### 4. 飞书字段不匹配

**错误信息：**
```
⚠️ 创建失败: {"code":1254021,"msg":"字段不存在"}
```

**解决方案：**
检查飞书表格字段名称是否与代码中完全一致（包括中文字符）。

## 性能优化

- ✅ **批量查询**：分页获取飞书表格已有记录（每页500条）
- ✅ **智能更新**：只更新有变化的记录
- ✅ **自动重试**：Token 过期时自动刷新
- ✅ **日志持久化**：所有操作日志保存到文件

## 相关文件

- **飞书同步服务**：[feishu_sync/store_ratings.py](feishu_sync/store_ratings.py)
- **API 路由**：[api/routers/store_ratings_sync.py](api/routers/store_ratings_sync.py)
- **定时任务**：[scheduler/scheduler.cron](scheduler/scheduler.cron)
- **手动脚本**：[sync_store_ratings.sh](sync_store_ratings.sh)
- **数据库表**：[db/migrations/20251230_add_store_ratings.sql](db/migrations/20251230_add_store_ratings.sql)

## 类似功能参考

- 每日销售汇总同步：[FEISHU_SYNC_TROUBLESHOOTING.md](FEISHU_SYNC_TROUBLESHOOTING.md)
- 每小时销售同步：[HOURLY_SALES_QUICKSTART.md](HOURLY_SALES_QUICKSTART.md)
