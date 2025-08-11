# Matrix Server 部署指南 - 生产环境

## 概述

本指南提供了在Ubuntu服务器上部署Matrix Synapse服务器的完整流程，包含我们自定义的好友功能。

## 系统要求

### 最低配置（推荐）
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 50GB SSD
- **网络**: 公网IP，带宽10Mbps+
- **操作系统**: Ubuntu 20.04/22.04 LTS

### 推荐配置
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 100GB SSD
- **网络**: 公网IP，带宽50Mbps+

## 快速部署

### 1. 系统准备

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装Docker和Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo systemctl enable docker

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# 配置防火墙
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 81/tcp
sudo ufw reload
```

### 2. 项目部署

```bash
# 创建项目目录
sudo mkdir -p /opt/matrix-server
sudo chown $USER:$USER /opt/matrix-server
cd /opt/matrix-server

# 上传项目文件
# 使用SFTP工具将以下文件上传到服务器：
# - pyproject.toml
# - Dockerfile
# - docker-compose.yml
# - 整个synapsecode目录
# - docker/ 目录及其内容

# 创建必要目录
mkdir -p well-known/matrix
mkdir -p docker/{postgres,nginx,grafana,prometheus,synapse}

# 复制环境配置文件
cp .env.example .env
chmod 600 .env
```

### 3. 配置环境变量

编辑 `.env` 文件：

```bash
nano .env
```

修改以下关键配置：
- `MATRIX_SERVER_NAME`: 您的Matrix服务器域名
- `MATRIX_DOMAIN`: 您的主域名
- `ADMIN_EMAIL`: 管理员邮箱
- 生成安全密钥：`openssl rand -base64 32`

### 4. 创建Well-known配置

```bash
# 创建服务器发现文件
cat > well-known/matrix/server << EOF
{
  "m.server": "${MATRIX_SERVER_NAME}:443"
}
EOF

# 创建客户端发现文件
cat > well-known/matrix/client << EOF
{
  "m.homeserver": {
    "base_url": "https://${MATRIX_SERVER_NAME}"
  },
  "m.identity_server": {
    "base_url": "https://vector.im"
  }
}
EOF
```

### 5. 启动服务

```bash
# 启动基础服务
docker-compose up -d postgres redis

# 等待数据库就绪
sleep 30

# 启动Synapse
docker-compose up -d --build synapse

# 启动其他服务
docker-compose up -d nginx-proxy-manager well-known

# 检查服务状态
docker-compose ps
```

### 6. 配置Nginx Proxy Manager

1. 访问管理界面：`http://your-server-ip:81`
2. 默认登录：`admin@example.com` / `changeme`
3. 配置代理主机：

**Matrix服务器代理:**
- Domain Names: `matrix.yourdomain.com`
- Scheme: `http`
- Forward Hostname/IP: `matrix-synapse`
- Forward Port: `8008`
- Enable SSL: 申请Let's Encrypt证书
- Enable Websocket Support: ✓

**Well-known服务代理:**
- Domain Names: `yourdomain.com`
- Scheme: `http`
- Forward Hostname/IP: `matrix-well-known`
- Forward Port: `80`
- Enable SSL: 申请Let's Encrypt证书

### 7. 生成Synapse配置

```bash
# 生成初始配置
docker-compose exec synapse python -m synapse.app.homeserver \
  --server-name=${MATRIX_SERVER_NAME} \
  --config-path=/data/homeserver.yaml \
  --generate-config \
  --report-stats=${REPORT_STATS}

# 创建优化的配置文件
docker-compose exec synapse tee /data/homeserver.yaml > /dev/null << 'EOF'
# 基础配置
server_name: "${MATRIX_SERVER_NAME}"
pid_file: /data/homeserver.pid
web_client_location: https://app.element.io/
public_baseurl: "https://${MATRIX_SERVER_NAME}/"

# 监听配置
listeners:
  - port: 8008
    tls: false
    type: http
    x_forwarded: true
    bind_addresses: ['0.0.0.0']
    resources:
      - names: [client, federation]
        compress: false

# 数据库配置
database:
  name: psycopg2
  args:
    user: "${POSTGRES_USER}"
    password: "${POSTGRES_PASSWORD}"
    database: "${POSTGRES_DB}"
    host: postgres
    port: 5432
    cp_min: 5
    cp_max: 10
    keepalives_idle: 10
    keepalives_interval: 5
    keepalives_count: 3

# Redis缓存配置
redis:
  enabled: true
  host: redis
  port: 6379

# 事件持久化配置
event_persistence:
  background_updates: true

# 缓存配置
caches:
  global_factor: ${SYNAPSE_CACHE_FACTOR}
  event_cache_size: ${SYNAPSE_EVENT_CACHE_SIZE}

# 日志配置
log_config: "/data/${MATRIX_SERVER_NAME}.log.config"

# 媒体存储
media_store_path: "/media"
max_upload_size: "${MAX_UPLOAD_SIZE}"
media_retention:
  local_media_lifetime: 30d
  remote_media_lifetime: 30d

# 注册配置
enable_registration: ${ENABLE_REGISTRATION}
registration_shared_secret: "${REGISTRATION_SHARED_SECRET}"

# 密钥配置
macaroon_secret_key: "${MACAROON_SECRET_KEY}"
form_secret: "${FORM_SECRET}"

# 好友功能配置
friends:
  enabled: ${FRIENDS_ENABLED}
  max_friends_per_user: ${MAX_FRIENDS_PER_USER}
  friend_request_timeout: ${FRIEND_REQUEST_TIMEOUT}
  rate_limiting:
    max_requests_per_hour: ${FRIEND_RATE_LIMIT_REQUESTS_PER_HOUR}
    rate_limit_window: ${FRIEND_RATE_LIMIT_WINDOW}
  allow_cross_domain_friends: true

# 隐私配置
enable_presence: true
allow_device_name_lookup: true

# 联邦配置
federation_domain_whitelist: []

# 统计配置
report_stats: ${REPORT_STATS}

# URL预览配置
url_preview_enabled: false

# 性能优化
stream_writers:
  events:
    writers:
      - type: directory
        path: /data/events
        max_file_size: 512MB
        max_files: 5
EOF

# 重启Synapse应用配置
docker-compose restart synapse
```

