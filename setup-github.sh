#!/bin/bash
# GitHub代码上传脚本 - Ubuntu Matrix Synapse部署

set -Eeuo pipefail

# 颜色输出函数
print_info() { echo -e "\033[34mℹ️  $1\033[0m"; }
print_success() { echo -e "\033[32m✅ $1\033[0m"; }
print_warning() { echo -e "\033[33m⚠️  $1\033[0m"; }
print_error() { echo -e "\033[31m❌ $1\033[0m"; }

echo "🚀 Matrix Synapse - GitHub代码上传脚本"
echo "======================================"
echo ""

# 预设仓库信息
REPO_NAME="matrix-synapse-ubuntu-server"
REPO_DESC="Matrix Synapse server for Ubuntu - with domain setup, Nginx proxy and SSL"
DEFAULT_BRANCH="main"

print_info "仓库信息："
echo "   名称: $REPO_NAME"
echo "   描述: $REPO_DESC"
echo "   分支: $DEFAULT_BRANCH"
echo ""

# 获取GitHub用户名
if [ -z "${GITHUB_USER:-}" ]; then
    read -p "请输入您的GitHub用户名: " GITHUB_USER
    export GITHUB_USER
fi

GITHUB_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"

# 检查Git配置
if ! git config --global user.name >/dev/null 2>&1; then
    read -p "请输入您的Git用户名: " GIT_NAME
    git config --global user.name "$GIT_NAME"
fi

if ! git config --global user.email >/dev/null 2>&1; then
    read -p "请输入您的Git邮箱: " GIT_EMAIL
    git config --global user.email "$GIT_EMAIL"
fi

# 检查是否已有远程仓库
if git remote -v | grep -q "origin"; then
    print_warning "远程仓库 'origin' 已存在"
    git remote -v
    read -p "是否继续使用现有远程仓库? (y/n): " CONTINUE
    if [[ $CONTINUE != "y" ]]; then
        print_info "正在移除现有远程仓库..."
        git remote remove origin
    fi
fi

# 添加远程仓库（如果不存在）
if ! git remote -v | grep -q "origin"; then
    print_info "添加远程仓库..."
    git remote add origin "$GITHUB_URL"
fi

# 提交所有更改
print_info "准备提交代码..."

# 检查是否有未提交的更改
if ! git diff --quiet || ! git diff --cached --quiet; then
    git add .
    git commit -m "feat: Complete Ubuntu server deployment with domain setup, Nginx proxy, SSL certificates

- Add secure .gitignore to protect secrets
- Configure domain setup with matrix.cjystx.top and cjystx.top
- Add Nginx reverse proxy configuration
- Implement SSL certificate automation with Let's Encrypt
- Update deploy-simple.sh for production deployment
- Add comprehensive Ubuntu server deployment guide
- Configure firewall rules for security
- Add well-known endpoint configuration
- Optimize Docker Compose for production use"
    
    print_success "代码已提交"
else
    print_info "没有新的更改需要提交"
fi

# 推送到GitHub
print_info "推送代码到GitHub..."

if git push -u origin $DEFAULT_BRANCH; then
    print_success "代码成功推送到GitHub！"
    echo ""
    echo "📋 仓库信息："
    echo "   URL: $GITHUB_URL"
    echo "   分支: $DEFAULT_BRANCH"
    echo ""
    echo "🚀 Ubuntu服务器部署命令："
    echo "   git clone $GITHUB_URL"
    echo "   cd $REPO_NAME"
    echo "   sudo ./setup-domain.sh      # 配置域名和SSL"
    echo "   sudo ./deploy-simple.sh     # 部署Matrix服务"
    echo ""
    echo "📖 部署文档："
    echo "   - UBUNTU_SERVER_DEPLOYMENT.md (完整部署指南)"
    echo "   - README.md (项目概述)"
    echo ""
    echo "🎯 服务器配置："
    echo "   Matrix: matrix.cjystx.top"
    echo "   主域名: cjystx.top"
    echo "   邮箱: admin@cjystx.top"
    echo ""
    print_success "部署准备完成！请在Ubuntu服务器上运行部署命令。"
else
    print_error "推送失败！"
    echo ""
    print_info "手动创建GitHub仓库步骤："
    echo "1. 访问 https://github.com/new"
    echo "2. 仓库名称：$REPO_NAME"
    echo "3. 描述：$REPO_DESC"
    echo "4. 设为公开或私有"
    echo "5. 不要初始化README（我们已有）"
    echo "6. 点击'Create repository'"
    echo ""
    echo "然后重新运行此脚本"
    exit 1
fi