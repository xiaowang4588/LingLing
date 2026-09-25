# 服务器 NoneBot2 QQ机器人 - 完整分析报告

## 🔍 服务器环境信息

**服务器IP**：101.200.128.14  
**用户**：root  
**部署根目录**：/www/wwwroot/  
**查询时间**：2026年9月20日

---

## 📊 发现的运行中进程

### 1. tencent-doc-filler（腾讯文档填充服务）✅ 运行中
```bash
进程ID: 331645
启动时间: Jun16（已运行约3个月）
命令: /www/wwwroot/tencent-doc-filler/.venv/bin/python3.11 .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8090
CPU使用: 0.1%
内存使用: 33860 KB (1.7%)
```

**功能**：
- 这是一个 FastAPI 服务
- 监听本地 8090 端口
- 负责接收工单数据并上传到腾讯文档

---

### 2. kb-api（课表API服务）✅ 运行中
```bash
进程ID: 1004166
启动时间: 15:42（今天启动）
命令: python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
CPU使用: 0.2%
内存使用: 75516 KB (3.9%)
```

**功能**：
- 课表查询 API 服务
- 监听本地 8001 端口

---

## 🤖 NoneBot2 机器人状态

### ❌ NoneBot2 机器人当前未运行

**机器人位置**：`/www/wwwroot/qq-bot-workspace/schedule-bot/`

**未发现运行中的 bot.py 进程**

---

## 📁 项目目录结构分析

### 1. qq-bot-workspace（QQ机器人工作空间）
**路径**：`/www/wwwroot/qq-bot-workspace/`

```
qq-bot-workspace/
├── go-cqhttp/          # go-cqhttp 协议端
└── schedule-bot/       # NoneBot2 机器人主项目 ⭐
```

---

### 2. schedule-bot（NoneBot2 核心项目）⭐
**路径**：`/www/wwwroot/qq-bot-workspace/schedule-bot/`

```
schedule-bot/
├── bot.py                    # 机器人主程序 ⭐
├── src/                      # 源代码目录
├── data/                     # 数据文件目录
│   ├── duty_workflow.json   # 工单与值班数据
│   └── sf_usage.json        # Token 使用统计
├── logs/                     # 日志目录
├── .env                      # 配置文件 ⭐
├── .env.example              # 配置示例
├── requirements.txt          # Python 依赖
├── pyproject.toml           # 项目配置
├── start.sh                 # 启动脚本 ⭐
├── restart_bot.sh           # 重启脚本
├── deploy_update.sh         # 部署更新脚本
├── schedule-bot.service     # systemd 服务配置
└── .venv/                   # Python 虚拟环境
```

**关键依赖**：
- NoneBot2（QQ 机器人框架）
- OneBot v11/v12 适配器
- FastAPI
- uvicorn

---

### 3. tencent-doc-filler（腾讯文档上传服务）⭐
**路径**：`/www/wwwroot/tencent-doc-filler/`

```
tencent-doc-filler/
├── app.py                    # FastAPI 主程序 ⭐
├── config.py                 # 配置管理
├── tencent_client.py         # 腾讯文档 API 客户端 ⭐
├── fields.py                 # 字段映射配置
├── .env                      # 环境配置
├── token.json                # 腾讯文档 Token
├── next_row.json             # 下一行写入位置记录
├── requirements.txt          # 依赖
└── .venv/                    # Python 虚拟环境
```

**运行状态**：✅ 正在运行（端口 8090）

---

## 🔗 系统架构关系图

```
QQ 群聊消息
    ↓
[go-cqhttp] (协议端)
    ↓ WebSocket/HTTP
[NoneBot2 schedule-bot] ❌ 未运行
    ↓ 处理消息，生成工单
    ↓ 写入 duty_workflow.json
    ↓
    ↓ HTTP POST 请求 (端口 8090)
    ↓
[tencent-doc-filler] ✅ 运行中
    ↓ 读取工单数据
    ↓ 调用腾讯文档 API
    ↓
[腾讯在线文档] 📊
```

---

## 🚀 启动 NoneBot2 机器人

### 方法1：使用启动脚本（推荐）
```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot
chmod +x start.sh
./start.sh
```

### 方法2：使用重启脚本
```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot
chmod +x restart_bot.sh
./restart_bot.sh
```

### 方法3：手动启动
```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot
source .venv/bin/activate
python bot.py
```

### 方法4：使用 systemd 服务
```bash
# 安装服务
sudo cp /www/wwwroot/qq-bot-workspace/schedule-bot/schedule-bot.service /etc/systemd/system/
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start schedule-bot

# 开机自启
sudo systemctl enable schedule-bot

# 查看状态
sudo systemctl status schedule-bot
```

