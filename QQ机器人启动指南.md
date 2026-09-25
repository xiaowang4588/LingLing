# 服务器 QQ 机器人启动指南

## 🚀 快速启动

### 方法1：使用启动脚本（推荐）⭐

```bash
# SSH登录服务器
ssh root@101.200.128.14
# 密码：Wang740326

# 进入机器人目录
cd /www/wwwroot/qq-bot-workspace/schedule-bot

# 启动机器人
./start.sh
```

---

### 方法2：使用重启脚本

```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot
./restart_bot.sh
```

---

### 方法3：手动启动

```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot

# 激活虚拟环境
source .venv/bin/activate

# 启动机器人
python bot.py
```

---

### 方法4：后台运行（推荐生产环境）

```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot

# 使用 nohup 后台运行
nohup python bot.py > logs/bot.log 2>&1 &

# 查看进程
ps aux | grep bot.py
```

---

## 🔧 使用 systemd 服务（最佳方案）

### 1. 安装服务

```bash
# 复制服务文件
sudo cp /www/wwwroot/qq-bot-workspace/schedule-bot/schedule-bot.service /etc/systemd/system/

# 重新加载 systemd
sudo systemctl daemon-reload
```

### 2. 启动服务

```bash
# 启动
sudo systemctl start schedule-bot

# 查看状态
sudo systemctl status schedule-bot

# 设置开机自启
sudo systemctl enable schedule-bot
```

### 3. 服务管理命令

```bash
# 停止服务
sudo systemctl stop schedule-bot

# 重启服务
sudo systemctl restart schedule-bot

# 查看日志
sudo journalctl -u schedule-bot -f
```

---

## 📊 检查机器人运行状态

### 查看进程

```bash
# 查看所有相关进程
ps aux | grep -E "bot.py|nonebot" | grep -v grep

# 查看详细信息
ps aux | grep python | grep bot
```

### 查看日志

```bash
# 实时查看日志
tail -f /www/wwwroot/qq-bot-workspace/schedule-bot/logs/bot.log

# 查看最近100行
tail -n 100 /www/wwwroot/qq-bot-workspace/schedule-bot/logs/bot.log

# 搜索错误
grep ERROR /www/wwwroot/qq-bot-workspace/schedule-bot/logs/bot.log
```

### 检查端口

```bash
# 查看机器人监听的端口
netstat -tunlp | grep python

# 或使用 ss 命令
ss -tunlp | grep python
```

---

## 🔗 启动整个系统

完整的 QQ 机器人系统需要启动多个组件：

### 1. 启动 go-cqhttp（QQ协议端）

```bash
cd /www/wwwroot/qq-bot-workspace/go-cqhttp

# 后台启动
nohup ./go-cqhttp > logs/go-cqhttp.log 2>&1 &
```

### 2. 启动 NoneBot2 机器人

```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot
./start.sh
```

### 3. 确认 tencent-doc-filler 正在运行

```bash
# 检查是否运行
ps aux | grep tencent-doc-filler

# 如果没运行，启动它
cd /www/wwwroot/tencent-doc-filler
source .venv/bin/activate
nohup uvicorn app:app --host 127.0.0.1 --port 8090 > logs/app.log 2>&1 &
```

### 4. 启动管理后台（可选）

```bash
cd /www/wwwroot/lingling-admin
./deploy/start-admin.sh
```

---

## 🛠️ 故障排查

### 问题1：启动失败

```bash
# 检查配置文件
cat /www/wwwroot/qq-bot-workspace/schedule-bot/.env

# 检查依赖
cd /www/wwwroot/qq-bot-workspace/schedule-bot
source .venv/bin/activate
pip list
```

### 问题2：连接失败

```bash
# 检查 go-cqhttp 是否运行
ps aux | grep go-cqhttp

# 查看 go-cqhttp 日志
tail -f /www/wwwroot/qq-bot-workspace/go-cqhttp/logs/latest.log
```

