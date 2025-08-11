#!/bin/bash
# 完整重新部署脚本 - 清理并重新下载最新代码

echo "🔄 Matrix Synapse 完整重新部署"
echo "================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root用户运行此脚本"
    echo "使用: sudo $0"
    exit 1
fi

# 询问确认
echo "⚠️  这将删除所有现有容器和数据"
read -p "确认继续? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "❌ 部署已取消"
    exit 1
fi

# 停止并删除所有容器
echo "🛑 停止所有容器..."
docker stop $(docker ps -aq) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true

# 删除所有镜像
echo "🗑️ 删除所有镜像..."
docker rmi $(docker images -q) 2>/dev/null || true

# 清理Docker系统
echo "🧹 清理Docker系统..."
docker system prune -a -f
docker volume prune -f
docker network prune -f

# 重启Docker服务
echo "🔄 重启Docker服务..."
systemctl restart docker
sleep 10

# 备份现有项目（如果存在）
if [ -d "synapsecode" ]; then
    echo "💾 备份现有项目..."
    mv synapsecode synapsecode.backup.$(date +%Y%m%d_%H%M%S)
fi

# 重新下载项目
echo "📥 重新下载最新代码..."
git clone https://github.com/langkebo/synapsecode.git
cd synapsecode

# 设置权限
echo "🔐 设置执行权限..."
chmod +x *.sh

# 使用简化版部署
echo "🚀 开始部署..."
./deploy-simple.sh

echo "✅ 重新部署完成！"
echo ""
echo "🔧 管理命令："
echo "  查看状态: docker-compose -f docker-compose.simple.yml ps"
echo "  查看日志: docker-compose -f docker-compose.simple.yml logs -f"
echo "  停止服务: docker-compose -f docker-compose.simple.yml down"