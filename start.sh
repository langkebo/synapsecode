#!/bin/bash
# Matrix Synapse 极简版快速启动脚本

echo "🚀 Matrix Synapse 极简版快速启动"
echo "=================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用root用户运行此脚本"
    echo "使用: sudo $0"
    exit 1
fi

# 检查文件是否存在
if [ ! -f "deploy-minimal.sh" ]; then
    echo "❌ 找不到 deploy-minimal.sh 文件"
    exit 1
fi

# 检查是否已经部署
if [ -f ".env" ] && docker ps --format "{{.Names}}" | grep -q "matrix-synapse"; then
    echo "✅ Matrix服务已部署"
    echo ""
    echo "📊 当前状态:"
    ./maintain-minimal.sh status
    echo ""
    echo "🔧 可用命令:"
    echo "  ./maintain-minimal.sh status    # 查看状态"
    echo "  ./maintain-minimal.sh logs      # 查看日志"
    echo "  ./maintain-minimal.sh restart   # 重启服务"
    echo "  ./maintain-minimal.sh resources # 查看资源"
    echo ""
    echo "🌐 访问地址:"
    echo "  Matrix服务器: https://$(hostname -f | sed 's/^*\.//'):8008"
    echo "  客户端地址: https://$(hostname -f | sed 's/^*\.//')/"
    echo ""
    echo "📖 更多信息请查看: MINIMAL_DEPLOYMENT.md"
else
    echo "📦 正在部署Matrix服务..."
    echo ""
    echo "⚡ 系统要求:"
    echo "   - CPU: 1核"
    echo "   - 内存: 2GB"
    echo "   - 存储: 10GB"
    echo ""
    read -p "确认继续部署? (y/n): " confirm
    if [ "$confirm" = "y" ]; then
        ./deploy-minimal.sh
    else
        echo "❌ 部署已取消"
    fi
fi