# 定时任务调度器配置说明

## 当前定时任务

### 数据爬取阶段

#### 1. HungryPanda 订单爬虫（凌晨4点）
```cron
0 4 * * * 抓取所有 HungryPanda 店铺订单
```
- **执行时间**：每天凌晨 4:00
- **随机延迟**：1-5分钟（避免同时请求）
- **平台**：panda
- **店铺范围**：all（所有店铺）
- **数据存储**：raw_orders 表
- **日志文件**：`/var/log/cron-panda.log`

#### 2. Deliveroo 订单爬虫（凌晨5点）
```cron
0 5 * * * 抓取所有 Deliveroo 店铺订单
```
- **执行时间**：每天凌晨 5:00
- **随机延迟**：1-5分钟（避免同时请求）
- **平台**：deliveroo
- **店铺范围**：all（所有店铺）
- **数据存储**：raw_orders 表
- **日志文件**：`/var/log/cron-deliveroo.log`

### 汇总计算阶段

#### 3. Deliveroo 每日汇总爬虫（凌晨6点）
```cron
0 6 * * * 爬取 Deliveroo 每日销售汇总
```
- **执行时间**：每天凌晨 6:00（等待5点订单爬虫完成）
- **延迟**：5分钟（确保订单爬虫完成）
- **数据来源**：Deliveroo Summary API
- **店铺范围**：all（所有店铺）
- **日期**：昨天
- **数据存储**：daily_sales_summary 表
- **日志文件**：`/var/log/cron-deliveroo-summary.log`

#### 4. HungryPanda ETL 汇总计算（凌晨6点10分）
```cron
10 6 * * * 计算 HungryPanda 每日销售汇总
```
- **执行时间**：每天凌晨 6:10（等待4点订单爬虫完成）
- **延迟**：1分钟（缓冲时间）
- **数据来源**：raw_orders 表（聚合计算）
- **店铺范围**：all（所有店铺）
- **日期**：昨天
- **数据存储**：daily_sales_summary 表
- **日志文件**：`/var/log/cron-panda-summary.log`

### 飞书推送阶段

#### 5. 昨日订单汇总推送（早上9点）
```cron
0 9 * * * 发送昨日订单汇总到飞书
```
- **执行时间**：每天早上 9:00
- **数据来源**：daily_sales_summary 表
- **功能**：推送昨日全平台订单统计
- **日志文件**：`/var/log/cron-feishu.log`

## 完整流程时间线

```
03:00-04:00  ▶ HungryPanda 平台订单陆续完成
04:00        ▶ 【任务1】HungryPanda 订单爬虫启动
04:01-04:05  ▶ 随机延迟后开始爬取
04:30        ▶ 订单数据写入 raw_orders 表

05:00        ▶ 【任务2】Deliveroo 订单爬虫启动
05:01-05:05  ▶ 随机延迟后开始爬取
05:30        ▶ 订单数据写入 raw_orders 表

06:00        ▶ 【任务3】Deliveroo 每日汇总爬虫启动
06:05        ▶ 延迟5分钟后开始爬取
06:10        ▶ 【任务4】HungryPanda ETL 计算启动
06:15        ▶ 汇总数据写入 daily_sales_summary 表

09:00        ▶ 【任务5】飞书推送昨日汇总
09:00        ▶ 管理人员收到数据报告
```

## 设计理念

### 1. 分阶段执行
- **阶段1（4:00-5:30）**：原始订单数据爬取
- **阶段2（6:00-6:15）**：汇总数据计算
- **阶段3（9:00）**：数据推送通知

### 2. 错峰处理
1. **避免资源冲突**：两个平台订单爬虫错开1小时
2. **汇总依赖**：等待订单数据完成后再计算汇总
3. **降低风险**：一个平台失败不影响另一个

### 3. 数据一致性
- 订单爬虫完成 → 汇总计算开始
- 汇总数据入库 → 飞书推送读取
- 避免推送时数据未准备好

### 4. 便于监控
- 独立的日志文件便于问题排查
- 明确的时间节点便于追踪进度
- 失败时可单独重跑某个阶段

## 日志查看

### 查看订单爬虫日志
```bash
# HungryPanda 订单爬虫
docker exec dataautomaticengine-scheduler-1 tail -f /var/log/cron-panda.log

# Deliveroo 订单爬虫
docker exec dataautomaticengine-scheduler-1 tail -f /var/log/cron-deliveroo.log
```

### 查看汇总计算日志
```bash
# Deliveroo 每日汇总爬虫
docker exec dataautomaticengine-scheduler-1 tail -f /var/log/cron-deliveroo-summary.log

# HungryPanda ETL 汇总计算
docker exec dataautomaticengine-scheduler-1 tail -f /var/log/cron-panda-summary.log
```

