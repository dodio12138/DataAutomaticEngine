# 飞书多维表格同步服务部署指南

## 📋 概述

本指南帮助您快速部署和使用飞书多维表格同步服务，实现 `daily_sales_summary` 数据自动同步到飞书多维表格。

## 🎯 功能特点

- ✅ 自动同步每日销售汇总数据到飞书多维表格
- ✅ 支持增量更新（已存在记录则更新，不存在则创建）
- ✅ 支持按日期范围、店铺、平台过滤同步
- ✅ 通过 API 或命令行灵活触发
- ✅ 定时任务自动执行
- ✅ 完整的日志记录和错误处理

## 🚀 快速开始

### 步骤 1: 配置飞书应用

#### 1.1 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 点击"创建企业自建应用"
3. 记录 **App ID** 和 **App Secret**

#### 1.2 配置应用权限

在应用管理页面添加以下权限：

| 权限名称 | 权限说明 |
|---------|---------|
| `bitable:app` | 获取多维表格信息 |
| `bitable:app:readonly` | 查看多维表格 |
| `bitable:app:read_write` | 编辑多维表格 |

权限配置后需要重新授权应用。

#### 1.3 获取多维表格 Token

1. 创建或打开一个飞书多维表格
2. 在浏览器地址栏查看 URL，格式如下：
   ```
   https://xxx.feishu.cn/base/bascnABC123?table=tblXYZ456
   ```
3. 提取 Token：
   - `bascnABC123` 是 **FEISHU_BITABLE_APP_TOKEN**
   - `tblXYZ456` 是 **FEISHU_BITABLE_TABLE_ID**

#### 1.4 创建表格字段

在飞书多维表格中创建以下字段（字段名必须完全匹配）：

| 字段名称 | 字段类型 | 说明 |
|---------|---------|------|
| 日期 | 日期 | 销售日期 |
| 店铺代码 | 文本 | 英文店铺代码（如 battersea_maocai） |
| 店铺名称 | 文本 | 中文店铺名称 |
| 平台 | 文本 | panda 或 deliveroo |
| 总销售额 | 数字 | gross_sales，保留2位小数 |
| 净销售额 | 数字 | net_sales，保留2位小数 |
| 订单数 | 数字 | order_count，整数 |
| 平均订单价值 | 数字 | avg_order_value，保留2位小数 |

### 步骤 2: 配置环境变量

编辑项目根目录的 `.env` 文件（参考 `.env.example`）：

```bash
# 飞书应用配置
FEISHU_APP_ID=cli_xxxxxxxxxxxxx              # 替换为你的 App ID
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxx      # 替换为你的 App Secret

# 飞书多维表格配置
FEISHU_BITABLE_APP_TOKEN=bascnxxxxxxxxxxxxx  # 替换为你的 app_token
FEISHU_BITABLE_TABLE_ID=tblxxxxxxxxxxxxx     # 替换为你的 table_id
```

### 步骤 3: 构建并启动服务

```bash
# 构建飞书同步服务镜像
cd /Users/levy/WorkSpace/Program/HaidilaoService/DataAutomaticEngine
docker compose build

# 或者单独构建
docker build -t dataautomaticengine-feishu-sync ./feishu_sync

# 启动所有服务
docker compose up -d
```

### 步骤 4: 测试同步

#### 方式 1: 使用便捷脚本（推荐）

```bash
# 同步昨天的数据
./sync_feishu_bitable.sh $(date -v-1d +%Y-%m-%d)

# 同步指定日期
./sync_feishu_bitable.sh 2025-12-24

# 同步日期范围
./sync_feishu_bitable.sh 2025-12-20 2025-12-25
```

#### 方式 2: 通过 API

```bash
# 同步最近7天
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

#### 方式 3: 直接运行容器

```bash
# 使用默认参数（最近7天）
docker run --rm --env-file .env \
  --network dataautomaticengine_default \
  dataautomaticengine-feishu-sync

# 指定日期范围
docker run --rm --env-file .env \
  --network dataautomaticengine_default \
  dataautomaticengine-feishu-sync \
  python main.py --start-date 2025-12-20 --end-date 2025-12-25
```

## 📅 自动化定时任务

定时任务已配置在 `scheduler/scheduler.cron` 中：

```cron
# 每天早上7:30同步昨天的数据到飞书多维表格
30 7 * * * curl -s -X POST http://api:8000/run/feishu-sync \
  -H "Content-Type: application/json" \
  -d '{"start_date":"$(date -d yesterday +%Y-%m-%d)","end_date":"$(date -d yesterday +%Y-%m-%d)"}' \
  >> /var/log/cron-feishu-sync.log 2>&1
```

**执行顺序：**
- 4:00 AM - HungryPanda 订单爬取
- 5:00 AM - Deliveroo 订单爬取
- 6:00 AM - Deliveroo 日汇总爬取
- 6:10 AM - HungryPanda 日汇总计算
- **7:30 AM - 飞书多维表格同步** ⬅️ 确保数据已准备好
- 9:00 AM - 飞书推送昨日汇总

## 🔍 同步逻辑说明

### 唯一键机制

使用 `日期_店铺代码_平台` 作为唯一键，例如：
- `2025-12-24_battersea_maocai_panda`
- `2025-12-24_piccadilly_hotpot_deliveroo`

### 增量更新策略

1. **首次同步**：查询飞书表格所有记录，构建唯一键映射
2. **逐条处理**：
   - 如果唯一键已存在 → 更新记录
   - 如果唯一键不存在 → 创建新记录
3. **幂等性**：多次执行相同日期范围的同步，结果保持一致

### 数据转换

- **日期字段**：转换为飞书时间戳（毫秒）
- **数字字段**：转换为 float/int 类型
- **文本字段**：直接使用字符串

## 📊 查看日志

```bash
# 查看最新的同步日志
ls -lt api/logs/feishu_sync_*.log | head -1 | xargs cat