### 问题3：端口冲突

```bash
# 查看端口占用
netstat -tunlp | grep -E "8080|8090|8001"

# 杀死占用端口的进程
kill -9 <PID>
```

---

## 📝 一键启动脚本

创建一个启动所有服务的脚本：

```bash
# 创建启动脚本
cat > /www/wwwroot/start_all_services.sh << 'EOF'
#!/bin/bash

echo "=== 启动 QQ 机器人系统 ==="

# 1. 启动 go-cqhttp
echo "启动 go-cqhttp..."
cd /www/wwwroot/qq-bot-workspace/go-cqhttp
nohup ./go-cqhttp > logs/go-cqhttp.log 2>&1 &
sleep 3

# 2. 启动 NoneBot2 机器人
echo "启动 NoneBot2 机器人..."
cd /www/wwwroot/qq-bot-workspace/schedule-bot
nohup python bot.py > logs/bot.log 2>&1 &
sleep 3

# 3. 检查 tencent-doc-filler
echo "检查 tencent-doc-filler..."
if ! pgrep -f "tencent-doc-filler" > /dev/null; then
    echo "启动 tencent-doc-filler..."
    cd /www/wwwroot/tencent-doc-filler
    source .venv/bin/activate
    nohup uvicorn app:app --host 127.0.0.1 --port 8090 > logs/app.log 2>&1 &
else
    echo "tencent-doc-filler 已在运行"
fi

sleep 2
echo ""
echo "=== 服务状态 ==="
ps aux | grep -E "go-cqhttp|bot.py|tencent-doc-filler" | grep -v grep

echo ""
echo "=== 启动完成 ==="
EOF

# 添加执行权限
chmod +x /www/wwwroot/start_all_services.sh
```

使用方法：

```bash
/www/wwwroot/start_all_services.sh
```

---

## 🔍 快速检查命令

```bash
# 一键检查所有服务状态
ps aux | grep -E "go-cqhttp|bot.py|tencent-doc|uvicorn" | grep -v grep

# 查看所有日志
tail -n 20 /www/wwwroot/qq-bot-workspace/schedule-bot/logs/bot.log
tail -n 20 /www/wwwroot/tencent-doc-filler/logs/app.log
tail -n 20 /www/wwwroot/qq-bot-workspace/go-cqhttp/logs/latest.log
```

---

## ⚠️ 注意事项

1. **启动顺序**：
   - 先启动 go-cqhttp（QQ协议端）
   - 再启动 NoneBot2 机器人
   - tencent-doc-filler 已经在运行

2. **配置检查**：
   - 确认 `.env` 文件配置正确
   - 确认 QQ 账号已登录 go-cqhttp
   - 确认端口没有冲突

3. **权限问题**：
   - 确保脚本有执行权限：`chmod +x *.sh`
   - 确保日志目录可写

4. **网络问题**：
   - 确认服务器可以访问 QQ 服务器
   - 确认防火墙规则正确

---

## 🎯 推荐的启动方式

**开发/测试环境**：
```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot
./start.sh
```

**生产环境**：
```bash
sudo systemctl start schedule-bot
sudo systemctl enable schedule-bot
```

---

## 📞 快速命令参考

| 操作 | 命令 |
|------|------|
| 启动机器人 | `cd /www/wwwroot/qq-bot-workspace/schedule-bot && ./start.sh` |
| 重启机器人 | `cd /www/wwwroot/qq-bot-workspace/schedule-bot && ./restart_bot.sh` |
| 停止机器人 | `pkill -f bot.py` |
| 查看状态 | `ps aux \| grep bot.py` |
| 查看日志 | `tail -f /www/wwwroot/qq-bot-workspace/schedule-bot/logs/bot.log` |
| 启动所有服务 | `/www/wwwroot/start_all_services.sh` |

---

需要我帮你远程启动吗？或者有任何问题可以告诉我！