### 查看飞书推送日志
```bash
docker exec dataautomaticengine-scheduler-1 tail -f /var/log/cron-feishu.log
```

### 查看系统 cron 日志
```bash
docker logs dataautomaticengine-scheduler-1
```

## 手动触发任务

### 触发订单爬虫
```bash
# HungryPanda 订单爬虫
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{"platform":"panda","store_code":"all"}'

# Deliveroo 订单爬虫
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{"platform":"deliveroo","store_code":"all"}'
```

### 触发汇总计算
```bash
# Deliveroo 每日汇总（指定日期）
curl -X POST http://localhost:8000/run/deliveroo/daily-summary \
  -H "Content-Type: application/json" \
  -d '{"stores":["all"],"date":"2025-12-22"}'

# HungryPanda ETL 汇总计算（指定日期）
curl -X POST http://localhost:8000/run/panda/daily-summary \
  -H "Content-Type: application/json" \
  -d '{"store_code":"all","date":"2025-12-22"}'

# 批量计算多日（12-20 到 12-27）
curl -X POST http://localhost:8000/run/deliveroo/daily-summary \
  -H "Content-Type: application/json" \
  -d '{"stores":["all"],"start_date":"2025-12-20","end_date":"2025-12-27"}'

curl -X POST http://localhost:8000/run/panda/daily-summary \
  -H "Content-Type: application/json" \
  -d '{"store_code":"all","start_date":"2025-12-20","end_date":"2025-12-27"}'
```

### 触发飞书推送
```bash
curl -X POST http://localhost:8000/reminder/daily-summary
```

## 修改定时任务

### 1. 编辑配置文件
```bash
vim scheduler/scheduler.cron
```

### 2. 重新构建并启动
```bash
docker compose up -d --build scheduler
```

### 3. 验证任务是否生效
```bash
docker exec dataautomaticengine-scheduler-1 crontab -l
```

## Cron 表达式参考

```
分 时 日 月 周
*  *  *  *  *
│  │  │  │  │
│  │  │  │  └─ 星期几 (0-7, 0和7都代表周日)
│  │  │  └──── 月份 (1-12)
│  │  └─────── 日期 (1-31)
│  └────────── 小时 (0-23)
└───────────── 分钟 (0-59)
```

### 常用示例
```cron
0 4 * * *          # 每天凌晨4点
0 */6 * * *        # 每6小时
30 2 * * 1         # 每周一凌晨2:30
0 0 1 * *          # 每月1号凌晨
0 9 * * 1-5        # 工作日早上9点
```

## 手动触发爬虫

如果需要立即执行而不等待定时任务：

### HungryPanda
```bash
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{"platform":"panda","store_code":"all"}'
```

### Deliveroo
```bash
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{"platform":"deliveroo","store_code":"all"}'
```

## 环境变量

Scheduler 容器内可用的环境变量（从 docker-compose.yaml 继承）：

- `TZ` - 时区设置（默认 UTC）
- API 端点通过容器网络访问：`http://api:8000`

## 故障排查

### 定时任务未执行？
1. 检查容器是否运行：`docker ps | grep scheduler`
2. 查看 cron 日志：`docker logs dataautomaticengine-scheduler-1`
3. 验证 crontab：`docker exec dataautomaticengine-scheduler-1 crontab -l`
4. 检查时区设置：`docker exec dataautomaticengine-scheduler-1 date`

### API 调用失败？
1. 检查 API 容器状态：`docker ps | grep api`
2. 测试网络连通性：`docker exec dataautomaticengine-scheduler-1 ping api`
3. 手动测试 API：`curl http://localhost:8000/health`

### 日志文件不存在？
容器内的 `/var/log` 是临时的，重启后会丢失。如需持久化：
```yaml
# docker-compose.yaml 中添加卷挂载
volumes:
  - ./scheduler/logs:/var/log
```

## 最佳实践

1. **错峰执行**：避免多个任务同时启动
2. **随机延迟**：使用 `sleep $((60 + RANDOM % 240))` 避免准点压力
3. **日志记录**：所有任务都应重定向输出到日志文件
4. **监控告警**：配合飞书提醒监控任务执行状态
5. **测试验证**：修改后先手动触发测试，确认无误再部署

## 参考文档

- [Docker Compose 文档](../docker-compose.yaml)
- [爬虫 API 文档](../api/routers/crawler.py)
- [多平台支持说明](../PLATFORM_SUPPORT_CHANGELOG.md)
