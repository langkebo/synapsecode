#!/bin/bash
# Matrix服务器域名配置脚本 - Ubuntu服务器版
# 自动配置域名、Nginx反向代理和SSL证书

set -Eeuo pipefail

# 错误处理
trap 'echo "❌ 脚本在第 ${LINENO} 行出错，正在退出" >&2' ERR

# 颜色输出函数
print_info() { echo -e "\033[34mℹ️  $1\033[0m"; }
print_success() { echo -e "\033[32m✅ $1\033[0m"; }
print_warning() { echo -e "\033[33m⚠️  $1\033[0m"; }
print_error() { echo -e "\033[31m❌ $1\033[0m"; }

echo "============================================"
echo "🌐 Matrix服务器域名配置脚本 - Ubuntu服务器版"
echo "============================================"
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    print_error "请使用root用户运行此脚本"
    echo "使用: sudo $0"
    exit 1
fi

# 预设域名配置（避免交互输入）
MATRIX_DOMAIN="matrix.cjystx.top"
MAIN_DOMAIN="cjystx.top"
ADMIN_EMAIL="admin@cjystx.top"

print_info "使用预设域名配置："
echo "   Matrix服务器: $MATRIX_DOMAIN"
echo "   主域名: $MAIN_DOMAIN"
echo "   管理员邮箱: $ADMIN_EMAIL"
echo ""

#-----------------------------
# 系统依赖安装
#-----------------------------
print_info "安装系统依赖..."

# 更新系统
apt-get update -y

# 安装基础依赖
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    nginx certbot python3-certbot-nginx \
    openssl curl wget jq \
    ca-certificates gnupg lsb-release

print_success "系统依赖安装完成"

#-----------------------------
# 环境配置文件
#-----------------------------
print_info "生成环境配置文件..."

# 备份现有.env文件
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    print_info "已备份现有.env文件"
fi

# 生成新的.env文件
cat > .env << EOF
# 服务器配置
MATRIX_SERVER_NAME=${MATRIX_DOMAIN}
MATRIX_DOMAIN=${MAIN_DOMAIN}
ADMIN_EMAIL=${ADMIN_EMAIL}

# 功能开关
ENABLE_REGISTRATION=false
FRIENDS_ENABLED=true
MAX_FRIENDS_PER_USER=100

# 数据库配置
POSTGRES_USER=synapse
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=synapse

# 安全密钥
REGISTRATION_SHARED_SECRET=$(openssl rand -base64 32)
MACAROON_SECRET_KEY=$(openssl rand -base64 32)
FORM_SECRET=$(openssl rand -base64 32)

# 统计报告
REPORT_STATS=no

# Docker配置
SYNAPSE_CONFIG_PATH=/data/homeserver.yaml
EOF

print_success ".env文件生成完成"

#-----------------------------
# Well-known配置
#-----------------------------
print_info "生成well-known配置..."

mkdir -p well-known/.well-known/matrix

# 服务器发现配置
cat > well-known/.well-known/matrix/server << EOF
{
    "m.server": "${MATRIX_DOMAIN}:443"
}
EOF

# 客户端发现配置
cat > well-known/.well-known/matrix/client << EOF
{
    "m.homeserver": {
        "base_url": "https://${MATRIX_DOMAIN}"
    },
    "m.identity_server": {
        "base_url": "https://vector.im"
    }
}
EOF

print_success "well-known配置完成"

#-----------------------------
# Nginx配置
#-----------------------------
print_info "配置Nginx反向代理..."

