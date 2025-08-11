#!/bin/bash
# Matrix Synapse 极简版一键部署脚本
# 适用于单核CPU 2G内存服务器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查系统资源
check_system() {
    print_info "检查系统资源..."
    
    # 检查内存
    total_mem=$(free -m | awk 'NR==2{printf "%.1f", $2/1024}')
    if (( $(echo "$total_mem < 1.8" | bc -l) )); then
        print_error "内存不足: ${total_mem}GB (至少需要2GB)"
        exit 1
    fi
    print_success "内存: ${total_mem}GB ✓"
    
    # 检查CPU核心数
    cpu_cores=$(nproc)
    if [ "$cpu_cores" -lt 1 ]; then
        print_error "CPU核心数不足: ${cpu_cores} (至少需要1核)"
        exit 1
    fi
    print_success "CPU核心: ${cpu_cores}核 ✓"
    
    # 检查磁盘空间
    disk_space=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')
    if [ "$disk_space" -lt 10 ]; then
        print_error "磁盘空间不足: ${disk_space}GB (至少需要10GB)"
        exit 1
    fi
    print_success "磁盘空间: ${disk_space}GB ✓"
}

# 检查依赖
check_dependencies() {
    print_info "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装"
        print_info "正在安装Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        print_success "Docker安装完成"
    else
        print_success "Docker已安装 ✓"
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose未安装"
        print_info "正在安装Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        print_success "Docker Compose安装完成"
    else
        print_success "Docker Compose已安装 ✓"
    fi
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        print_error "Git未安装"
        print_info "正在安装Git..."
        sudo apt-get update && sudo apt-get install -y git
        print_success "Git安装完成"
    else
        print_success "Git已安装 ✓"
    fi
}

# 创建配置文件
create_config() {
    print_info "创建配置文件..."
    
    # 创建.env文件
    if [ ! -f .env ]; then
        cat > .env << EOF
# 服务器配置
MATRIX_SERVER_NAME=$(hostname -f | sed 's/^*\.//')
MATRIX_DOMAIN=$(hostname -f | sed 's/^*\.//')
ADMIN_EMAIL=admin@$(hostname -f | sed 's/^*\.//')

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
EOF
        print_success ".env文件创建完成"
    else
        print_warning ".env文件已存在，跳过创建"
    fi
    
    # 创建homeserver.yaml
    if [ ! -f config/homeserver.yaml ]; then
        mkdir -p config
        cat > config/homeserver.yaml << EOF
# 极简版 homeserver.yaml
server_name: "\${MATRIX_SERVER_NAME}"
pid_file: /data/homeserver.pid
web_client: false
public_baseurl: https://\${MATRIX_SERVER_NAME}/

# 监听配置
listeners:
  - port: 8008
    tls: false
    bind_addresses: ['0.0.0.0']
    type: http
    x_forwarded: true

    resources:
      - names: [client, federation]
        compress: false

# 数据库配置
database:
  name: psycopg2
  args:
    user: "\${POSTGRES_USER}"
    password: "\${POSTGRES_PASSWORD}"
    database: "\${POSTGRES_DB}"
    host: postgres
    port: 5432
    cp_min: 1
    cp_max: 2

# 日志配置
log_config: "/data/synapse.log.config"

# 媒体存储
media_store_path: "/data/media"

# 性能优化
caches:
  global_factor: 0.2
  event_cache_size: 500

# 注册配置
enable_registration: \${ENABLE_REGISTRATION}
registration_shared_secret: "\${REGISTRATION_SHARED_SECRET}"

# 好友功能
friends:
  enabled: \${FRIENDS_ENABLED}
  max_friends_per_user: \${MAX_FRIENDS_PER_USER}

# 速率限制
rc_registration:
  per_second: 0.17
  burst_count: 3

# 限制最大文件上传大小
max_upload_size: "10M"

# 媒体保留时间
media_retention:
  remote_media_lifetime: "7d"
  local_media_lifetime: "14d"
EOF
        print_success "homeserver.yaml创建完成"
    else
        print_warning "homeserver.yaml已存在，跳过创建"
    fi
    
    # 创建well-known目录
    mkdir -p well-known/.well-known/matrix
    cat > well-known/.well-known/matrix/server << EOF
{
    "m.server": "\${MATRIX_SERVER_NAME}:8008"
}
EOF
    cat > well-known/.well-known/matrix/client << EOF
{
    "m.homeserver": {
        "base_url": "https://\${MATRIX_SERVER_NAME}"
    }
}
EOF
    print_success "well-known配置完成"
}

# 启动服务
start_services() {
    print_info "启动Matrix服务..."
    
    # 停止现有服务
    docker-compose -f docker-compose.minimal.yml down --remove-orphans
    
    # 构建并启动服务
    docker-compose -f docker-compose.minimal.yml up -d --build
    
    # 等待服务启动
    print_info "等待服务启动..."
    sleep 30
    
    # 检查服务状态
    if docker-compose -f docker-compose.minimal.yml ps | grep -q "Up"; then
        print_success "服务启动成功！"
    else
        print_error "服务启动失败"
        docker-compose -f docker-compose.minimal.yml logs
        exit 1
    fi
}

# 生成管理员用户
create_admin() {
    print_info "创建管理员用户..."
    
    # 生成管理员用户
    read -p "请输入管理员用户名: " admin_user
    read -s -p "请输入管理员密码: " admin_pass
    echo
    
    docker-compose -f docker-compose.minimal.yml exec synapse \
        register_new_matrix_user \
        -u "$admin_user" \
        -p "$admin_pass" \
        -a \
        -c /data/homeserver.yaml
    
    print_success "管理员用户 '$admin_user' 创建完成"
}

# 显示访问信息
show_access_info() {
    print_info "访问信息："
    echo "==================================="
    echo "服务器地址: https://$(hostname -f)"
    echo "客户端地址: https://$(hostname -f)/"
    echo "服务器端口: 8008"
    echo ""
    echo "管理命令："
    echo "  查看状态: docker-compose -f docker-compose.minimal.yml ps"
    echo "  查看日志: docker-compose -f docker-compose.minimal.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose.minimal.yml down"
    echo "  重启服务: docker-compose -f docker-compose.minimal.yml restart"
    echo ""
    echo "配置文件："
    echo "  环境变量: .env"
    echo "  主配置: config/homeserver.yaml"
    echo "  Docker配置: docker-compose.minimal.yml"
    echo "==================================="
}

# 主函数
main() {
    echo "=========================================="
    echo "  Matrix Synapse 极简版一键部署脚本"
    echo "  适用于单核CPU 2G内存服务器"
    echo "=========================================="
    echo ""
    
    # 检查是否为root用户
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用root用户运行此脚本"
        echo "使用: sudo $0"
        exit 1
    fi
    
    # 执行部署步骤
    check_system
    check_dependencies
    create_config
    start_services
    
    # 询问是否创建管理员用户
    read -p "是否创建管理员用户? (y/n): " create_admin_user
    if [ "$create_admin_user" = "y" ]; then
        create_admin
    fi
    
    show_access_info
    
    print_success "Matrix服务器部署完成！"
    print_info "请使用客户端连接您的Matrix服务器"
}

# 运行主函数
main "$@"