# 基础镜像
FROM python:3.11-slim

# 安装 chromium 和 chromedriver 所需依赖（Debian slim）
RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
	   wget gnupg ca-certificates unzip fonts-liberation libnss3 libxss1 libasound2 \
	   libatk-bridge2.0-0 libgtk-3-0 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 \
	&& rm -rf /var/lib/apt/lists/*

# 安装 Chromium
RUN apt-get update && apt-get install -y chromium \
	&& rm -rf /var/lib/apt/lists/*

# 下载与 Chromium 兼容的 chromedriver（尽量使用匹配版本，示例中使用 chromium-driver 包名）
RUN apt-get update && apt-get install -y chromium-driver \
	&& rm -rf /var/lib/apt/lists/*

# 创建指向 chromedriver 的标准位置（某些系统将其安装到 /usr/bin/chromedriver）
RUN if [ -f /usr/bin/chromedriver ]; then ln -s /usr/bin/chromedriver /usr/local/bin/chromedriver || true; \
	elif [ -f /usr/lib/chromium/chromedriver ]; then ln -s /usr/lib/chromium/chromedriver /usr/local/bin/chromedriver || true; fi

# 设置工作目录
WORKDIR /app

# 拷贝 Python 依赖文件并安装（包含 selenium）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝源码
COPY . .

# 环境变量，指向 chromium 可执行文件
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/local/bin/chromedriver

# 设置默认执行命令
CMD ["python", "main.py"]
