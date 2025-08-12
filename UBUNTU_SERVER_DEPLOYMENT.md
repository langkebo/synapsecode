# Matrix Synapse - Ubuntu服务器部署指南

## 🚀 快速部署

本项目提供了完整的Matrix Synapse服务器部署解决方案，专为Ubuntu服务器优化。

### 🎯 配置信息

- **Matrix服务器**: `matrix.cjystx.top`
- **主域名**: `cjystx.top`
- **管理员邮箱**: `admin@cjystx.top`

### 📋 系统要求

- Ubuntu 20.04+ 服务器
- 2GB+ RAM
- 20GB+ 磁盘空间
- Root访问权限
- 域名DNS已正确配置

## 🔧 一键部署

### 1. 克隆项目

```bash
git clone <your-github-repo-url>
cd synapse
```

### 2. 域名和SSL配置

**首先运行域名配置脚本（配置Nginx反向代理和SSL证书）:**

```bash
sudo ./setup-domain.sh
```

这个脚本会自动：
- ✅ 安装Nginx和Certbot
- ✅ 配置反向代理
- ✅ 申请Let's Encrypt SSL证书
- ✅ 设置防火墙规则
- ✅ 配置well-known端点

### 3. 部署Matrix Synapse

**然后运行主部署脚本:**

```bash
sudo ./deploy-simple.sh
```

这个脚本会自动：
- ✅ 安装Docker和Docker Compose
- ✅ 生成安全的配置文件
- ✅ 构建并启动所有服务
- ✅ 验证服务健康状态

## 📊 服务验证

部署完成后，验证服务状态：

```bash
# 检查Docker容器状态
docker compose -f docker-compose.simple.yml ps

# 测试Matrix API
curl -s https://matrix.cjystx.top/_matrix/client/versions | jq .

# 测试well-known配置
curl -s https://cjystx.top/.well-known/matrix/server

# 查看服务日志
docker compose -f docker-compose.simple.yml logs -f synapse
```

## 👤 创建管理员用户

```bash
docker compose -f docker-compose.simple.yml exec synapse \
  register_new_matrix_user -c /data/homeserver.yaml \
  -a http://localhost:8008
```

## 🔐 安全配置

### 自动生成的安全密钥

- `POSTGRES_PASSWORD`: PostgreSQL数据库密码
- `REGISTRATION_SHARED_SECRET`: 用户注册共享密钥
- `MACAROON_SECRET_KEY`: Macaroon签名密钥
- `FORM_SECRET`: 表单安全密钥

### SSL证书

- 自动申请Let's Encrypt证书
- 证书自动更新已配置
- HTTPS强制重定向

### 防火墙

只开放必要端口：
- 22 (SSH)
- 80 (HTTP，重定向到HTTPS)
- 443 (HTTPS)

## 🛠 管理命令

### 服务管理

```bash
# 查看服务状态
docker compose -f docker-compose.simple.yml ps

# 重启服务
docker compose -f docker-compose.simple.yml restart

# 停止服务
docker compose -f docker-compose.simple.yml down

# 更新服务
docker compose -f docker-compose.simple.yml up -d --build
```

### 系统管理

```bash
# 查看Nginx状态
systemctl status nginx

# 查看SSL证书
certbot certificates

# 更新SSL证书
certbot renew

# 查看防火墙状态
ufw status
```

### 数据备份

```bash
# 备份数据目录
sudo tar -czf matrix-backup-$(date +%Y%m%d).tar.gz data/ media/ uploads/

# 备份数据库
docker compose -f docker-compose.simple.yml exec postgres \
  pg_dump -U synapse synapse > backup.sql
```

## 🔍 故障排除

### 常见问题

1. **SSL证书申请失败**
   ```bash
   # 检查DNS解析
   nslookup matrix.cjystx.top
   nslookup cjystx.top
   
   # 手动申请证书
   sudo certbot --nginx -d matrix.cjystx.top
   ```

2. **服务无法启动**
   ```bash
   # 查看详细日志
   docker compose -f docker-compose.simple.yml logs
   
   # 检查端口占用
   sudo netstat -tulpn | grep :8008
   ```

3. **内存不足**
   ```bash
   # 查看资源使用
   free -h
   docker stats
   ```

### 日志查看

```bash
# Matrix Synapse日志
docker compose -f docker-compose.simple.yml logs -f synapse

# PostgreSQL日志
docker compose -f docker-compose.simple.yml logs -f postgres

# Nginx日志
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## 🌐 客户端连接

### 连接信息

- **服务器地址**: `https://matrix.cjystx.top`
- **服务器名**: `matrix.cjystx.top`

### 推荐客户端

- **桌面**: Element Desktop
- **移动端**: Element (iOS/Android)
- **Web**: https://app.element.io

## 🔄 更新部署

```bash
# 拉取最新代码
git pull

# 重新部署
sudo ./deploy-simple.sh
```

## 📞 技术支持

- **管理员邮箱**: admin@cjystx.top
- **服务状态**: https://matrix.cjystx.top/_matrix/client/versions
- **Federation测试**: https://federationtester.matrix.org

---

## 🚨 重要提醒

1. **DNS配置**: 确保域名正确解析到服务器IP
2. **防火墙**: 只开放必要端口
3. **备份**: 定期备份数据和配置
4. **更新**: 定期更新系统和容器镜像
5. **监控**: 监控服务器资源使用情况

---

**部署完成后，您的Matrix服务器将在 `https://matrix.cjystx.top` 上运行！** 🎉