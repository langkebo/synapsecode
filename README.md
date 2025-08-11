# Matrix Synapse with Friends Functionality

一个基于Matrix Synapse的自定义服务器实现，包含完整的好友管理功能。

## 功能特性

### 核心功能
- ✅ 完整的Matrix协议支持
- ✅ 联邦通信（与其他Matrix服务器互通）
- ✅ 端到端加密
- ✅ 文件分享和媒体存储
- ✅ 房间管理
- ✅ 用户认证和授权

### 好友功能（自定义）
- ✅ 好友请求发送和响应
- ✅ 好友列表管理
- ✅ 用户搜索（用于添加好友）
- ✅ 用户屏蔽/取消屏蔽
- ✅ 跨域好友支持
- ✅ 好友状态管理
- ✅ 速率限制保护

### 技术特性
- 🐳 Docker容器化部署
- 📊 Prometheus + Grafana监控
- 🗄️ PostgreSQL数据库
- 🚀 Redis缓存
- 🔐 SSL/TLS支持
- 📈 性能优化
- 🔄 自动备份

## 系统要求

### 最低配置
- **CPU**: 2核心
- **内存**: 4GB RAM
- **存储**: 50GB SSD
- **网络**: 公网IP，带宽10Mbps+

### 推荐配置
- **CPU**: 4核心
- **内存**: 8GB RAM
- **存储**: 100GB SSD
- **网络**: 公网IP，带宽50Mbps+

## 快速开始

### 一键部署

```bash
# 下载项目
git clone https://github.com/yourusername/synapse-friends.git
cd synapse-friends

# 运行一键部署脚本
sudo ./deploy.sh
```

按照脚本提示完成配置即可。

### 手动部署

1. **系统准备**
```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

2. **项目配置**
```bash
# 复制环境配置
cp .env.example .env
nano .env  # 修改配置

# 启动服务
docker-compose up -d
```

3. **配置Nginx Proxy Manager**
   - 访问 `http://your-ip:81`
   - 配置反向代理和SSL证书

## 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `MATRIX_SERVER_NAME` | Matrix服务器域名 | - |
| `MATRIX_DOMAIN` | 主域名 | - |
| `ADMIN_EMAIL` | 管理员邮箱 | - |
| `ENABLE_REGISTRATION` | 是否开放注册 | `false` |
| `FRIENDS_ENABLED` | 启用好友功能 | `true` |
| `MAX_FRIENDS_PER_USER` | 每用户最大好友数 | `1000` |
| `FRIEND_REQUEST_TIMEOUT` | 好友请求超时时间 | `604800` |

### 好友功能配置

```yaml
friends:
  enabled: true
  max_friends_per_user: 1000
  friend_request_timeout: 604800
  rate_limiting:
    max_requests_per_hour: 10
    rate_limit_window: 3600
  allow_cross_domain_friends: true
```

## API文档

### 好友管理API

#### 发送好友请求
```http
POST /_matrix/client/r0/friends/request
{
  "user_id": "@target:example.com",
  "message": "Hello, let's be friends!"
}
```

#### 响应好友请求
```http
POST /_matrix/client/r0/friends/request/{request_id}/response
{
  "accept": true
}
```

#### 获取好友列表
```http
GET /_matrix/client/r0/friends
```

#### 搜索用户
```http
GET /_matrix/client/r0/friends/search?q=search_term&limit=10
```

#### 屏蔽用户
```http
POST /_matrix/client/r0/friends/block
{
  "user_id": "@target:example.com"
}
```

## 架构设计

### 系统架构
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx Proxy   │    │   Matrix Synapse│    │   PostgreSQL    │
│    Manager      │◄──►│     Server      │◄──►│    Database     │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │  SSL/TLS    │ │    │ │  Friends    │ │    │ │   Friends   │ │
│ │   Proxy     │ │    │ │  Handler    │ │    │ │   Tables    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │     Redis      │
                    │     Cache      │
                    └─────────────────┘
