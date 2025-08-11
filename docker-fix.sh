#\!/bin/bash
# Docker文件系统修复脚本

echo "🔧 修复Docker文件系统问题..."

# 检查Docker服务状态
echo "📊 检查Docker服务状态..."
systemctl status docker --no-pager

# 清理Docker数据目录（谨慎使用）
echo "⚠️ 清理Docker临时文件..."
rm -rf /var/lib/docker/tmp/* 2>/dev/null || true

# 重新创建Docker网络
echo "🌐 重新创建Docker网络..."
docker network prune -f

# 检查磁盘空间
echo "💾 检查磁盘空间..."
df -h | grep -E "(\/$|\/var)"

# 验证Docker功能
echo "🧪 测试Docker功能..."
docker run --rm hello-world 2>/dev/null || {
    echo "❌ Docker功能测试失败"
    echo "🔄 正在重启Docker服务..."
    systemctl restart docker
    sleep 15
    docker run --rm hello-world 2>/dev/null || {
        echo "❌ Docker仍有问题，建议重启服务器"
        exit 1
    }
}

echo "✅ Docker修复完成！"
