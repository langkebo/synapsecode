#\!/bin/bash
# Docker清理脚本 - 解决文件系统问题

echo "🧹 清理Docker缓存和临时文件..."

# 停止所有容器
echo "🛑 停止所有Docker容器..."
docker stop $(docker ps -aq) 2>/dev/null || true

# 清理未使用的资源
echo "🗑️ 清理未使用的Docker资源..."
docker system prune -f

# 清理所有镜像（强制重新下载）
echo "🔄 清理所有Docker镜像..."
docker image prune -a -f

# 清理卷积
echo "📦 清理未使用的Docker卷积..."
docker volume prune -f

# 清理构建缓存
echo "🏗️ 清理Docker构建缓存..."
docker builder prune -f

# 重启Docker服务
echo "🔄 重启Docker服务..."
systemctl restart docker

echo "⏳ 等待Docker服务启动..."
sleep 10

echo "✅ Docker清理完成！"
echo ""
echo "🚀 现在可以重新部署："
echo "   sudo ./deploy-minimal.sh"