```

### 数据库表结构

#### 好友关系表
```sql
CREATE TABLE user_friendships (
    user1_id TEXT NOT NULL,
    user2_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_ts BIGINT NOT NULL,
    PRIMARY KEY (user1_id, user2_id)
);
```

#### 好友请求表
```sql
CREATE TABLE friend_requests (
    request_id TEXT PRIMARY KEY,
    sender_user_id TEXT NOT NULL,
    target_user_id TEXT NOT NULL,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_ts BIGINT NOT NULL,
    updated_ts BIGINT NOT NULL
);
```

#### 用户屏蔽表
```sql
CREATE TABLE user_blocks (
    blocker_user_id TEXT NOT NULL,
    blocked_user_id TEXT NOT NULL,
    created_ts BIGINT NOT NULL,
    PRIMARY KEY (blocker_user_id, blocked_user_id)
);
```

## 开发指南

### 环境设置

```bash
# 安装Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安装依赖
poetry install

# 启动开发环境
poetry run python -m synapse.app.homeserver
```

### 代码结构

```
synapsecode/
├── synapse/
│   ├── handlers/
│   │   └── friends.py          # 好友功能处理器
│   ├── storage/
│   │   └── databases/
│   │       └── main/
│   │           └── friends.py  # 好友数据存储
│   ├── rest/
│   │   └── client/
│   │       └── friends.py      # 好友API端点
│   └── config/
│       └── friends.py          # 好友功能配置
├── docker/                     # Docker配置
├── tests/                      # 测试文件
└── docs/                       # 文档
```

### 添加新功能

1. **Handler层**: 在 `handlers/friends.py` 中添加业务逻辑
2. **Storage层**: 在 `storage/databases/main/friends.py` 中添加数据操作
3. **API层**: 在 `rest/client/friends.py` 中添加API端点
4. **配置**: 在 `config/friends.py` 中添加配置选项

## 监控和维护

### 健康检查

```bash
# 运行健康检查
./health-check.sh

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f synapse
```

### 备份和恢复

```bash
# 手动备份
./backup.sh

# 恢复备份
docker-compose exec -T postgres psql -U synapse -d synapse < backup/postgres_YYYYMMDD.sql
```

### 性能监控

启用监控组件：
```bash
docker-compose --profile monitoring up -d prometheus grafana
```

访问Grafana: `http://your-ip:3000`

## 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   docker-compose logs synapse
   docker-compose down
   docker-compose up -d
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

### 日志分析

```bash
# 查看错误日志
docker-compose logs --tail=100 synapse | grep ERROR

# 查看特定用户日志
docker-compose logs synapse | grep "@user:domain.com"
```

## 安全建议

1. **定期更新**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

2. **密钥管理**
   - 定期更换密钥
   - 使用强密码
   - 妥善保管 `.env` 文件

3. **网络安全**
   - 配置防火墙
   - 使用SSL/TLS
   - 限制API访问

## 性能优化

### 数据库优化

```sql
-- 添加索引
CREATE INDEX idx_friendships_user1 ON user_friendships(user1_id);
CREATE INDEX idx_friendships_user2 ON user_friendships(user2_id);
CREATE INDEX idx_friend_requests_sender ON friend_requests(sender_user_id);
CREATE INDEX idx_friend_requests_target ON friend_requests(target_user_id);
```

### 缓存优化

```yaml
# Synapse配置
caches:
  global_factor: 1.0
  event_cache_size: 10000

# Redis配置
redis:
  enabled: true
  host: redis
  port: 6379
```

## 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 许可证

本项目基于 Apache 2.0 许可证开源。详见 [LICENSE](LICENSE) 文件。

## 支持

- 📧 邮件: admin@yourdomain.com
- 🐛 问题反馈: [GitHub Issues](https://github.com/yourusername/synapse-friends/issues)
- 📖 文档: [Wiki](https://github.com/yourusername/synapse-friends/wiki)

## 致谢

感谢 [Matrix.org](https://matrix.org) 提供的Matrix协议实现。
感谢所有贡献者和用户的支持！

---

**⚠️ 注意**: 本项目仅用于学习和研究目的，在生产环境使用前请进行充分测试。