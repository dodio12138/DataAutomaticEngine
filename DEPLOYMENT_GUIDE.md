# 服务器部署更新指南

## 快速部署流程

### 1. 连接服务器
```bash
ssh user@your-server-ip
cd /path/to/DataAutomaticEngine
```

### 2. 拉取最新代码
```bash
# 拉取最新代码
git pull origin main

# 或指定分支
git pull origin <branch-name>
```

### 3. 重新构建并启动服务
```bash
# 方式一：完整重建（推荐，确保所有更改生效）
./clean_rebuild.sh

# 方式二：快速重启（仅重启容器，不重建镜像）
docker compose down && docker compose up -d

# 方式三：仅重启 API 服务（修改了 API 代码时）
docker compose restart api
```

### 4. 验证部署
```bash
# 检查容器状态
docker ps

# 检查服务健康
curl http://localhost:8000/health

# 查看 API 日志
docker logs -f delivery_api

# 查看调度器日志
docker logs -f delivery_scheduler
```

---

## 详细部署场景

### 场景 1：更新了 API 代码
```bash
git pull origin main
docker compose build api
docker compose up -d api
docker logs -f delivery_api  # 验证启动
```

### 场景 2：更新了爬虫代码
```bash
git pull origin main
docker compose build crawler
# 爬虫是临时容器，下次运行时自动使用新镜像
```

### 场景 3：更新了 ETL 代码
```bash
git pull origin main
docker compose build etl
# ETL 是临时容器，下次运行时自动使用新镜像
```

### 场景 4：更新了飞书同步代码
```bash
git pull origin main
docker compose build feishu_sync
# 飞书同步是临时容器，下次运行时自动使用新镜像
```

### 场景 5：更新了数据库迁移文件
```bash
git pull origin main
docker compose down
docker compose up -d
# PostgreSQL 容器启动时会自动执行 db/migrations/ 中的新迁移
```

### 场景 6：更新了定时任务 (scheduler.cron)
```bash
git pull origin main
docker compose restart scheduler
docker exec delivery_scheduler crontab -l  # 验证定时任务
```

### 场景 7：更新了环境变量 (.env)
```bash
# 编辑 .env 文件
vim .env

# 重启所有服务以加载新环境变量
docker compose down
docker compose up -d
```

---

## 常用运维命令

### 查看日志
```bash
# 查看 API 日志
docker logs delivery_api
docker logs -f delivery_api  # 实时跟踪

# 查看爬虫日志
ls -lt api/logs/crawler_*.log | head -5

# 查看 ETL 日志
ls -lt api/logs/*_summary_*.log | head -5

# 查看定时任务日志
docker exec delivery_scheduler cat /var/log/cron-ratings.log
docker exec delivery_scheduler cat /var/log/cron-panda.log
```

### 手动触发任务
```bash
# 爬取订单
./manual_crawl.sh 2026-01-17

# 爬取评分
./manual_ratings.sh

# 同步飞书
./sync_feishu_bitable.sh 2026-01-17
./sync_hourly_sales.sh 2026-01-17
./sync_store_ratings.sh 2026-01-17

# 聚合小时销售
curl -X POST http://localhost:8000/run/hourly-sales/aggregate \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-01-17"}'
```

### 数据库操作
```bash
# 进入数据库
./db_shell.sh

# 查看汇总数据
./db_view_daily_summary.sh

# 查看评分数据
./db_view_ratings.sh

# 查看订单详情
./db_view_orders.sh

# 查看数据统计
./db_stats.sh
```

### 服务管理
```bash
# 停止所有服务
docker compose down

# 启动所有服务
docker compose up -d

# 重启单个服务
docker compose restart api
docker compose restart scheduler

# 查看服务状态
docker compose ps

# 查看资源使用
docker stats
```

---

## 故障排查

### 问题 1：API 启动失败
```bash
# 查看错误日志
docker logs delivery_api

# 常见原因：
# - 数据库未启动：docker compose up -d db
# - 端口被占用：lsof -i :8000
# - 环境变量缺失：检查 .env 文件
```

### 问题 2：定时任务不执行
```bash
# 检查 scheduler 容器状态
docker ps | grep scheduler

# 查看 crontab 配置
docker exec delivery_scheduler crontab -l

# 查看定时任务日志
docker exec delivery_scheduler cat /var/log/cron-ratings.log

# 重启 scheduler
docker compose restart scheduler
```

### 问题 3：飞书同步失败
```bash
# 检查环境变量
docker exec delivery_api printenv | grep FEISHU

# 手动测试同步
./sync_store_ratings.sh

# 查看详细日志
ls -lt api/logs/store_ratings_sync_*.log | head -1
tail -100 api/logs/store_ratings_sync_*.log
```

