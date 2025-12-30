FROM alpine:3.19

# 安装 cron + curl（调用 API 用）
RUN apk add --no-cache \
    bash \
    curl \
    tzdata

# 设置时区
ENV TZ=Europe/London
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime

# 创建日志目录
RUN mkdir -p /var/log && chmod 777 /var/log

# 拷贝 crontab
COPY scheduler.cron /etc/crontabs/root

# 权限必须对
RUN chmod 0644 /etc/crontabs/root

# 关键：以前台模式运行 cron
CMD ["crond", "-f", "-l", "2"]