# 实时查看日志
tail -f api/logs/feishu_sync_$(date +%Y%m%d)*.log

# 查看容器日志
docker logs delivery_api | grep feishu
```

## 🐛 常见问题排查

### 1. 权限不足错误

**错误信息：**
```
❌ 创建失败: 99991668 - permission denied
```

**解决方案：**
1. 检查应用权限配置，确保已添加 `bitable:app:read_write` 权限
2. 在应用管理页面点击"重新授权"
3. 将应用添加到多维表格的协作者列表

### 2. Token 错误

**错误信息：**
```
❌ 创建失败: 99991663 - invalid app_token
```

**解决方案：**
1. 检查 `.env` 中 `FEISHU_BITABLE_APP_TOKEN` 是否正确
2. 确认多维表格 URL 中的 token 是否匹配
3. 检查 token 是否包含完整的前缀（如 `bascn`）

### 3. 字段不匹配

**错误信息：**
```
❌ 创建失败: field not exist
```

**解决方案：**
1. 检查飞书表格中的字段名称是否与代码完全一致（包括大小写）
2. 确保字段类型正确（日期、文本、数字）
3. 参考上方"创建表格字段"部分重新创建字段

### 4. 数据库连接失败

**错误信息：**
```
❌ 同步失败: could not connect to server
```

**解决方案：**
1. 检查容器是否加入 `dataautomaticengine_default` 网络
2. 确认 `.env` 中 `DB_HOST=db`（容器内使用服务名）
3. 运行 `docker network ls` 检查网络是否存在

### 5. 日期格式问题

**错误信息：**
```
❌ 创建失败: invalid date format
```

**解决方案：**
1. 确保日期格式为 `YYYY-MM-DD`（如 `2025-12-24`）
2. 检查数据库中 `date` 字段的格式
3. 查看日志中的具体错误信息

## 🔧 高级配置

### 自定义同步频率

修改 `scheduler/scheduler.cron` 文件：

```cron
# 每2小时同步一次（增量更新）
0 */2 * * * curl -s -X POST http://api:8000/run/feishu-sync >> /var/log/cron-feishu-sync.log 2>&1

# 每天中午12点同步最近3天
0 12 * * * curl -s -X POST http://api:8000/run/feishu-sync \
  -H "Content-Type: application/json" \
  -d '{"start_date":"$(date -d '3 days ago' +%Y-%m-%d)"}' \
  >> /var/log/cron-feishu-sync.log 2>&1
```

### 仅同步特定店铺

```bash
# 仅同步巴特西店的数据
./sync_feishu_bitable.sh 2025-12-24

# 通过 API 过滤
curl -X POST http://localhost:8000/run/feishu-sync \
  -H "Content-Type: application/json" \
  -d '{
    "store_code": "battersea_maocai",
    "start_date": "2025-12-20",
    "end_date": "2025-12-25"
  }'
```

### 仅同步特定平台

```bash
# 仅同步 HungryPanda 平台数据
curl -X POST http://localhost:8000/run/feishu-sync \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "panda",
    "start_date": "2025-12-24"
  }'
```

## 📈 监控和维护

### 检查同步状态

```bash
# 查看最近的同步记录
tail -20 api/logs/feishu_sync_*.log

# 统计同步成功率
grep -c "✅" api/logs/feishu_sync_*.log
grep -c "❌" api/logs/feishu_sync_*.log
```

### 数据一致性检查

```bash
# 查看数据库中的记录数
./db_shell.sh
SELECT COUNT(*) FROM daily_sales_summary WHERE date >= '2025-12-20';

# 对比飞书表格中的记录数（在飞书表格中查看）
```

### 清理旧日志

```bash
# 删除7天前的日志
find api/logs -name "feishu_sync_*.log" -mtime +7 -delete
```

## 📚 相关文档

- [飞书同步服务 README](feishu_sync/README.md)
- [飞书开放平台文档](https://open.feishu.cn/document/home/introduction)
- [多维表格 API 参考](https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview)
- [项目架构说明](struct.MD)
- [AI Agent 指南](.github/copilot-instructions.md)

## 💡 最佳实践

1. **首次同步**：建议先同步最近1-2天的数据测试，确认无误后再同步历史数据
2. **定期检查**：每周检查一次同步日志，确保数据完整性
3. **权限管理**：定期更新飞书应用 Token，避免过期导致同步失败
4. **备份策略**：重要数据建议在数据库和飞书表格中都保留
5. **错误处理**：同步失败时及时查看日志，必要时手动补充数据

## 🆘 获取帮助

遇到问题？

1. 查看本文档的"常见问题排查"部分
2. 查看日志文件：`api/logs/feishu_sync_*.log`
3. 运行测试脚本：`./sync_feishu_bitable.sh --help`
4. 检查飞书开放平台的状态页面
5. 联系技术支持团队

---

**版本**：v1.0.0  
**最后更新**：2025-12-30
