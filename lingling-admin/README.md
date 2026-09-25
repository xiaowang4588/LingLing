# 灵灵后台管理系统

前后端分离的后台管理，用于监控运营、工单管理、值班排班、课表查询与系统配置。

## 架构

```
lingling-admin/
├── backend/     Spring Boot 3.2 API（默认 :8082）
└── web/         Vue 3 + Element Plus + ECharts
```

后端直接读写 qq-bot 的 `data/duty_workflow.json`、`data/sf_usage.json` 与 `.env`，与 NoneBot2 机器人共享同一份数据文件。

| 模块 | 路由前缀 | 说明 |
|------|----------|------|
| 控制台 | `/api/dashboard` | 今日报修、趋势图、楼栋分布 |
| 工单 | `/api/tickets` | 列表筛选、强制结案、删除 |
| 值班 | `/api/duty` | 录入/删除值班表、查看当前值班 |
| 课表 | `/api/schedule` | 代理 schedule-mysql API |
| 设置 | `/api/settings` | .env 配置、日志、Token 统计 |
| 楼栋地图 | `/api/dashboard/building-map` | 待处理报修楼栋闪烁 |

## 快速启动（本地）

### 1. 后端

```bash
cd robot/lingling-admin/backend
mvn spring-boot:run
```

默认账号：`admin` / `lingling2026`（可在 `application.yml` 或环境变量修改）

关键环境变量：

| 变量 | 默认 | 说明 |
|------|------|------|
| `BOT_DATA_PATH` | `../../qq-bot/data` | 工单与 Token 数据目录 |
| `BOT_ENV_PATH` | `../../qq-bot/.env` | Bot 环境配置 |
| `SCHEDULE_API_BASE` | `http://127.0.0.1:5000` | 课表 API |
| `JWT_SECRET` | - | JWT 密钥（生产必改） |
| `ADMIN_PASSWORD` | `lingling2026` | 后台登录密码 |

### 2. 前端

```bash
cd robot/lingling-admin/web
npm install
npm run dev
```

浏览器访问 http://localhost:4500 ，Vite 已将 `/api` 代理到 `8082`。

### 3. 依赖服务

- **课表查询**：需 schedule-mysql 后端运行在 `:5000`
- **Bot 数据**：qq-bot 的 `data/` 目录需存在且可读写

## 生产部署建议

1. 后端打包：`mvn -DskipTests package`，jar 与 Bot 同机部署
2. 设置 `BOT_DATA_PATH=/www/wwwroot/qq-bot-workspace/schedule-bot/data`
3. 前端 `npm run build`，静态文件可由 Nginx 托管
4. 修改 `JWT_SECRET`、`ADMIN_PASSWORD`，限制 CORS 来源
5. 修改 `.env` 后需重启 Bot；后台写入值班/工单会即时生效（Bot 下次读文件时同步）

## 认证

当前采用 **JWT + 用户名密码**。管理员 QQ 白名单在 `ADMIN_QQ_IDS` 中配置，供后续扩展 QQ 扫码登录。

## 注意事项

- 工单/值班数据仍为 JSON 文件，Bot 与后台并发写入时存在竞态；高并发场景建议后续迁移 SQLite
- 后台强制结案不会自动触发腾讯文档填表（该逻辑仍在 Bot 群内结案流程中）
- API Key 类配置在界面中脱敏显示，仅允许修改白名单内的非敏感项
