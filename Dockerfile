FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 包管理工具
RUN pip install uv

# 设置工作目录
WORKDIR /app

# 先拷贝依赖清单和锁文件，利用 uv 进行安装
COPY pyproject.toml uv.lock ./
RUN uv sync

# 拷贝环境变量文件
COPY .env .env

# 拷贝项目源码
COPY . .

# 复制并授权 entrypoint
COPY ./docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露应用端口
EXPOSE 8000

# 使用 entrypoint 启动
ENTRYPOINT ["/entrypoint.sh"]
