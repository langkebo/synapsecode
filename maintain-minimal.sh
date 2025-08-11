#!/bin/bash
# Matrix Synapse 极简版验证和维护脚本
# 适用于单核CPU 2G内存服务器

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置文件
COMPOSE_FILE="docker-compose.minimal.yml"
CONFIG_FILE="config/homeserver-minimal.yaml"

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

# 检查服务状态
check_services() {
    print_info "检查服务状态..."
    
    # 检查Docker服务
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker服务未运行"
        exit 1
    fi
    
    # 检查容器状态
    local containers=("matrix-postgres" "matrix-synapse" "matrix-well-known")
    local all_running=true
    
    for container in "${containers[@]}"; do
        if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container.*Up"; then
            print_success "$container ✓"
        else
            print_error "$container ✗"
            all_running=false
        fi
    done
    
    if [ "$all_running" = false ]; then
        print_error "部分服务未运行"
        return 1
    fi
    
    print_success "所有服务运行正常"
}

# 检查资源使用情况
check_resources() {
    print_info "检查资源使用情况..."
    
    # 检查内存使用
    print_info "内存使用情况:"
    docker stats --no-stream --format "table {{.Container}}\t{{.MemUsage}}\t{{.CPUPerc}}"
    
    # 检查磁盘使用
    print_info "磁盘使用情况:"
    df -h .
    
    # 检查容器日志大小
    print_info "容器日志大小:"
    for container in "matrix-postgres" "matrix-synapse" "matrix-well-known"; do
        if docker ps -a --format "{{.Names}}" | grep -q "$container"; then
            local log_size=$(docker logs --tail 0 "$container" 2>&1 | wc -c)
            echo "$container: ${log_size} bytes"
        fi
    done
}

# 检查Synapse健康状态
check_synapse_health() {
    print_info "检查Synapse健康状态..."
    
    # 检查Synapse API
    if docker-compose -f $COMPOSE_FILE exec -T synapse curl -f http://localhost:8008/_matrix/client/versions >/dev/null 2>&1; then
        print_success "Synapse API响应正常 ✓"
    else
        print_error "Synapse API无响应"
        return 1
    fi
    
    # 检查数据库连接
    if docker-compose -f $COMPOSE_FILE exec -T postgres pg_isready -U synapse -d synapse >/dev/null 2>&1; then
        print_success "数据库连接正常 ✓"
    else
        print_error "数据库连接失败"
        return 1
    fi
    
    # 检查well-known配置
    if docker-compose -f $COMPOSE_FILE exec -T well-known curl -f http://localhost/.well-known/matrix/server >/dev/null 2>&1; then
        print_success "Well-known配置正常 ✓"
    else
        print_error "Well-known配置失败"
        return 1
    fi
}

# 清理资源
cleanup_resources() {
    print_info "清理资源..."
    
    # 清理Docker缓存
    docker system prune -f >/dev/null 2>&1
    
    # 清理未使用的镜像
    docker image prune -f >/dev/null 2>&1
    
    # 清理容器日志
    for container in "matrix-postgres" "matrix-synapse" "matrix-well-known"; do
        if docker ps -a --format "{{.Names}}" | grep -q "$container"; then
            docker logs --tail 100 "$container" > "/tmp/${container}_logs.log" 2>&1
            truncate -s 0 "$(docker inspect --format='{{.LogPath}}' "$container")" 2>/dev/null || true
        fi
    done
    
    print_success "资源清理完成"
}

# 重启服务
restart_services() {
    print_info "重启服务..."
    
    docker-compose -f $COMPOSE_FILE restart
    
    print_info "等待服务启动..."
    sleep 20
    
    if check_services >/dev/null 2>&1; then
        print_success "服务重启成功"
    else
        print_error "服务重启失败"
        return 1
    fi
}

# 查看日志
show_logs() {
    local service="$1"
    
    if [ -z "$service" ]; then
        print_info "查看所有服务日志:"
        docker-compose -f $COMPOSE_FILE logs --tail=50
    else
        print_info "查看 $service 日志:"
        docker-compose -f $COMPOSE_FILE logs --tail=50 "$service"
    fi
}

# 备份配置
backup_config() {
    print_info "备份配置..."
    
    local backup_dir="backup/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # 备份配置文件
    cp .env "$backup_dir/" 2>/dev/null || true
    cp -r config "$backup_dir/" 2>/dev/null || true
    cp -r well-known "$backup_dir/" 2>/dev/null || true
    cp "$COMPOSE_FILE" "$backup_dir/" 2>/dev/null || true
    
    # 备份数据库
    docker-compose -f $COMPOSE_FILE exec -T postgres pg_dump -U synapse synapse > "$backup_dir/database.sql" 2>/dev/null || true
    
    print_success "配置已备份到: $backup_dir"
}

# 显示系统信息
show_system_info() {
    print_info "系统信息:"
    echo "================================"
    echo "主机名: $(hostname)"
    echo "操作系统: $(cat /etc/os-release | grep PRETTY_NAME | cut -d= -f2 | tr -d '"')"
    echo "内核版本: $(uname -r)"
    echo "CPU核心: $(nproc)"
    echo "内存总量: $(free -h | awk 'NR==2{print $2}')"
    echo "磁盘空间: $(df -h . | awk 'NR==2{print $4}')"
    echo "Docker版本: $(docker --version)"
    echo "Docker Compose版本: $(docker-compose --version)"
    echo "================================"
}

# 显示帮助信息
show_help() {
    echo "Matrix Synapse 极简版维护脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  status      检查服务状态"
    echo "  health      检查健康状态"
    echo "  resources   检查资源使用"
    echo "  cleanup     清理资源"
    echo "  restart     重启服务"
    echo "  logs [服务] 查看日志"
    echo "  backup      备份配置"
    echo "  info        显示系统信息"
    echo "  help        显示帮助"
    echo ""
    echo "示例:"
    echo "  $0 status"
    echo "  $0 logs synapse"
    echo "  $0 backup"
}

# 主函数
main() {
    local action="${1:-status}"
    
    case "$action" in
        "status")
            check_services
            ;;
        "health")
            check_services && check_synapse_health
            ;;
        "resources")
            check_resources
            ;;
        "cleanup")
            cleanup_resources
            ;;
        "restart")
            restart_services
            ;;
        "logs")
            show_logs "$2"
            ;;
        "backup")
            backup_config
            ;;
        "info")
            show_system_info
            ;;
        "help")
            show_help
            ;;
        *)
            print_error "未知选项: $action"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"