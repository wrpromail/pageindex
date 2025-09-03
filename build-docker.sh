#!/bin/bash

# PageIndex Docker 构建脚本 (简化版)
# 用于快速构建和测试Docker镜像

set -e

IMAGE_NAME="pageindex"
IMAGE_TAG="latest"

echo "=== PageIndex Docker 构建脚本 ==="

# 检查Docker
if ! docker info &> /dev/null; then
    echo "❌ Docker 未运行，请启动 Docker Desktop"
    exit 1
fi

echo "✅ Docker 检查通过"

# 构建镜像（指定amd64平台）
echo "🔨 开始构建 Docker 镜像 (linux/amd64)..."
docker build --platform linux/amd64 -t "$IMAGE_NAME:$IMAGE_TAG" .

if [[ $? -eq 0 ]]; then
    echo "✅ Docker 镜像构建成功!"
    echo ""
    echo "📋 镜像信息:"
    docker images "$IMAGE_NAME:$IMAGE_TAG"
    echo ""
    echo "🚀 使用方式:"
    echo "  方法1 - 使用docker-compose:"
    echo "    docker-compose up"
    echo ""
    echo "  方法2 - 直接使用docker run:"
    echo "    docker run -p 8501:8501 \\"
    echo "      -v \$(pwd)/model_configs.yaml:/app/model_configs.yaml:ro \\"
    echo "      -v \$(pwd)/prompt_config.yaml:/app/prompt_config.yaml:ro \\"
    echo "      -v \$(pwd)/ocr_files:/app/ocr_files \\"
    echo "      -v \$(pwd)/results:/app/results \\"
    echo "      $IMAGE_NAME:$IMAGE_TAG"
    echo ""
    echo "📖 查看部署文档: docs/DOCKER_DEPLOYMENT.md"
else
    echo "❌ Docker 镜像构建失败!"
    exit 1
fi
