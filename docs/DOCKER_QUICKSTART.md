# PageIndex Docker 快速开始

## 构建镜像

```bash
# 构建Docker镜像 (linux/amd64架构)
./build-docker.sh
```

> **注意**: 构建脚本会自动指定linux/amd64平台，确保在任何环境下都能正常运行。

## 启动服务

### 方法1：使用docker-compose（推荐）

```bash
# 启动服务（会自动使用已构建的镜像）
docker-compose up

# 后台运行
docker-compose up -d
```

### 方法2：直接使用docker run

```bash
# 启动容器
docker run -d \
  --name pageindex-app \
  -p 8501:8501 \
  -v $(pwd)/model_configs.yaml:/app/model_configs.yaml:ro \
  -v $(pwd)/prompt_config.yaml:/app/prompt_config.yaml:ro \
  -v $(pwd)/ocr_files:/app/ocr_files \
  -v $(pwd)/results:/app/results \
  pageindex:latest
```

## 工作流程说明

1. **构建阶段**：`./build-docker.sh` - 负责构建Docker镜像
2. **运行阶段**：`docker-compose up` - 负责运行容器（使用已构建的镜像）

## 访问应用

打开浏览器访问：http://localhost:8501

## 停止服务

```bash
# 停止docker-compose服务
docker-compose down

# 停止单独容器
docker stop pageindex-app
docker rm pageindex-app
```

## 查看日志

```bash
# docker-compose日志
docker-compose logs -f

# 单独容器日志
docker logs -f pageindex-app
```

## 故障排除

1. **端口占用**：修改端口映射 `-p 8502:8501`
2. **权限问题**：确保配置文件和目录有适当权限
3. **构建失败**：检查Docker Desktop是否正常运行

## 详细文档

查看完整部署文档：`docs/DOCKER_DEPLOYMENT.md`