### 8. 创建管理员用户

```bash
# 创建管理员用户
docker-compose exec synapse register_new_matrix_user \
  -c /data/homeserver.yaml \
  -a \
  http://localhost:8008
```

### 9. 验证部署

```bash
# 健康检查脚本
cat > health-check.sh << 'EOF'
#!/bin/bash

# 检查服务可用性
check_service() {
    if ! curl -f -s $1 > /dev/null; then
        echo "❌ 服务不可用: $1"
        return 1
    fi
    echo "✅ 服务可用: $1"
}

echo "🔍 开始健康检查..."

# 检查服务
check_service "https://${MATRIX_SERVER_NAME}/_matrix/client/versions"
check_service "https://${MATRIX_DOMAIN}/.well-known/matrix/server"

echo "✅ 健康检查完成"
EOF

chmod +x health-check.sh
./health-check.sh
```

## 高级配置

### 启用监控（可选）

```bash
# 启动监控服务
docker-compose --profile monitoring up -d prometheus grafana

# 访问Grafana: http://your-server-ip:3000
# 默认用户: admin / ${GRAFANA_PASSWORD}
```

### 备份配置

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/matrix-server/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec -T postgres pg_dump -U ${POSTGRES_USER} -d ${POSTGRES_DB} > $BACKUP_DIR/postgres_$DATE.sql

# 备份配置文件
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
  .env \
  docker-compose.yml \
  well-known/ \
  docker/

# 备份数据目录
tar -czf $BACKUP_DIR/data_$DATE.tar.gz \
  synapse_data/ \
  synapse_media/

# 清理旧备份（保留7天）
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "备份完成: $BACKUP_DIR"
EOF

chmod +x backup.sh

# 设置定时备份
echo "0 2 * * * /opt/matrix-server/backup.sh" | crontab -
```

### 性能优化

```bash
# 系统优化
sudo tee /etc/sysctl.d/99-matrix.conf << EOF
# 增加文件描述符限制
fs.file-max = 65536

# 网络参数优化
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 120
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.tcp_syncookies = 1
net.ipv4.ip_local_port_range = 1024 65535
EOF

sudo sysctl -p /etc/sysctl.d/99-matrix.conf

# 限制资源使用
sudo tee /etc/security/limits.conf << EOF
* soft nofile 65536
* hard nofile 65536
* soft nproc 4096
* hard nproc 8192
EOF
```

## 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   docker-compose logs synapse
   docker-compose logs postgres
   ```

2. **数据库连接问题**
   ```bash
   docker-compose exec postgres pg_isready
   ```

3. **内存不足**
   ```bash
   free -h
   docker stats
   ```

4. **SSL证书问题**
   ```bash
   docker-compose logs nginx-proxy-manager
   ```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f synapse
docker-compose logs -f postgres

# 查看最近的日志
docker-compose logs --tail=100 synapse
```

### 重置部署（谨慎操作）

```bash
# 停止服务
docker-compose down

# 备份数据
./backup.sh

# 清理数据（会删除所有数据）
sudo rm -rf synapse_data synapse_media postgres_data redis_data

# 重新初始化
docker-compose up -d
```

## 安全建议

1. **定期更新**
   ```bash
   # 更新Docker镜像
   docker-compose pull
   docker-compose up -d
   ```

2. **防火墙配置**
   ```bash
   # 只开放必要端口
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw allow 81/tcp
   sudo ufw enable
   ```

3. **监控设置**
   - 设置日志监控
   - 配置性能告警
   - 定期检查安全更新

4. **备份策略**
   - 每日自动备份
   - 异地备份存储
   - 定期测试恢复

## 性能调优

### 根据服务器规模调整

**小型服务器（1-2核，2-4GB内存）**
- 减少 `max_connections` 到 50
- 减少 `SYNAPSE_CACHE_FACTOR` 到 0.5
- 减少 `SYNAPSE_EVENT_CACHE_SIZE` 到 5000

**中型服务器（4核，8GB内存）**
- 使用默认配置
- 启用Redis缓存
- 考虑启用监控

**大型服务器（8核+，16GB+内存）**
- 增加 `max_connections` 到 200
- 增加 `SYNAPSE_CACHE_FACTOR` 到 2.0
- 启用所有监控组件
- 考虑负载均衡

## 总结

这个部署方案提供了：
- ✅ 完整的Matrix服务器功能
- ✅ 自定义好友功能
- ✅ 生产级别的安全性
- ✅ 监控和备份支持
- ✅ 可扩展的架构

适合个人使用到中型团队的Matrix服务器部署需求。