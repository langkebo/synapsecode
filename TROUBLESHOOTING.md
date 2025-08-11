# Matrix Synapse 问题解决指南

## 🚨 当前问题分析

根据您的反馈，主要问题包括：

1. **域名配置问题** - 没有正确设置 `matrix.cjystx.top`
2. **服务未启动** - 所有Matrix容器都没有运行
3. **well-known配置** - 需要通过 `cjystx.top` 发现服务器

## 🔧 解决步骤

### 第一步：配置域名

```bash
# 在您的服务器上运行
cd /opt/synapsecode
sudo chmod +x setup-domain.sh
sudo ./setup-domain.sh

# 输入以下信息：
# Matrix服务器域名: matrix.cjystx.top
# 主域名: cjystx.top
```

### 第二步：诊断问题

```bash
# 运行诊断脚本
sudo ./diagnose.sh
```

### 第三步：重新部署

```bash
# 停止现有服务
sudo docker-compose -f docker-compose.minimal.yml down --remove-orphans

# 清理Docker环境
sudo ./docker-cleanup.sh

# 重新部署
sudo ./deploy-simple.sh
```

## 🌐 域名配置详解

### 1. DNS配置
确保您的域名解析正确：
```
matrix.cjystx.top → 您的服务器IP
cjystx.top → 您的服务器IP
```

### 2. well-known配置
配置完成后，以下URL应该可以访问：
- `https://cjystx.top/.well-known/matrix/server`
- `https://cjystx.top/.well-known/matrix/client`

### 3. 反向代理配置
您需要配置反向代理（如Nginx）来处理SSL证书和请求转发。

## 🚀 快速修复命令

如果上述步骤复杂，可以直接运行：

```bash
# 一键修复
cd /opt/synapsecode
sudo ./setup-domain.sh
sudo docker-compose -f docker-compose.minimal.yml down
sudo docker-compose -f docker-compose.minimal.yml up -d --build
```

## 📊 服务状态检查

修复后，运行以下命令检查服务状态：

```bash
# 检查服务状态
sudo ./maintain-minimal.sh status

# 检查健康状态
sudo ./maintain-minimal.sh health

# 查看日志
sudo ./maintain-minimal.sh logs synapse
```

## 🔄 如果仍有问题

1. **检查Docker服务**
   ```bash
   sudo systemctl status docker
   sudo systemctl start docker
   ```

2. **检查端口占用**
   ```bash
   sudo netstat -tlnp | grep -E ":8008|:5432"
   ```

3. **检查磁盘空间**
   ```bash
   sudo df -h
   ```

4. **重新安装Docker**
   ```bash
   sudo apt-get purge docker-ce docker-ce-cli containerd.io
   sudo rm -rf /var/lib/docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh
   ```

## 📞 预期结果

成功配置后，您应该能够：

1. ✅ 所有容器正常运行
2. ✅ 通过 `https://matrix.cjystx.top` 访问服务器
3. ✅ 通过 `https://cjystx.top/.well-known/matrix/` 发现服务器
4. ✅ 使用Matrix客户端连接到服务器

## 🎯 重要提醒

- 确保您的防火墙允许端口 8008 和 5432
- 确保有足够的磁盘空间（至少10GB）
- 确保服务器有足够的内存（至少2GB）
- 确保域名DNS解析正确