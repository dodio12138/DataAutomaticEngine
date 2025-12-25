# 手动爬虫脚本使用指南

## 爬虫时间逻辑

爬虫的时间参数逻辑为：
- `start_date=2025-12-24, end_date=2025-12-25` 表示爬取 **12月24日当天** 的数据
- 即：`end_date` 是 `start_date + 1天`，爬取的是 `start_date` 这一天的订单

## 脚本用法

### 基础语法
```bash
./manual_crawl.sh [起始日期] [结束日期] [店铺代码]
```

### 使用示例

#### 1. 爬取单日数据（最常用）
```bash
# 爬取昨天所有店铺的数据（默认）
./manual_crawl.sh

# 爬取12月24日所有店铺的数据
./manual_crawl.sh 2025-12-24

# 爬取12月24日指定店铺的数据
./manual_crawl.sh 2025-12-24 battersea_maocai
```

#### 2. 爬取日期范围（批量补爬）
```bash
# 爬取12月20日到24日（共5天）所有店铺
./manual_crawl.sh 2025-12-20 2025-12-25

# 爬取12月20日到24日指定店铺
./manual_crawl.sh 2025-12-20 2025-12-25 battersea_maocai
```

**注意：** 
- 日期范围 `2025-12-20` 到 `2025-12-25` 会爬取 20, 21, 22, 23, 24 共5天的数据
- 结束日期本身不会被爬取（因为爬虫逻辑是爬取到 end_date 前一天）

## 店铺代码

### 常用店铺代码
- `all` - 所有店铺（默认）
- `battersea_maocai` - 海底捞冒菜（巴特西）
- 其他店铺代码见 [crawler/store_config.py](crawler/store_config.py)

### 多店铺爬取
如需爬取多个指定店铺，需要多次调用脚本：
```bash
./manual_crawl.sh 2025-12-24 battersea_maocai
./manual_crawl.sh 2025-12-24 store_code_2
```

## 执行流程

1. **检查 API 容器状态** - 确保 `delivery_api` 容器运行中
2. **计算日期范围** - 根据爬虫逻辑自动计算需要爬取的天数
3. **逐天提交任务** - 循环调用 API `/run/crawler` 端点
4. **显示汇总结果** - 显示成功/失败统计

## 输出示例

```
========================================
  手动触发爬虫 - 批量模式
========================================
起始日期: 2025-12-21
结束日期: 2025-12-22
店铺代码: battersea_maocai

📅 共需爬取 1 天的数据 (2025-12-21 到 2025-12-21)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 正在爬取: 2025-12-21 (API参数: start=2025-12-21, end=2025-12-22)
   店铺: battersea_maocai
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 2025-12-21 爬取任务已提交

========================================
  爬取任务汇总
========================================
✅ 成功: 1 天
❌ 失败: 0 天
📊 总计: 1 天

查看实时日志:
  docker logs -f delivery_api

查看爬虫日志文件:
  ls -lht api/logs/ | head -10
```

## 日志查看

### 实时查看 API 日志
```bash
docker logs -f delivery_api
```

### 查看爬虫日志文件
```bash
ls -lht api/logs/ | head -10
tail -f api/logs/crawler_YYYYMMDD_HHMMSS.log
```

### 查看数据库数据
```bash
# 查看统计信息
./db_stats.sh

# 查看指定日期订单
./db_view_orders.sh 2025-12-24

# 查看每日汇总
./db_daily_summary.sh 2025-12-24
```

## 常见问题

### 1. API 容器未运行
**错误信息：** `❌ API 容器未运行`

**解决方案：**
```bash
docker compose up -d api
```

### 2. 日期格式错误
**正确格式：** `YYYY-MM-DD` （如 `2025-12-24`）

### 3. 爬取任务提交失败
**可能原因：**
- 店铺代码不存在
- 日期范围超出限制
- API 服务异常

**排查步骤：**
1. 检查 API 日志：`docker logs delivery_api --tail 50`
2. 验证店铺代码：查看 `crawler/store_config.py`
3. 手动测试 API：
```bash
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{
    "store_code": "battersea_maocai",
    "start_date": "2025-12-24",
    "end_date": "2025-12-25"
  }'
```

## 最佳实践

### 1. 定期补爬
如果自动定时任务失败，使用脚本手动补爬：
```bash
# 补爬过去3天
./manual_crawl.sh $(date -v-3d +%Y-%m-%d) $(date -v-1d +%Y-%m-%d)
```

### 2. 验证数据
爬取完成后使用数据库工具验证：
```bash
./db_stats.sh
./db_daily_summary.sh 2025-12-24
```

### 3. 批量爬取时间间隔
脚本内置1秒间隔，避免对平台造成过大压力。如需调整，修改脚本中的 `sleep 1`。

### 4. 错误处理
脚本遇到失败会继续处理后续日期，最后汇总显示失败天数。退出码非0表示有失败任务。

## 参数参考

| 参数位置 | 说明 | 必填 | 默认值 | 示例 |
|---------|------|------|--------|------|
| 第1个 | 起始日期 | 否 | 昨天 | `2025-12-24` |
| 第2个 | 结束日期或店铺代码 | 否 | 起始日期+1天 / `all` | `2025-12-25` 或 `battersea_maocai` |
| 第3个 | 店铺代码 | 否 | `all` | `battersea_maocai` |

## 相关文档

- [API 文档](api/MODULE_STRUCTURE.md)
- [店铺配置](crawler/store_config.py)
- [数据库查询工具](DB_TOOLS.md)
- [项目架构](struct.MD)
