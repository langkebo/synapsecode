#!/bin/bash
# Matrix服务诊断脚本

echo "🔍 Matrix服务诊断"
echo "=================="

# 检查Docker状态
echo "🐳 检查Docker服务..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "❌ Docker服务未运行"
    echo "🔄 尝试启动Docker服务..."
    systemctl start docker
    sleep 5
    if ! docker info &> /dev/null; then
        echo "❌ Docker服务启动失败"
        exit 1
    fi
fi

echo "✅ Docker服务正常"

# 检查Docker Compose
echo "📦 检查Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装"
    exit 1
fi
echo "✅ Docker Compose正常"

# 检查docker-compose文件
echo "📋 检查配置文件..."
if [ ! -f "docker-compose.minimal.yml" ]; then
    echo "❌ docker-compose.minimal.yml不存在"
    exit 1
fi
echo "✅ docker-compose.minimal.yml存在"

# 检查.env文件
if [ ! -f ".env" ]; then
    echo "❌ .env文件不存在"
    echo "📝 请先运行 ./setup-domain.sh 配置域名"
    exit 1
fi
echo "✅ .env文件存在"

# 显示当前配置
echo ""
echo "📊 当前配置："
echo "=================="
cat .env
echo "=================="

# 检查容器状态
echo ""
echo "🏃 检查容器状态..."
docker-compose -f docker-compose.minimal.yml ps

# 检查Docker日志
echo ""
echo "📝 检查Docker系统日志..."
if docker logs $(docker ps -aq --filter "name=matrix-synapse") 2>&1 | grep -q "error"; then
    echo "⚠️ 发现错误日志，详细信息："
    docker logs $(docker ps -aq --filter "name=matrix-synapse") 2>&1 | grep -i error | head -5
else
    echo "✅ 未发现明显错误"
fi

# 检查端口占用
echo ""
echo "🔌 检查端口占用..."
if netstat -tlnp | grep -q ":8008"; then
    echo "⚠️ 端口8008已被占用"
    netstat -tlnp | grep ":8008"
else
    echo "✅ 端口8008可用"
fi

if netstat -tlnp | grep -q ":5432"; then
    echo "⚠️ 端口5432已被占用"
    netstat -tlnp | grep ":5432"
else
    echo "✅ 端口5432可用"
fi

# 检查磁盘空间
echo ""
echo "💾 检查磁盘空间..."
df -h | grep -E "(\/$|\/var)"

# 检查内存
echo ""
echo "🧠 检查内存使用..."
free -h

# 建议解决方案
echo ""
echo "🔧 建议的解决方案："
echo "=================="
echo "1. 如果容器未运行："
echo "   docker-compose -f docker-compose.minimal.yml down"
echo "   docker-compose -f docker-compose.minimal.yml up -d --build"
echo ""
echo "2. 如果端口被占用："
echo "   停止占用端口的程序或修改docker-compose中的端口映射"
echo ""
echo "3. 如果配置文件问题："
echo "   运行 ./setup-domain.sh 重新配置域名"
echo ""
echo "4. 如果Docker问题："
echo "   运行 ./docker-cleanup.sh 清理Docker环境"