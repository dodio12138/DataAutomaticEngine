# 定时任务调度器配置说明

## 当前定时任务

### 1. HungryPanda 爬虫（凌晨4点）
```cron
0 4 * * * 抓取所有 HungryPanda 店铺订单
```
- **执行时间**：每天凌晨 4:00
- **随机延迟**：1-5分钟（避免同时请求）
- **平台**：panda
- **店铺范围**：all（所有店铺）
- **日志文件**：`/var/log/cron-panda.log`

### 2. Deliveroo 爬虫（凌晨5点）
```cron
0 5 * * * 抓取所有 Deliveroo 店铺订单
```
- **执行时间**：每天凌晨 5:00
- **随机延迟**：1-5分钟（避免同时请求）
- **平台**：deliveroo
- **店铺范围**：all（所有店铺）
- **日志文件**：`/var/log/cron-deliveroo.log`

### 3. 昨日订单汇总（早上9点）
```cron
0 9 * * * 发送昨日订单汇总到飞书
```
- **执行时间**：每天早上 9:00
- **功能**：推送昨日订单统计

## 时间安排说明

### 为什么分开执行？
1. **避免资源冲突**：两个平台同时爬取可能导致内存/CPU 峰值
2. **降低风险**：一个平台失败不影响另一个
3. **便于追踪**：独立的日志文件便于问题排查
4. **符合业务节奏**：HungryPanda 通常订单更多，优先处理

### 时间选择理由
- **4:00** - 熊猫订单通常在凌晨3点后基本完成
- **5:00** - Deliveroo 订单延后1小时，错峰处理
- **9:00** - 工作时间开始，便于查看昨日数据

## 日志查看

### 查看 HungryPanda 爬虫日志
```bash
docker exec dataautomaticengine-scheduler-1 tail -f /var/log/cron-panda.log
```

### 查看 Deliveroo 爬虫日志
```bash
docker exec dataautomaticengine-scheduler-1 tail -f /var/log/cron-deliveroo.log
```

### 查看系统 cron 日志
```bash
docker logs dataautomaticengine-scheduler-1
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