### 问题 4：爬虫执行失败
```bash
# 查看爬虫日志
ls -lt api/logs/crawler_*.log | head -5
tail -100 api/logs/crawler_*.log

# 检查 Selenium 容器
docker ps -a | grep crawler

# 手动测试爬虫
./manual_crawl.sh 2026-01-17
```

---

## 回滚策略

### 快速回滚到上一版本
```bash
# 1. 回退代码
git log --oneline -5  # 查看最近提交
git checkout <previous-commit-hash>

# 2. 重新构建
./clean_rebuild.sh

# 3. 验证
curl http://localhost:8000/health
```

### 使用 Git 标签回滚
```bash
# 查看可用标签
git tag -l

# 回滚到指定标签
git checkout tags/<tag-name>

# 重新构建
./clean_rebuild.sh
```

---

## 性能监控

### 检查系统资源
```bash
# 容器资源使用
docker stats --no-stream

# 磁盘空间
df -h

# 日志文件大小
du -sh api/logs/

# 清理旧日志（保留最近7天）
find api/logs/ -name "*.log" -mtime +7 -delete
```

### 数据库监控
```bash
# 数据库大小
./db_shell.sh
\l+  # 列出所有数据库及大小
\dt+  # 列出所有表及大小

# 查询慢查询
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC LIMIT 10;
```

---

## 备份与恢复

### 备份数据库
```bash
# 导出完整数据库
docker exec delivery_postgres pg_dump -U delivery_user delivery_data > backup_$(date +%Y%m%d).sql

# 仅导出特定表
docker exec delivery_postgres pg_dump -U delivery_user -t store_ratings delivery_data > store_ratings_backup.sql
```

### 恢复数据库
```bash
# 恢复完整数据库
cat backup_20260118.sql | docker exec -i delivery_postgres psql -U delivery_user delivery_data

# 恢复特定表
cat store_ratings_backup.sql | docker exec -i delivery_postgres psql -U delivery_user delivery_data
```

---

## 生产环境最佳实践

### 1. 部署前检查清单
- [ ] 代码已在本地测试通过
- [ ] 数据库迁移文件已准备好
- [ ] 环境变量已配置完整
- [ ] 备份当前数据库
- [ ] 通知团队成员即将部署

### 2. 部署步骤
```bash
# 1. 备份数据库
docker exec delivery_postgres pg_dump -U delivery_user delivery_data > backup_$(date +%Y%m%d).sql

# 2. 拉取代码
git pull origin main

# 3. 停止服务
docker compose down

# 4. 构建镜像
docker compose build

# 5. 启动服务
docker compose up -d

# 6. 验证部署
curl http://localhost:8000/health
docker ps
docker logs delivery_api

# 7. 测试关键功能
./test_store_ratings_sync.sh
```

### 3. 部署后验证
```bash
# 检查所有容器运行正常
docker ps

# 检查日志无错误
docker logs delivery_api | grep -i error
docker logs delivery_scheduler | grep -i error

# 手动触发一次任务验证
./manual_ratings.sh

# 检查数据库数据
./db_stats.sh
```

---

## 自动化部署脚本

创建 `deploy.sh` 脚本：

```bash
#!/bin/bash
set -e

echo "🚀 开始部署..."

# 1. 备份
echo "📦 备份数据库..."
docker exec delivery_postgres pg_dump -U delivery_user delivery_data > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 拉取代码
echo "📥 拉取最新代码..."
git pull origin main

# 3. 重建服务
echo "🔨 重建服务..."
docker compose down
docker compose build
docker compose up -d

# 4. 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 5. 验证
echo "✅ 验证部署..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ 部署成功！"
    docker ps
else
    echo "❌ 部署失败，请检查日志"
    docker logs delivery_api
    exit 1
fi
```

使用方式：
```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 快速参考

| 操作 | 命令 |
|------|------|
| 拉取代码 | `git pull origin main` |
| 完整重建 | `./clean_rebuild.sh` |
| 快速重启 | `docker compose restart api` |
| 查看日志 | `docker logs -f delivery_api` |
| 健康检查 | `curl http://localhost:8000/health` |
| 进入数据库 | `./db_shell.sh` |
| 手动爬虫 | `./manual_crawl.sh 2026-01-17` |
| 飞书同步 | `./sync_store_ratings.sh` |

---

## 联系与支持

遇到问题时：
1. 查看本文档的故障排查章节
2. 检查相关日志文件
3. 查看项目根目录的 `*.md` 文档
4. 联系开发团队
