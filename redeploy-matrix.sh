#\!/bin/bash
# Matrix重新部署脚本

echo "🚀 Matrix重新部署..."

# 停止现有服务
echo "🛑 停止现有Matrix服务..."
docker-compose -f docker-compose.minimal.yml down --remove-orphans

# 等待完全停止
sleep 5

# 清理相关镜像
echo "🗑️ 清理Matrix相关镜像..."
docker images | grep -E "(matrix|synapse|postgres)" | awk '{print $3}' | xargs -r docker rmi -f

# 重新部署
echo "🏗️ 重新部署Matrix服务..."
docker-compose -f docker-compose.minimal.yml up -d --build

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose -f docker-compose.minimal.yml ps

echo "✅ Matrix重新部署完成！"
