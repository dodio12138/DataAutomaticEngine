FROM alpine:3.19

# 安装 cron + curl（调用 API 用）
RUN apk add --no-cache \
    bash \
    curl \
    tzdata

# 拷贝 crontab
COPY crontab /etc/crontabs/root

# 权限必须对
RUN chmod 0644 /etc/crontabs/root

# 关键：以前台模式运行 cron
CMD ["crond", "-f", "-l", "2"]
