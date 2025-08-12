#!/bin/bash

# 完整的重新部署脚本
# 用于在服务器上重新部署 Matrix Synapse

set -e

echo "=== Matrix Synapse 完整重新部署 ==="
echo

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 root 权限运行此脚本"
    echo "使用: sudo ./redeploy-complete.sh"
    exit 1
fi

# 设置工作目录
WORK_DIR="/opt/synapsecode"
cd "$WORK_DIR"

echo "1. 停止现有服务..."
docker-compose -f docker-compose.minimal.yml down 2>/dev/null || true

echo "2. 拉取最新代码..."
git pull origin main

echo "3. 运行部署前检查..."
./pre-deploy-check.sh

echo "4. 清理 Docker 系统..."
docker system prune -f
docker volume prune -f

echo "5. 配置 Docker 镜像加速..."
mkdir -p /etc/docker
cat > /etc/docker/daemon.json << 'EOF'
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

echo "6. 重启 Docker 服务..."
systemctl daemon-reload
systemctl restart docker
sleep 10

echo "7. 检查 Docker 服务状态..."
if systemctl is-active --quiet docker; then
    echo "✅ Docker 服务运行正常"
else
    echo "❌ Docker 服务启动失败"
    exit 1
fi

echo "8. 拉取基础镜像..."
docker pull postgres:15-alpine
docker pull python:3.9-slim
docker pull nginx:alpine

echo "9. 检查环境变量..."
if [ ! -f ".env" ]; then
    echo "⚠️ .env 文件不存在，运行配置脚本..."
    ./setup-domain.sh
else
    echo "✅ .env 文件已存在"
fi

echo "10. 构建并启动服务..."
docker-compose -f docker-compose.minimal.yml up -d --build

echo "11. 等待服务启动..."
sleep 30

echo "12. 检查服务状态..."
docker-compose -f docker-compose.minimal.yml ps

echo "13. 检查 Synapse 健康状态..."
if docker-compose -f docker-compose.minimal.yml exec -T synapse curl -f http://localhost:8008/_matrix/client/versions >/dev/null 2>&1; then
    echo "✅ Synapse 服务健康"
else
    echo "⚠️ Synapse 服务可能还在启动中"
fi

echo "14. 检查数据库连接..."
if docker-compose -f docker-compose.minimal.yml exec -T postgres pg_isready -U synapse >/dev/null 2>&1; then
    echo "✅ PostgreSQL 数据库连接正常"
else
    echo "❌ PostgreSQL 数据库连接失败"
fi

echo "15. 显示服务日志..."
echo "=== Synapse 服务日志 ==="
docker-compose -f docker-compose.minimal.yml logs --tail=20 synapse

echo
echo "=== 部署完成 ==="
echo
echo "📊 服务状态:"
echo "  查看状态: sudo docker-compose -f docker-compose.minimal.yml ps"
echo "  查看日志: sudo docker-compose -f docker-compose.minimal.yml logs -f"
echo "  停止服务: sudo docker-compose -f docker-compose.minimal.yml down"
echo
echo "🔧 故障排除:"
echo "  运行诊断: sudo ./diagnose.sh"
echo "  重新部署: sudo ./redeploy-complete.sh"
echo
echo "🌐 访问地址:"
echo "  Matrix 服务器: https://$(grep MATRIX_SERVER_NAME .env | cut -d'=' -f2)"
echo "  Well-known 配置: https://$(grep MATRIX_SERVER_NAME .env | cut -d'=' -f2)/.well-known/matrix/server"
echo
echo "📝 注意事项:"
echo "  1. 确保 Nginx 反向代理已正确配置"
echo "  2. 确保 SSL 证书已安装"
echo "  3. 防火墙已开放 443 端口"
echo "  4. DNS 解析已正确配置"