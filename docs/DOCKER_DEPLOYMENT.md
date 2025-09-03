# PageIndex Docker 部署指南

## 概述

本指南介绍如何使用Docker部署PageIndex智能文档检索系统。

## 前置要求

- Docker Desktop for Mac (macOS)
- Docker Engine 20.10+
- docker-compose 1.29+

## 快速开始

### 方法1：使用docker-compose（推荐）

```bash
# 1. 克隆项目
git clone <repository-url>
cd PageIndex

# 2. 构建并启动服务
docker-compose up --build

# 3. 访问应用
# 打开浏览器访问: http://localhost:8501
```

### 方法2：手动构建

```bash
# 1. 使用构建脚本（macOS）
./build-docker.sh

# 2. 启动容器
docker run -d \
  --name pageindex-app \
  -p 8501:8501 \
  -v $(pwd)/model_configs.yaml:/app/model_configs.yaml:ro \
  -v $(pwd)/prompt_config.yaml:/app/prompt_config.yaml:ro \
  -v $(pwd)/ocr_files:/app/ocr_files \
  -v $(pwd)/results:/app/results \
  pageindex:latest
```

## 配置文件挂载

### 必须挂载的配置文件

```yaml
# model_configs.yaml - 模型配置
volumes:
  - ./model_configs.yaml:/app/model_configs.yaml:ro

# prompt_config.yaml - 提示词配置
volumes:
  - ./prompt_config.yaml:/app/prompt_config.yaml:ro
```

### 数据目录挂载

```yaml
# OCR文件目录
volumes:
  - ./ocr_files:/app/ocr_files

# 索引结果目录
volumes:
  - ./results:/app/results

# 临时文件目录
volumes:
  - ./temp:/app/temp

# 索引状态目录
volumes:
  - ./index_states:/app/index_states
```

## 环境变量

可以在docker-compose.yml中添加环境变量：

```yaml
environment:
  - OPENAI_API_KEY=your_api_key
  - OTHER_CONFIG=value
```

## 端口映射

默认端口映射：
- `8501:8501` - Streamlit Web界面

## 构建选项

### 多平台构建

```bash
# 构建amd64镜像（默认）
./build-docker.sh

# 构建arm64镜像
docker buildx build --platform linux/arm64 -t pageindex:arm64 .
```

### 自定义构建

```bash
# 使用不同的Python版本
docker build --build-arg PYTHON_VERSION=3.12 -t pageindex:custom .

# 使用不同的基础镜像
docker build --build-arg BASE_IMAGE=python:3.12-slim -t pageindex:slim .
```

## 故障排除

### 常见问题

1. **构建失败**
   ```bash
   # 检查Docker状态
   docker info

   # 清理构建缓存
   docker system prune -f
   ```

2. **端口占用**
   ```bash
   # 检查端口使用情况
   lsof -i :8501

   # 修改端口映射
   docker run -p 8502:8501 pageindex:latest
   ```

3. **权限问题**
   ```bash
   # 检查目录权限
   ls -la ocr_files/

   # 修改目录权限
   chmod 755 ocr_files/
   ```

4. **内存不足**
   ```bash
   # 增加Docker内存分配
   # Docker Desktop -> Settings -> Resources -> Memory
   ```

### 日志查看

```bash
# 查看容器日志
docker-compose logs -f pageindex

# 查看构建日志
docker build --progress=plain .
```

## 性能优化

### 生产环境配置

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  pageindex:
    build:
      context: .
      dockerfile: Dockerfile
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 512M
    restart: always
```

### 使用外部数据库

如果需要持久化数据到外部数据库：

```yaml
services:
  pageindex:
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/pageindex
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=pageindex
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
```

## 更新和维护

### 更新镜像

```bash
# 重新构建
docker-compose build --no-cache

# 重新启动
docker-compose up -d
```

### 备份数据

```bash
# 备份配置和数据
tar -czf backup.tar.gz \
  model_configs.yaml \
  prompt_config.yaml \
  ocr_files/ \
  results/
```

## 监控和日志

### 健康检查

容器包含健康检查配置：
- 间隔：30秒
- 超时：10秒
- 重试：3次

### 日志轮转

```bash
# 配置日志轮转
docker-compose.yml 添加：
services:
  pageindex:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## 安全建议

1. **使用只读挂载**
   ```yaml
   volumes:
     - ./model_configs.yaml:/app/model_configs.yaml:ro
   ```

2. **限制资源使用**
   ```yaml
   deploy:
     resources:
       limits:
         memory: 2G
         cpus: '1.0'
   ```

3. **使用secrets管理敏感信息**
   ```yaml
   secrets:
     - api_key
   ```

## 故障排除命令

```bash
# 停止所有容器
docker-compose down

# 完全清理
docker-compose down -v --remove-orphans
docker system prune -f

# 查看容器状态
docker-compose ps

# 进入容器调试
docker-compose exec pageindex /bin/bash
```
