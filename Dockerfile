# 使用官方的Python基础镜像，指定amd64架构
FROM --platform=linux/amd64 python:3.13.7-alpine3.22

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    cargo \
    rust \
    && rm -rf /var/cache/apk/*

# 安装 uv
RUN pip install --no-cache-dir uv

# 复制项目文件
COPY . .

# 使用 uv 安装依赖
RUN uv pip install --system -e .

# 创建必要的目录
RUN mkdir -p /app/ocr_files /app/results /app/temp /app/index_states /app/checkpoints /app/cookbook /app/docs /app/tests /app/tutorials

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8501

# 设置健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import streamlit; print('Streamlit available')" || exit 1

# 启动命令
CMD ["streamlit", "run", "streamlit_app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
