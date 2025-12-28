# 定时任务多平台调度配置 - 部署完成

## ✅ 已完成配置

### 定时任务时间表

| 时间 | 平台 | 任务 | 随机延迟 | 日志文件 |
|------|------|------|----------|----------|
| 04:00 | HungryPanda | 爬取所有店铺订单 | 1-5分钟 | `/var/log/cron-panda.log` |
| 05:00 | Deliveroo | 爬取所有店铺订单 | 1-5分钟 | `/var/log/cron-deliveroo.log` |
| 09:00 | - | 发送昨日订单汇总 | 无 | - |

### 配置文件

**[scheduler/scheduler.cron](scheduler/scheduler.cron)**
```cron
# HungryPanda - 凌晨4点
0 4 * * * /bin/bash -c 'sleep $((60 + RANDOM % 240)) && curl -s -X POST http://api:8000/run/crawler -H "Content-Type: application/json" -d '"'"'{"platform":"panda","store_code":"all"}'"'"' >> /var/log/cron-panda.log 2>&1'

# Deliveroo - 凌晨5点
0 5 * * * /bin/bash -c 'sleep $((60 + RANDOM % 240)) && curl -s -X POST http://api:8000/run/crawler -H "Content-Type: application/json" -d '"'"'{"platform":"deliveroo","store_code":"all"}'"'"' >> /var/log/cron-deliveroo.log 2>&1'
```

## 🚀 快速部署

### 方式一：使用部署脚本（推荐）
```bash
./deploy_scheduler.sh
```

### 方式二：手动部署
```bash
# 1. 停止当前容器
docker compose stop scheduler

# 2. 重新构建
docker compose build scheduler

# 3. 启动容器
docker compose up -d scheduler

# 4. 验证配置
docker exec dataautomaticengine-scheduler-1 crontab -l
```

## 🧪 测试与验证

### 验证定时任务配置
```bash
./verify_scheduler.sh
```

### 手动触发测试
```bash
# 测试 HungryPanda
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{"platform":"panda","store_code":"all"}'

# 测试 Deliveroo
curl -X POST http://localhost:8000/run/crawler \
  -H "Content-Type: application/json" \
  -d '{"platform":"deliveroo","store_code":"all"}'
```

### 查看日志

#### 实时监控 HungryPanda 日志
```bash
docker exec dataautomaticengine-scheduler-1 tail -f /var/log/cron-panda.log
```

#### 实时监控 Deliveroo 日志
```bash
docker exec dataautomaticengine-scheduler-1 tail -f /var/log/cron-deliveroo.log
```

#### 查看容器日志
```bash
docker logs -f dataautomaticengine-scheduler-1
```

## 📊 时间安排说明

### 为什么分开1小时？

1. **避免资源冲突**
   - 两个爬虫同时运行会占用大量内存和CPU
   - Selenium 浏览器实例需要大量资源
   - 分开执行确保系统稳定

2. **降低风险**
   - 一个平台失败不影响另一个
   - 独立的日志便于问题追踪
   - 便于单独重试失败的任务

3. **业务优先级**
   - HungryPanda 订单量通常更大，优先处理
   - Deliveroo 延后1小时，确保数据完整性
   - 给每个平台充足的执行时间

### 随机延迟的意义

```bash
sleep $((60 + RANDOM % 240))
```

- **60秒基础延迟**：等待系统启动稳定
- **240秒随机**：避免准点请求高峰（4-8分钟）
- **避免检测**：类似人工操作的时间分布
- **降低负载**：分散请求时间

## 🔧 故障排查

### 问题1：定时任务未执行

**检查步骤：**
```bash
# 1. 容器是否运行
docker ps | grep scheduler

# 2. 查看 crontab 配置
docker exec dataautomaticengine-scheduler-1 crontab -l

# 3. 检查容器日志
docker logs dataautomaticengine-scheduler-1

# 4. 验证时间设置
docker exec dataautomaticengine-scheduler-1 date
```

### 问题2：API 调用失败

**检查步骤：**
```bash
# 1. API 容器状态
docker ps | grep api

# 2. 网络连通性
docker exec dataautomaticengine-scheduler-1 ping -c 3 api

# 3. 手动测试 API
curl http://localhost:8000/health
```

### 问题3：日志文件为空

**可能原因：**
- 任务尚未执行（检查当前时间）
- 任务执行失败（查看容器日志）
- API 返回错误（手动触发测试）

## 📝 修改定时任务

### 更改执行时间

编辑 `scheduler/scheduler.cron`：
```cron
# 改为每天6点执行 Deliveroo
0 6 * * * /bin/bash -c '...'
```

### 添加新的定时任务

```cron
# 每2小时执行一次
0 */2 * * * curl -X POST http://api:8000/run/crawler -d '{"platform":"panda","store_code":"piccadilly_maocai"}'

# 只在工作日执行
0 8 * * 1-5 curl -X POST http://api:8000/reminder/daily-summary
```

### 应用更改

```bash
# 重新部署
./deploy_scheduler.sh

# 或手动重启
docker compose restart scheduler
```

## 📚 相关文档

- **[scheduler/README.md](scheduler/README.md)** - 详细的定时任务说明
- **[PLATFORM_SUPPORT_CHANGELOG.md](PLATFORM_SUPPORT_CHANGELOG.md)** - 多平台支持文档
- **[test_multi_platform.sh](test_multi_platform.sh)** - 多平台测试脚本
- **[verify_scheduler.sh](verify_scheduler.sh)** - 定时任务验证脚本

## 🎯 下一步

1. **部署定时任务**
   ```bash
   ./deploy_scheduler.sh
   ```

2. **验证配置**
   ```bash
   ./verify_scheduler.sh
   ```

3. **监控首次执行**
   - 在凌晨4点前准备好
   - 实时监控日志
   - 验证数据库记录

4. **配置告警**
   - 飞书提醒任务执行状态
   - 监控爬虫成功率
   - 数据完整性检查

## ⚠️ 注意事项

1. **时区设置**：确保容器时区正确（默认 UTC）
2. **网络连接**：scheduler 容器需要访问 api 容器
3. **资源限制**：确保主机有足够内存运行双爬虫
4. **日志管理**：定期清理旧日志文件
5. **数据备份**：定时任务前建议备份数据库

---

**部署时间：** 2025年12月27日  
**配置版本：** v2.0 - 多平台支持  
**维护人员：** 开发团队
