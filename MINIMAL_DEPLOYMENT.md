# Matrix Synapse 极简版部署指南
## 专为单核CPU 2G内存服务器优化

### 🚀 一键部署

```bash
# 1. 克隆项目
git clone https://github.com/langkebo/synapsecode.git
cd synapsecode

# 2. 运行极简版部署脚本
sudo chmod +x deploy-minimal.sh
sudo ./deploy-minimal.sh
```

### 📋 系统要求

- **CPU**: 1核心
- **内存**: 2GB RAM
- **存储**: 10GB SSD
- **网络**: 公网IP
- **系统**: Ubuntu 20.04+ / Debian 10+

### ⚡ 性能优化

#### 资源分配
- **PostgreSQL**: 512MB内存, 0.3核CPU
- **Synapse**: 1GB内存, 0.7核CPU
- **Well-known**: 32MB内存, 0.05核CPU
- **总计**: ~1.5GB内存, 1核CPU

#### 优化配置
- 缓存因子: 0.2 (原为1.0)
- 事件缓存: 500 (原为10000)
- 数据库连接池: 1-2个
- 媒体保留: 3-7天
- 上传限制: 5MB

### 🔧 配置文件

1. **主配置**: `config/homeserver-minimal.yaml`
2. **环境变量**: `.env.minimal`
3. **Docker配置**: `docker-compose.minimal.yml`
4. **部署脚本**: `deploy-minimal.sh`

### 🛠️ 管理命令

```bash
# 查看服务状态
./maintain-minimal.sh status

# 检查健康状态
./maintain-minimal.sh health

# 查看资源使用
./maintain-minimal.sh resources

# 查看日志
./maintain-minimal.sh logs synapse

# 重启服务
./maintain-minimal.sh restart

# 清理资源
./maintain-minimal.sh cleanup

# 备份配置
./maintain-minimal.sh backup
```

### 📊 监控指标

```bash
# 实时监控
docker stats

# 查看容器状态
docker-compose -f docker-compose.minimal.yml ps

# 查看日志
docker-compose -f docker-compose.minimal.yml logs -f
```

### 🚨 故障排除

#### 常见问题

1. **内存不足**
   ```bash
   # 检查内存使用
   free -h
   docker stats
   
   # 清理资源
   ./maintain-minimal.sh cleanup
   ```

2. **服务启动失败**
   ```bash
   # 查看错误日志
   ./maintain-minimal.sh logs
   
   # 重启服务
   ./maintain-minimal.sh restart
   ```

3. **数据库连接问题**
   ```bash
   # 检查数据库状态
   docker-compose -f docker-compose.minimal.yml exec postgres pg_isready
   ```

### 🔒 安全建议

1. **修改默认密码**
   ```bash
   # 编辑环境变量
   nano .env.minimal
   ```

2. **配置防火墙**
   ```bash
   # 只开放必要端口
   ufw allow 8008
   ufw allow 443
   ufw allow 80
   ```

3. **定期备份**
   ```bash
   # 每周备份
   ./maintain-minimal.sh backup
   ```

### 📈 性能基准

#### 预期性能
- **用户数量**: 1-3个用户
- **消息处理**: ~100条/天
- **内存使用**: ~1.5GB
- **CPU使用**: ~60-80%

#### 限制说明
- 好友数量限制: 50个/用户
- 文件上传限制: 5MB
- 媒体保留时间: 3-7天
- 速率限制: 严格限制

### 🔄 更新和维护

```bash
# 更新镜像
docker-compose -f docker-compose.minimal.yml pull

# 重新构建
docker-compose -f docker-compose.minimal.yml up -d --build

# 清理旧镜像
docker image prune -f
```

### 📞 支持

如果遇到问题，请：
1. 检查日志: `./maintain-minimal.sh logs`
2. 查看状态: `./maintain-minimal.sh status`
3. 重启服务: `./maintain-minimal.sh restart`

---

**⚠️ 注意**: 此版本专为低配服务器优化，功能有所限制，但保持了核心的Matrix和好友功能。