# 创建Matrix服务器的Nginx配置
cat > /etc/nginx/sites-available/${MATRIX_DOMAIN} << EOF
# Matrix服务器配置 - ${MATRIX_DOMAIN}
server {
    listen 80;
    server_name ${MATRIX_DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${MATRIX_DOMAIN};

    # SSL配置 (将由certbot自动配置)
    ssl_certificate /etc/letsencrypt/live/${MATRIX_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${MATRIX_DOMAIN}/privkey.pem;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 安全头部
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    
    # 客户端最大请求大小
    client_max_body_size 50M;
    
    # Matrix API代理
    location ~ ^(/_matrix|/_synapse/client) {
        proxy_pass http://localhost:8008;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Host \$host;
        
        # 客户端缓冲
        client_body_buffer_size 25M;
        client_max_body_size 50M;
        proxy_max_temp_file_size 0;
        
        # 超时设置
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
    
    # 健康检查
    location /_matrix/client/versions {
        proxy_pass http://localhost:8008;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Host \$host;
    }
}
EOF

# 创建主域名的Nginx配置（用于well-known）
cat > /etc/nginx/sites-available/${MAIN_DOMAIN} << EOF
# 主域名配置 - ${MAIN_DOMAIN}
server {
    listen 80;
    server_name ${MAIN_DOMAIN};
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ${MAIN_DOMAIN};

    # SSL配置 (将由certbot自动配置)
    ssl_certificate /etc/letsencrypt/live/${MAIN_DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${MAIN_DOMAIN}/privkey.pem;
    
    # SSL安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Well-known配置
    location /.well-known/matrix/ {
        root /var/www/matrix-well-known;
        default_type application/json;
        add_header Access-Control-Allow-Origin *;
    }
    
    # 根目录（可选）
    location / {
        return 200 'Matrix Server Active';
        add_header Content-Type text/plain;
    }
}
EOF

# 启用站点配置
ln -sf /etc/nginx/sites-available/${MATRIX_DOMAIN} /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/${MAIN_DOMAIN} /etc/nginx/sites-enabled/

# 测试Nginx配置
nginx -t

print_success "Nginx配置完成"

#-----------------------------
# Well-known文件部署
#-----------------------------
print_info "部署well-known文件到Nginx目录..."

# 创建well-known目录
mkdir -p /var/www/matrix-well-known/.well-known/matrix

# 复制well-known文件
cp -r well-known/.well-known/matrix/* /var/www/matrix-well-known/.well-known/matrix/

# 设置权限
chown -R www-data:www-data /var/www/matrix-well-known
chmod -R 755 /var/www/matrix-well-known

print_success "well-known文件部署完成"

#-----------------------------
# SSL证书配置
#-----------------------------
print_info "配置SSL证书..."

# 重启Nginx以应用初始配置
systemctl reload nginx

print_warning "准备申请SSL证书..."
print_info "请确保以下域名的DNS已正确指向此服务器："
echo "   - ${MATRIX_DOMAIN}"
echo "   - ${MAIN_DOMAIN}"
echo ""

# 申请SSL证书
print_info "申请SSL证书（这可能需要几分钟）..."

# 为Matrix域名申请证书
if certbot --nginx -d ${MATRIX_DOMAIN} --non-interactive --agree-tos --email ${ADMIN_EMAIL} --redirect; then
    print_success "Matrix域名SSL证书申请成功"
else
    print_warning "Matrix域名SSL证书申请失败，请检查DNS配置"
fi

# 为主域名申请证书
if certbot --nginx -d ${MAIN_DOMAIN} --non-interactive --agree-tos --email ${ADMIN_EMAIL} --redirect; then
    print_success "主域名SSL证书申请成功"
else
    print_warning "主域名SSL证书申请失败，请检查DNS配置"
fi

# 设置证书自动更新
systemctl enable certbot.timer

print_success "SSL证书配置完成"

#-----------------------------
# 更新docker-compose配置
#-----------------------------
print_info "更新docker-compose配置以适配生产环境..."

# 更新docker-compose.simple.yml以移除端口暴露（通过Nginx代理）
if [ -f docker-compose.simple.yml ]; then
    cp docker-compose.simple.yml docker-compose.simple.yml.backup
    
    # 移除synapse的端口映射，只保留内部网络通信
    sed -i 's/- "8008:8008"/# - "8008:8008"  # 通过Nginx代理/' docker-compose.simple.yml
    
    print_success "docker-compose配置已更新"
fi

#-----------------------------
# 防火墙配置
#-----------------------------
print_info "配置防火墙规则..."

# 检查ufw是否安装
if command -v ufw >/dev/null 2>&1; then
    # 允许SSH、HTTP、HTTPS
    ufw --force enable
    ufw allow 22/tcp    # SSH
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    ufw reload
    
    print_success "防火墙规则配置完成"
else
    print_warning "ufw未安装，请手动配置防火墙"
fi

#-----------------------------
# 完成配置
#-----------------------------
systemctl reload nginx

print_success "域名配置完成！"
echo ""
echo "🎯 配置信息："
echo "   Matrix服务器: https://${MATRIX_DOMAIN}"
echo "   主域名: https://${MAIN_DOMAIN}"
echo "   管理员邮箱: ${ADMIN_EMAIL}"
echo "   Well-known: https://${MAIN_DOMAIN}/.well-known/matrix/"
echo ""
echo "📋 下一步操作："
echo "   1. 验证DNS解析: nslookup ${MATRIX_DOMAIN}"
echo "   2. 测试well-known: curl https://${MAIN_DOMAIN}/.well-known/matrix/server"
echo "   3. 部署Matrix服务: ./deploy-simple.sh"
echo "   4. 创建管理员用户"
echo ""
echo "🔧 管理命令："
echo "   查看Nginx状态: systemctl status nginx"
echo "   查看SSL证书: certbot certificates"
echo "   更新证书: certbot renew"
echo "   查看防火墙: ufw status"
echo ""
echo "✅ 配置完成！现在可以运行部署脚本了。"