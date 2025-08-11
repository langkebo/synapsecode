#!/bin/bash
# Matrix Synapse 极简版验证脚本

echo "🔍 Matrix Synapse 极简版验证"
echo "=============================="

# 检查极简版文件
MINIMAL_FILES=(
    "docker-compose.minimal.yml"
    "Dockerfile.minimal"
    "deploy-minimal.sh"
    "maintain-minimal.sh"
    "start.sh"
    "config/homeserver-minimal.yaml"
    ".env.minimal"
    "MINIMAL_DEPLOYMENT.md"
)

echo "📋 检查极简版文件..."
for file in "${MINIMAL_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        if [[ -x "$file" ]]; then
            echo "✅ $file (executable)"
        else
            echo "✅ $file"
        fi
    else
        echo "❌ $file - MISSING"
    fi
done

# 检查资源优化配置
echo ""
echo "⚡ 检查资源优化配置..."

# 检查docker-compose.minimal.yml中的资源限制
if [[ -f "docker-compose.minimal.yml" ]]; then
    echo "🐳 检查Docker资源配置..."
    
    # PostgreSQL内存限制
    pg_mem=$(grep -A 10 "postgres:" docker-compose.minimal.yml | grep "memory:" | head -1 | awk '{print $2}')
    echo "   PostgreSQL内存限制: $pg_mem"
    
    # Synapse内存限制
    syn_mem=$(grep -A 15 "synapse:" docker-compose.minimal.yml | grep "memory:" | head -1 | awk '{print $2}')
    echo "   Synapse内存限制: $syn_mem"
    
    # Well-known内存限制
    wk_mem=$(grep -A 10 "well-known:" docker-compose.minimal.yml | grep "memory:" | head -1 | awk '{print $2}')
    echo "   Well-known内存限制: $wk_mem"
fi

# 检查homeserver-minimal.yaml配置
if [[ -f "config/homeserver-minimal.yaml" ]]; then
    echo ""
    echo "⚙️ 检查Synapse性能配置..."
    
    # 缓存因子
    cache_factor=$(grep "global_factor:" config/homeserver-minimal.yaml | awk '{print $2}')
    echo "   缓存因子: $cache_factor"
    
    # 事件缓存
    event_cache=$(grep "event_cache_size:" config/homeserver-minimal.yaml | head -1 | awk '{print $2}')
    echo "   事件缓存: $event_cache"
    
    # 好友数量限制
    max_friends=$(grep "max_friends_per_user:" config/homeserver-minimal.yaml | awk '{print $2}')
    echo "   好友数量限制: $max_friends"
fi

# 显示部署命令
echo ""
echo "🚀 部署命令："
echo "   快速启动: sudo ./start.sh"
echo "   手动部署: sudo ./deploy-minimal.sh"
echo "   维护命令: ./maintain-minimal.sh [status|health|resources]"

# 显示预期资源使用
echo ""
echo "📊 预期资源使用："
echo "   总内存: ~1.5GB"
echo "   总CPU: ~1核"
echo "   存储空间: ~10GB"
echo "   适用用户: 1-3人"

echo ""
echo "=============================="
echo "✅ 极简版验证完成！"
echo ""
echo "🎯 推荐用于单核CPU 2G内存服务器"