---

## 📝 配置文件位置

### 1. NoneBot2 机器人配置
**文件**：`/www/wwwroot/qq-bot-workspace/schedule-bot/.env`

**主要配置项**：
- QQ 机器人连接配置
- 管理员 QQ 列表
- API 密钥
- 腾讯文档服务地址（指向 8090 端口）

### 2. 腾讯文档服务配置
**文件**：`/www/wwwroot/tencent-doc-filler/.env`

**主要配置项**：
- 腾讯文档 API 凭证
- 文档 ID
- 工作表 ID
- 字段映射

### 3. 管理后台配置
**文件**：`/www/wwwroot/lingling-admin/backend/lingling-admin-api.jar`（内置配置）

**环境变量**：
- `BOT_DATA_PATH=/www/wwwroot/qq-bot-workspace/schedule-bot/data`
- `BOT_ENV_PATH=/www/wwwroot/qq-bot-workspace/schedule-bot/.env`

---

## 📊 数据流向详解

### 完整工作流程

#### 1. 用户在 QQ 群发送报修消息
```
QQ 用户: "宿舍楼 A301 水龙头坏了"
```

#### 2. go-cqhttp 接收消息并转发
```
go-cqhttp (协议端)
    ↓ WebSocket
NoneBot2 监听消息
```

#### 3. NoneBot2 处理消息
```python
# schedule-bot 接收消息
# 解析报修内容
# 生成工单数据
工单数据 = {
    "楼栋": "A栋",
    "房间号": "301",
    "问题": "水龙头坏了",
    "报修人": "xxx",
    "时间": "2026-09-20 17:00:00"
}

# 写入本地文件
duty_workflow.json ← 工单数据

# 发送 HTTP POST 到腾讯文档服务
POST http://127.0.0.1:8090/api/submit-ticket
```

#### 4. tencent-doc-filler 上传到腾讯文档
```python
# app.py 接收请求
@app.post("/api/submit-ticket")
def submit_ticket(data):
    # tencent_client.py 调用腾讯文档 API
    # 将工单数据追加到在线表格
    腾讯文档.append_row(工单数据)
    
    # 更新下一行位置
    next_row.json ← 行号+1
```

#### 5. 管理员查看
```
方式1: 直接访问腾讯在线文档查看
方式2: 通过管理后台查看 (http://101.200.128.14:4500)
```

---

## 🔍 关键文件说明

### 1. bot.py（机器人主程序）
**路径**：`/www/wwwroot/qq-bot-workspace/schedule-bot/bot.py`

**功能**：
- NoneBot2 启动入口
- 加载插件
- 配置适配器

### 2. duty_workflow.json（工单数据文件）
**路径**：`/www/wwwroot/qq-bot-workspace/schedule-bot/data/duty_workflow.json`

**内容结构**：
```json
{
  "tickets": [
    {
      "id": "xxx",
      "building": "A栋",
      "room": "301",
      "issue": "水龙头坏了",
      "reporter": "xxx",
      "time": "2026-09-20 17:00:00",
      "status": "pending"
    }
  ],
  "duty_roster": [
    {
      "date": "2026-09-20",
      "person": "值班人员"
    }
  ]
}
```

### 3. tencent_client.py（腾讯文档客户端）
**路径**：`/www/wwwroot/tencent-doc-filler/tencent_client.py`

**核心方法**：
- `get_token()` - 获取访问令牌
- `append_row()` - 追加一行数据
- `update_cell()` - 更新单元格
- `get_sheet_data()` - 读取表格数据

### 4. app.py（腾讯文档服务主程序）
**路径**：`/www/wwwroot/tencent-doc-filler/app.py`

**API 接口**：
- `POST /api/submit-ticket` - 提交工单到腾讯文档
- `GET /api/health` - 健康检查
- `POST /api/sync-data` - 同步数据

---

## 🛠️ 运维操作指南

### 查看日志

#### 1. NoneBot2 机器人日志
```bash
# 实时查看
tail -f /www/wwwroot/qq-bot-workspace/schedule-bot/logs/bot.log

# 查看最近 100 行
tail -n 100 /www/wwwroot/qq-bot-workspace/schedule-bot/logs/bot.log
```

#### 2. 腾讯文档服务日志
```bash
# 实时查看
tail -f /www/wwwroot/tencent-doc-filler/logs/app.log

# 查看最近 100 行
tail -n 100 /www/wwwroot/tencent-doc-filler/logs/app.log
```

