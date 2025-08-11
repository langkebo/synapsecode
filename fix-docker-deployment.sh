#!/bin/bash

# Docker deployment fix script
# 解决Docker镜像下载问题的部署脚本

set -e

echo "=== Matrix Synapse Docker 部署修复脚本 ==="
echo

# 检查Docker状态
echo "1. 检查Docker状态..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker服务未运行，请启动Docker服务"
    exit 1
fi
echo "✅ Docker服务正常运行"

# 检查docker-compose
echo "2. 检查docker-compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose未安装"
    exit 1
fi
echo "✅ docker-compose已安装"

# 清理Docker系统
echo "3. 清理Docker系统..."
sudo docker system prune -f
sudo docker volume prune -f

# 配置Docker镜像加速器
echo "4. 配置Docker镜像加速器..."
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ],
  "max-concurrent-downloads": 3,
  "max-concurrent-uploads": 5
}
EOF

# 重启Docker服务
echo "5. 重启Docker服务..."
sudo systemctl daemon-reload
sudo systemctl restart docker
sudo systemctl enable docker

echo "6. 等待Docker服务启动..."
sleep 10

# 检查Docker服务状态
if sudo systemctl is-active --quiet docker; then
    echo "✅ Docker服务重启成功"
else
    echo "❌ Docker服务重启失败"
    exit 1
fi

# 拉取基础镜像
echo "7. 拉取基础镜像..."
sudo docker pull postgres:15-alpine
sudo docker pull python:3.9-slim
sudo docker pull nginx:alpine

echo "8. 检查镜像..."
sudo docker images

echo "9. 开始部署Matrix Synapse..."
sudo docker-compose -f docker-compose.minimal.yml down
sudo docker-compose -f docker-compose.minimal.yml up -d --build

echo "10. 检查服务状态..."
sleep 30
sudo docker-compose -f docker-compose.minimal.yml ps

echo "11. 检查服务日志..."
sudo docker-compose -f docker-compose.minimal.yml logs --tail=20 synapse

echo
echo "=== 部署完成 ==="
echo "查看服务状态: sudo docker-compose -f docker-compose.minimal.yml ps"
echo "查看服务日志: sudo docker-compose -f docker-compose.minimal.yml logs -f"
echo "停止服务: sudo docker-compose -f docker-compose.minimal.yml down"