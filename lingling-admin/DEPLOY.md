# 服务器部署说明

解压后根目录固定为：**`/www/wwwroot/lingling-admin`**

## 解压后目录结构

```
/www/wwwroot/lingling-admin/
├── backend/
│   └── lingling-admin-api.jar    # Spring Boot 后端
├── web/
│   └── dist/                     # 前端静态文件（Nginx root）
├── deploy/
│   ├── start-admin.sh            # 后端启停脚本
│   └── nginx-lingling-admin.conf # Nginx 站点配置
├── DEPLOY.md
└── README.md
```

## 1. 上传并解压

```bash
# 上传 zip 到服务器后
mkdir -p /www/wwwroot/lingling-admin
unzip lingling-admin-release.zip -d /www/wwwroot/lingling-admin
```

若 zip 内多一层 `release/` 目录，请确保最终 JAR 在：
`/www/wwwroot/lingling-admin/backend/lingling-admin-api.jar`

## 2. 启动后端（8082，仅本机）

```bash
cd /www/wwwroot/lingling-admin
chmod +x deploy/start-admin.sh

export JWT_SECRET='你的随机密钥'
export ADMIN_PASSWORD='你的强密码'

/www/wwwroot/lingling-admin/deploy/start-admin.sh start
/www/wwwroot/lingling-admin/deploy/start-admin.sh status
```

Bot 数据路径默认已指向：
- `/www/wwwroot/qq-bot-workspace/schedule-bot/data`
- `/www/wwwroot/qq-bot-workspace/schedule-bot/.env`

## 3. 配置 Nginx（对外 4500）

宝塔或手动添加站点，直接 include：

```nginx
include /www/wwwroot/lingling-admin/deploy/nginx-lingling-admin.conf;
```

或复制 `deploy/nginx-lingling-admin.conf` 内容，其中 `root` 已是：

```
/www/wwwroot/lingling-admin/web/dist
```

重载：

```bash
nginx -t && nginx -s reload
```

## 4. 访问

```
http://101.200.128.14:4500
```

默认账号：`admin` / `lingling2026`（上线前务必修改 `ADMIN_PASSWORD`）

## 端口

| 端口 | 用途 |
|------|------|
| **4500** | 对外访问（Nginx → 前端 + `/api` 反代） |
| **8082** | 后端 API（127.0.0.1，不对外暴露） |

## 常用命令

```bash
# 启停
/www/wwwroot/lingling-admin/deploy/start-admin.sh restart

# 查看日志
tail -f /www/wwwroot/lingling-admin/logs/admin-api.log
```