#### 3. 管理后台日志
```bash
tail -f /www/wwwroot/lingling-admin/logs/admin-api.log
```

---

### 重启服务

#### 1. 重启 NoneBot2 机器人
```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot
./restart_bot.sh
```

#### 2. 重启腾讯文档服务
```bash
# 查找进程 PID
ps aux | grep "tencent-doc-filler" | grep -v grep

# 杀死进程（PID: 331645）
kill 331645

# 重新启动
cd /www/wwwroot/tencent-doc-filler
source .venv/bin/activate
nohup uvicorn app:app --host 127.0.0.1 --port 8090 > logs/app.log 2>&1 &
```

#### 3. 重启管理后台
```bash
/www/wwwroot/lingling-admin/deploy/start-admin.sh restart
```

---

### 检查服务状态

```bash
# 查看所有相关进程
ps aux | grep -E "bot.py|tencent-doc|uvicorn|lingling" | grep -v grep

# 检查端口占用
netstat -tunlp | grep -E "8090|8001|8082|4500"

# 测试腾讯文档服务
curl http://127.0.0.1:8090/api/health
```

---

## ⚠️ 当前问题与建议

### 🔴 问题1：NoneBot2 机器人未运行
**现象**：
- 没有发现 bot.py 进程
- QQ 消息无法被处理

**建议**：
```bash
cd /www/wwwroot/qq-bot-workspace/schedule-bot
./start.sh
```

**可能原因**：
- 手动停止
- 进程崩溃
- 配置错误

---

### 🟢 问题2：tencent-doc-filler 正常运行
**状态**：✅ 正常

**进程信息**：
- 已运行约 3 个月
- 稳定运行在 8090 端口

---

### 🟡 建议：配置进程守护

#### 使用 systemd（推荐）
```bash
# NoneBot2 机器人
sudo systemctl enable schedule-bot
sudo systemctl start schedule-bot

# 腾讯文档服务（需要创建 service 文件）
sudo nano /etc/systemd/system/tencent-doc-filler.service
```

**tencent-doc-filler.service 示例**：
```ini
[Unit]
Description=Tencent Doc Filler Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/tencent-doc-filler
ExecStart=/www/wwwroot/tencent-doc-filler/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8090
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 使用 Supervisor
```bash
apt install supervisor

# 配置文件
/etc/supervisor/conf.d/schedule-bot.conf
/etc/supervisor/conf.d/tencent-doc-filler.conf
```

---

## 📦 下载到本地的指令

### 下载 schedule-bot（NoneBot2 主项目）
```bash
scp -r root@101.200.128.14:/www/wwwroot/qq-bot-workspace/schedule-bot ~/Desktop/
```

### 下载 tencent-doc-filler（腾讯文档服务）
```bash
scp -r root@101.200.128.14:/www/wwwroot/tencent-doc-filler ~/Desktop/
```

### 下载 go-cqhttp（协议端）
```bash
scp -r root@101.200.128.14:/www/wwwroot/qq-bot-workspace/go-cqhttp ~/Desktop/
```

---

## 🎯 总结

### 三大核心组件

| 组件 | 路径 | 状态 | 端口 | 功能 |
|------|------|------|------|------|
| **NoneBot2 机器人** | `/www/wwwroot/qq-bot-workspace/schedule-bot/` | ❌ 未运行 | - | 接收处理QQ消息 |
| **腾讯文档服务** | `/www/wwwroot/tencent-doc-filler/` | ✅ 运行中 | 8090 | 上传数据到腾讯文档 |
| **管理后台** | `/www/wwwroot/lingling-admin/` | ✅ 运行中 | 4500/8082 | 数据查看和管理 |

### 完整流程
```
QQ消息 → go-cqhttp → NoneBot2(❌未运行) → 本地JSON → HTTP请求 → 腾讯文档服务(✅) → 腾讯在线文档
                                              ↓
                                        管理后台(✅) 查看
```

### 立即行动
1. ✅ 启动 NoneBot2 机器人：`cd /www/wwwroot/qq-bot-workspace/schedule-bot && ./start.sh`
2. ✅ 配置 systemd 自启动
3. ✅ 检查日志确认运行正常

---

## 📞 技术支持

**机器人项目路径**：`/www/wwwroot/qq-bot-workspace/schedule-bot/`  
**腾讯文档服务路径**：`/www/wwwroot/tencent-doc-filler/`  
**管理后台路径**：`/www/wwwroot/lingling-admin/`

**配置文件**：
- NoneBot2: `/www/wwwroot/qq-bot-workspace/schedule-bot/.env`
- 腾讯文档: `/www/wwwroot/tencent-doc-filler/.env`
