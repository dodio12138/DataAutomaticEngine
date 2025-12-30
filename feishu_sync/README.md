# 飞书多维表格同步服务

## 功能说明
从 `daily_sales_summary` 表自动同步数据到飞书多维表格，支持增量更新。

## 环境变量配置

需要在 `.env` 文件中添加以下配置：

```bash
# 飞书应用配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxx

# 飞书多维表格配置
FEISHU_BITABLE_APP_TOKEN=bascnxxxxxxxxxxxxx   # 多维表格的 app_token
FEISHU_BITABLE_TABLE_ID=tblxxxxxxxxxxxxx      # 数据表的 table_id
```

## 飞书多维表格字段配置

在飞书多维表格中需要创建以下字段：

| 字段名称 | 字段类型 | 说明 |
|---------|---------|------|
| 日期 | 日期 | 销售日期 |
| 店铺代码 | 文本 | 店铺英文代码 |
| 店铺名称 | 文本 | 店铺中文名称 |
| 平台 | 文本 | panda/deliveroo |
| 总销售额 | 数字 | gross_sales |
| 净销售额 | 数字 | net_sales |
| 订单数 | 数字 | order_count |
| 平均订单价值 | 数字 | avg_order_value |

## 使用方法

### 1. 通过 API 触发（推荐）

```bash
# 同步最近7天的所有数据
curl -X POST http://localhost:8000/run/feishu-sync

# 同步指定日期范围
curl -X POST http://localhost:8000/run/feishu-sync \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2025-12-20",
    "end_date": "2025-12-25"
  }'

# 同步特定店铺和平台
curl -X POST http://localhost:8000/run/feishu-sync \
  -H "Content-Type: application/json" \
  -d '{
    "store_code": "battersea_maocai",
    "platform": "panda",
    "start_date": "2025-12-24"
  }'
```

### 2. 直接运行容器

```bash
# 同步最近7天
docker run --rm --env-file .env \
  --network dataautomaticengine_default \
  dataautomaticengine-feishu-sync

# 同步指定日期范围
docker run --rm --env-file .env \
  --network dataautomaticengine_default \
  dataautomaticengine-feishu-sync \
  python main.py --start-date 2025-12-20 --end-date 2025-12-25

# 同步特定店铺
docker run --rm --env-file .env \
  --network dataautomaticengine_default \
  dataautomaticengine-feishu-sync \
  python main.py --store-code battersea_maocai --platform panda
```

### 3. 使用便捷脚本

```bash
# 同步昨天的数据
./sync_feishu_bitable.sh

# 同步指定日期
./sync_feishu_bitable.sh 2025-12-24

# 同步日期范围
./sync_feishu_bitable.sh 2025-12-20 2025-12-25
```

## 同步逻辑

1. **唯一性判断**：使用 `日期_店铺代码_平台` 作为唯一键
2. **增量更新**：如果记录已存在则更新，不存在则创建
3. **批量查询**：先获取飞书表格所有记录，构建映射关系
4. **逐条同步**：遍历数据库记录，判断创建或更新

## 定时任务配置

在 `scheduler/scheduler.cron` 中添加：

```cron
# 每天早上 7:00 同步昨天的数据到飞书
0 7 * * * curl -s -X POST http://api:8000/run/feishu-sync >> /var/log/cron-feishu-sync.log 2>&1
```

## 获取飞书多维表格 Token

### 1. 获取 app_token

在浏览器中打开你的多维表格，URL 格式为：
```
https://xxx.feishu.cn/base/bascnXXXXXXXXXXXXX?table=tblXXXXXXXXXXXXX
```

其中 `bascnXXXXXXXXXXXXX` 就是 `FEISHU_BITABLE_APP_TOKEN`

### 2. 获取 table_id

URL 中 `table=tblXXXXXXXXXXXXX` 就是 `FEISHU_BITABLE_TABLE_ID`

## 权限配置

需要在飞书开放平台为应用添加以下权限：

- `bitable:app` - 获取多维表格信息
- `bitable:app:readonly` - 查看多维表格
- `bitable:app:read_write` - 编辑多维表格

## 故障排查

### 1. 权限不足
```
❌ 创建失败: 99991668 - permission denied
```
**解决方案**：检查应用权限配置，确保已添加多维表格权限并重新授权

### 2. Token 错误
```
❌ 创建失败: 99991663 - invalid app_token
```
**解决方案**：检查 `FEISHU_BITABLE_APP_TOKEN` 是否正确

### 3. 字段不匹配
```
❌ 创建失败: field not exist
```
**解决方案**：确保飞书表格中的字段名称与代码中的字段名称完全一致

### 4. 数据库连接失败
```
❌ 同步失败: could not connect to server
```
**解决方案**：检查容器网络配置，确保容器加入 `dataautomaticengine_default` 网络

## 日志查看

```bash
# 查看 API 触发的同步日志
tail -f api/logs/feishu_sync_*.log

# 查看容器日志
docker logs <container_name>
```
