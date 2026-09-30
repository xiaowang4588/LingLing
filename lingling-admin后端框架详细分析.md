# Lingling-Admin 后端框架详细分析

## 📋 目录
- [技术栈概览](#技术栈概览)
- [项目结构](#项目结构)
- [核心配置](#核心配置)
- [架构设计](#架构设计)
- [API接口层](#api接口层)
- [业务服务层](#业务服务层)
- [数据访问层](#数据访问层)
- [安全认证](#安全认证)
- [依赖管理](#依赖管理)
- [部署架构](#部署架构)

---

## 🎯 技术栈概览

### 核心框架
| 技术 | 版本 | 说明 |
|------|------|------|
| **Spring Boot** | 3.2.5 | 核心框架 |
| **Java** | 17 | JDK版本 |
| **Maven** | - | 构建工具 |
| **Jackson** | 2.15.4 | JSON序列化 |
| **JWT** | 0.12.5 (jjwt) | Token认证 |
| **Logback** | 1.4.14 | 日志框架 |
| **Hibernate Validator** | 8.0.1 | 参数校验 |

### 项目标识
```xml
<groupId>com.kb</groupId>
<artifactId>lingling-admin-api</artifactId>
<version>1.0.0</version>
<name>lingling-admin-api</name>
<description>灵灵 QQ 机器人后台管理 API</description>
```

---

## 📁 项目结构

### 包结构（Package Structure）
```
com.kb.lingling/
├── config/                          # 配置类
│   ├── AppProperties                # 应用配置属性
│   ├── AuthWebConfig                # 认证Web配置
│   └── WebConfig                    # Web通用配置
│
├── controller/                      # 控制器层（REST API）
│   ├── AuthController               # 认证接口
│   ├── DashboardController          # 控制台接口
│   ├── DutyController               # 值班管理接口
│   ├── HealthController             # 健康检查接口
│   ├── ScheduleController           # 课表查询接口
│   ├── SettingsController           # 设置管理接口
│   └── TicketController             # 工单管理接口
│
├── dto/                             # 数据传输对象
│   ├── ApiResponse                  # 统一响应格式
│   ├── DutyRosterRequest            # 值班录入请求
│   ├── LoginRequest                 # 登录请求
│   └── TicketUpdateRequest          # 工单更新请求
│
├── model/                           # 数据模型
│   └── WorkflowStore                # 工作流数据存储模型
│
├── security/                        # 安全认证
│   ├── JwtAuthInterceptor           # JWT拦截器
│   └── JwtService                   # JWT服务
│
├── service/                         # 业务服务层
│   ├── ConfigService                # 配置管理服务
│   ├── DashboardService             # 控制台服务
│   ├── DutyService                  # 值班管理服务
│   ├── ScheduleProxyService         # 课表代理服务
│   ├── TicketService                # 工单服务
│   ├── UsageService                 # 使用统计服务
│   └── WorkflowFileService          # 工作流文件服务
│
├── exception/                       # 异常处理
│   └── GlobalExceptionHandler       # 全局异常处理器
│
└── LinglingAdminApplication         # 主启动类
```

---

## ⚙️ 核心配置

### application.yml 完整配置
```yaml
server:
  port: ${SERVER_PORT:8082}

spring:
  application:
    name: lingling-admin-api

app:
  # CORS跨域配置
  cors-origins: "*"
  
  # Bot数据目录（duty_workflow.json、sf_usage.json）
  bot-data-path: ${BOT_DATA_PATH:../../qq-bot/data}
  
  # Bot配置文件（.env）
  bot-env-path: ${BOT_ENV_PATH:../../qq-bot/.env}
  
  # 课表API地址
  schedule-api-base: ${SCHEDULE_API_BASE:http://127.0.0.1:5000}
  
  # JWT配置
  jwt-secret: ${JWT_SECRET:lingling-admin-change-me-in-production}
  jwt-expire-hours: 24
  
  # 管理员账号
  admin-username: ${ADMIN_USERNAME:admin}
  admin-password: ${ADMIN_PASSWORD:lingling2026}
  
  # 管理员QQ白名单（逗号分隔）
  admin-qq-ids: ${ADMIN_QQ_IDS:2321850493}
```

### 环境变量说明
| 变量名 | 默认值 | 必需 | 说明 |
|--------|--------|------|------|
| `SERVER_PORT` | `8082` | 否 | 服务端口 |
| `BOT_DATA_PATH` | `../../qq-bot/data` | 是 | Bot数据目录绝对路径 |
| `BOT_ENV_PATH` | `../../qq-bot/.env` | 是 | Bot配置文件路径 |
| `SCHEDULE_API_BASE` | `http://127.0.0.1:5000` | 否 | 课表API基础URL |
| `JWT_SECRET` | `lingling-admin-change-me-in-production` | **是** | JWT密钥（生产必改） |
| `ADMIN_USERNAME` | `admin` | 否 | 管理员用户名 |
| `ADMIN_PASSWORD` | `lingling2026` | **是** | 管理员密码（生产必改） |
| `ADMIN_QQ_IDS` | `2321850493` | 否 | 管理员QQ白名单 |

### 生产环境配置示例
```bash
export SERVER_PORT=8082
export BOT_DATA_PATH=/www/wwwroot/qq-bot-workspace/schedule-bot/data
export BOT_ENV_PATH=/www/wwwroot/qq-bot-workspace/schedule-bot/.env
export SCHEDULE_API_BASE=http://127.0.0.1:5000
export JWT_SECRET='your-random-256-bit-secret-key-here'
export ADMIN_PASSWORD='your-strong-password-here'
export ADMIN_QQ_IDS='2321850493,1234567890'
```

---

## 🏗️ 架构设计

### 整体架构图
```
┌─────────────────────────────────────────────────────────────┐
│                      Nginx (Port 4500)                      │
│                    静态文件 + API反向代理                     │
└────────────┬───────────────────────────────┬────────────────┘
             │                               │
             ↓ (静态文件)                    ↓ (/api/*)
    ┌────────────────┐           ┌──────────────────────────┐
    │  Vue 3 前端     │           │  Spring Boot 后端        │
    │  (dist/)       │           │  (Port 8082, 127.0.0.1) │
    └────────────────┘           └──────────┬───────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    ↓                       ↓                       ↓
          ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
          │ JWT拦截器        │    │ 全局异常处理     │    │ CORS配置         │
          │ (认证授权)       │    │ (统一响应)      │    │ (跨域支持)       │
          └─────────────────┘    └─────────────────┘    └─────────────────┘
                    │
                    ↓
          ┌─────────────────────────────────────────────────────────┐
          │                   Controller 层                          │
          │  AuthController | DashboardController | TicketController │
          │  DutyController | ScheduleController  | SettingsController│
          └─────────────────────┬───────────────────────────────────┘
                                ↓
          ┌─────────────────────────────────────────────────────────┐
          │                    Service 层                            │
          │  TicketService | DashboardService | ConfigService       │
          │  DutyService   | UsageService     | ScheduleProxyService│
          └─────────────────────┬───────────────────────────────────┘
                                ↓
          ┌─────────────────────────────────────────────────────────┐
          │              WorkflowFileService (数据访问)               │
          │              读写 JSON 文件（与 Bot 共享）                 │
          └─────────────────────┬───────────────────────────────────┘
                                ↓
                    ┌───────────────────────────────┐
                    │    文件系统 (JSON存储)         │
                    │  - duty_workflow.json         │
                    │  - sf_usage.json              │
                    │  - .env                       │
                    └───────────────────────────────┘
```

### 分层职责

#### 1. Controller 层（控制器）
- **职责**：接收HTTP请求，参数校验，调用Service，返回响应
- **特点**：RESTful API设计，使用`@RestController`
- **返回**：统一使用`ApiResponse`包装

#### 2. Service 层（业务逻辑）
- **职责**：核心业务逻辑处理
- **特点**：使用`@Service`注解，事务管理
- **依赖**：调用数据访问层

#### 3. Data Access 层（数据访问）
- **职责**：读写JSON文件，与Bot共享数据
- **实现**：`WorkflowFileService`
- **存储**：文件系统（无数据库）

#### 4. Security 层（安全）
- **职责**：JWT认证、权限校验
- **实现**：拦截器模式
- **流程**：请求 → JWT拦截器 → 验证Token → 放行/拒绝

---

## 🌐 API接口层

### 1. AuthController（认证接口）
**路由前缀**：`/api/auth`

#### POST /api/auth/login
**功能**：用户登录，返回JWT Token

**请求**：
```json
{
  "username": "admin",
  "password": "lingling2026"
}
```

**响应**：
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "token": "<ACCESS_TOKEN_已脱敏>",
    "username": "admin",
    "expiresIn": 86400000
  }
}
```

---

### 2. DashboardController（控制台）
**路由前缀**：`/api/dashboard`

#### GET /api/dashboard
**功能**：获取控制台统计数据

**响应**：
```json
{
  "success": true,
  "data": {
    "todayTickets": 15,
    "pendingTickets": 5,
    "resolvedTickets": 10,
    "trendData": [...],
    "buildingDistribution": {...}
  }
}
```

#### GET /api/dashboard/building-map
**功能**：获取楼栋地图数据（待处理工单的楼栋闪烁）

---

### 3. TicketController（工单管理）
**路由前缀**：`/api/tickets`

#### GET /api/tickets
**功能**：工单列表查询（支持筛选）

**查询参数**：
- `status` - 状态筛选（pending/resolved/closed）
- `building` - 楼栋筛选
- `startDate` - 开始日期
- `endDate` - 结束日期
- `page` - 页码
- `size` - 每页数量

**响应**：
```json
{
  "success": true,
  "data": {
    "tickets": [...],
    "total": 100,
    "page": 1,
    "size": 20
  }
}
```

#### GET /api/tickets/{id}
**功能**：获取工单详情

#### PUT /api/tickets/{id}
**功能**：更新工单（强制结案）

**请求**：
```json
{
  "status": "closed",
  "note": "手动强制结案"
}
```

⚠️ **注意**：后台强制结案**不会触发腾讯文档填表**，该逻辑在Bot中

#### DELETE /api/tickets/{id}
**功能**：删除工单

---

### 4. DutyController（值班管理）
**路由前缀**：`/api/duty`

#### GET /api/duty/current
**功能**：获取当前值班人员

#### POST /api/duty/roster
**功能**：录入值班表

**请求**：
```json
{
  "date": "2026-09-20",
  "person": "张三",
  "contact": "12345678901"
}
```

#### DELETE /api/duty/{id}
**功能**：删除值班记录

---

### 5. ScheduleController（课表查询）
**路由前缀**：`/api/schedule`

#### GET /api/schedule/**
**功能**：代理转发到schedule-mysql API

**实现**：
- 使用`RestTemplate`或`WebClient`
- 转发所有`/api/schedule/**`请求到`http://127.0.0.1:5000`
- 透传请求参数和响应

---

### 6. SettingsController（系统设置）
**路由前缀**：`/api/settings`

#### GET /api/settings/env
**功能**：查看.env配置（脱敏显示）

**响应**：
```json
{
  "success": true,
  "data": {
    "TENCENT_DOC_CLIENT_ID": "94860fc7******cbd20",
    "TENCENT_DOC_ACCESS_TOKEN": "eyJhbG***...(隐藏)",
    "BOT_ADMIN_QQ": "2321850493",
    "OPENAI_API_KEY": "sk-***...(隐藏)"
  }
}
```

#### PUT /api/settings/env
**功能**：修改白名单内的配置项

**白名单**：
- 非敏感配置项
- 不包含API密钥、Token等

#### GET /api/settings/logs
**功能**：查看日志

**查询参数**：
- `lines` - 读取行数（默认100）
- `type` - 日志类型（bot/admin/tencent-doc）

#### GET /api/settings/usage
**功能**：Token使用统计

**响应**：
```json
{
  "success": true,
  "data": {
    "totalCalls": 1523,
    "todayCalls": 45,
    "lastCallTime": "2026-09-20T15:30:00Z",
    "apiBreakdown": {...}
  }
}
```

---

### 7. HealthController（健康检查）
**路由前缀**：`/health`

#### GET /health
**功能**：服务健康检查

**响应**：
```json
{
  "status": "UP",
  "timestamp": "2026-09-20T15:30:00Z",
  "checks": {
    "botDataPath": "accessible",
    "botEnvPath": "accessible",
    "scheduleApi": "UP"
  }
}
```

---

## 💼 业务服务层

### 1. WorkflowFileService（核心数据访问）
**职责**：读写`duty_workflow.json`文件

**关键方法**：
```java
// 读取工作流数据
WorkflowStore readWorkflow()

// 写入工作流数据
void writeWorkflow(WorkflowStore store)

// 加文件锁防止并发冲突
synchronized void safeWrite(WorkflowStore store)
```

**数据模型**：
```json
{
  "tickets": [
    {
      "id": "ticket-001",
      "building": "A栋",
      "room": "301",
      "issue": "水龙头坏了",
      "reporter": "张三",
      "reporterCollege": "计算机学院",
      "reportTime": "2026-09-20 10:00:00",
      "status": "pending",
      "handler": "",
      "resolveTime": null
    }
  ],
  "dutyRoster": [
    {
      "date": "2026-09-20",
      "person": "李四",
      "contact": "12345678901"
    }
  ]
}
```

---

### 2. TicketService（工单业务）
**职责**：工单CRUD、状态管理

**核心逻辑**：
```java
// 获取工单列表（支持筛选）
List<Ticket> listTickets(TicketFilter filter)

// 强制结案（不触发腾讯文档）
void forceCloseTicket(String ticketId, String note)

// 删除工单
void deleteTicket(String ticketId)

// 获取统计数据
TicketStatistics getStatistics()
```

**注意事项**：
- 后台操作**立即生效**（写入JSON）
- Bot下次读取文件时同步
- 强制结案**不会**调用tencent-doc-filler

---

### 3. DashboardService（控制台统计）
**职责**：生成控制台展示数据

**核心功能**：
```java
// 今日报修统计
DashboardSummary getTodaySummary()

// 趋势数据（过去7天/30天）
List<TrendData> getTrendData(int days)

// 楼栋分布统计
Map<String, Integer> getBuildingDistribution()

// 待处理工单楼栋列表（用于地图闪烁）
List<String> getPendingBuildings()
```

---

### 4. ConfigService（配置管理）
**职责**：读写Bot的`.env`配置

**核心功能**：
```java
// 读取配置（敏感信息脱敏）
Map<String, String> readEnvConfig()

// 更新配置（白名单检查）
void updateEnvConfig(Map<String, String> updates)

// 敏感Key列表
private static final Set<String> SENSITIVE_KEYS = Set.of(
    "TENCENT_DOC_CLIENT_SECRET",
    "TENCENT_DOC_ACCESS_TOKEN",
    "OPENAI_API_KEY",
    "API_SECRET"
);

// 可修改白名单
private static final Set<String> EDITABLE_KEYS = Set.of(
    "BOT_ADMIN_QQ",
    "GROUP_ID",
    "NOTIFICATION_ENABLED"
);
```

**脱敏规则**：
- API Key: `sk-***...***abc`（保留前3后3字符）
- Token: `eyJhbG***...(隐藏)`
- 密码: `******`

---

### 5. UsageService（使用统计）
**职责**：读取`sf_usage.json`统计API调用

**数据结构**：
```json
{
  "totalCalls": 1523,
  "apiBreakdown": {
    "gpt-4": 234,
    "tencent-doc": 1289
  },
  "dailyStats": [
    {
      "date": "2026-09-20",
      "calls": 45,
      "tokens": 12345
    }
  ]
}
```

---

### 6. ScheduleProxyService（课表代理）
**职责**：转发课表API请求

**实现方式**：
```java
@Service
public class ScheduleProxyService {
    private final RestTemplate restTemplate;
    private final String scheduleApiBase;
    
    public ResponseEntity<String> proxyRequest(
        String path,
        HttpMethod method,
        Map<String, String> params
    ) {
        String url = scheduleApiBase + path;
        return restTemplate.exchange(url, method, ...);
    }
}
```

---

## 🔒 安全认证

### JWT认证流程
```
1. 用户登录
   POST /api/auth/login
   ↓
2. 验证用户名密码
   username == ADMIN_USERNAME
   password == ADMIN_PASSWORD
   ↓
3. 生成JWT Token
   JwtService.generateToken(username)
   ↓
4. 返回Token给前端
   {token: "eyJhbG...", expiresIn: 86400000}
   ↓
5. 前端存储Token
   localStorage.setItem('token', token)
   ↓
6. 后续请求携带Token
   Header: Authorization: Bearer eyJhbG...
   ↓
7. JWT拦截器验证
   JwtAuthInterceptor.preHandle()
   ↓
8. 放行/拒绝
```

### JwtService核心方法
```java
@Service
public class JwtService {
    private final String secret;
    private final long expireHours;
    
    // 生成Token
    public String generateToken(String username) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + expireHours * 3600 * 1000);
        
        return Jwts.builder()
            .setSubject(username)
            .setIssuedAt(now)
            .setExpiration(expiry)
            .signWith(SignatureAlgorithm.HS256, secret)
            .compact();
    }
    
    // 验证Token
    public boolean validateToken(String token) {
        try {
            Jwts.parser()
                .setSigningKey(secret)
                .parseClaimsJws(token);
            return true;
        } catch (JwtException e) {
            return false;
        }
    }
    
    // 提取用户名
    public String extractUsername(String token) {
        return Jwts.parser()
            .setSigningKey(secret)
            .parseClaimsJws(token)
            .getBody()
            .getSubject();
    }
}
```

### JwtAuthInterceptor拦截器
```java
@Component
public class JwtAuthInterceptor implements HandlerInterceptor {
    private final JwtService jwtService;
    
    @Override
    public boolean preHandle(
        HttpServletRequest request,
        HttpServletResponse response,
        Object handler
    ) throws Exception {
        // 放行登录接口和健康检查
        String path = request.getRequestURI();
        if (path.startsWith("/api/auth/login") || path.startsWith("/health")) {
            return true;
        }
        
        // 提取Token
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            response.setStatus(401);
            response.getWriter().write("{\"error\":\"Missing or invalid token\"}");
            return false;
        }
        
        String token = authHeader.substring(7);
        
        // 验证Token
        if (!jwtService.validateToken(token)) {
            response.setStatus(401);
            response.getWriter().write("{\"error\":\"Invalid or expired token\"}");
            return false;
        }
        
        // 放行
        return true;
    }
}
```

### 拦截器注册
```java
@Configuration
public class AuthWebConfig implements WebMvcConfigurer {
    private final JwtAuthInterceptor jwtAuthInterceptor;
    
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(jwtAuthInterceptor)
            .addPathPatterns("/api/**")
            .excludePathPatterns("/api/auth/login", "/health");
    }
}
```

---

## 📦 依赖管理

### Maven依赖列表
```xml
<dependencies>
    <!-- Spring Boot Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    
    <!-- 参数校验 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>
    
    <!-- JWT认证 -->
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-api</artifactId>
        <version>0.12.5</version>
    </dependency>
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-impl</artifactId>
        <version>0.12.5</version>
        <scope>runtime</scope>
    </dependency>
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-jackson</artifactId>
        <version>0.12.5</version>
        <scope>runtime</scope>
    </dependency>
    
    <!-- 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

### 运行时依赖（JAR包）
```
核心框架：
- spring-boot-3.2.5.jar
- spring-core-6.1.6.jar
- spring-web-6.1.6.jar
- spring-webmvc-6.1.6.jar

JSON处理：
- jackson-databind-2.15.4.jar
- jackson-core-2.15.4.jar
- jackson-annotations-2.15.4.jar

JWT认证：
- jjwt-api-0.12.5.jar
- jjwt-impl-0.12.5.jar
- jjwt-jackson-0.12.5.jar

日志：
- logback-classic-1.4.14.jar
- slf4j-api-2.0.13.jar

校验：
- hibernate-validator-8.0.1.Final.jar
- jakarta.validation-api-3.0.2.jar
```

---

## 🚀 部署架构

### 服务器部署拓扑
```
服务器: 101.200.128.14
用户: root
操作系统: Linux

部署路径:
/www/wwwroot/lingling-admin/
├── backend/
│   └── lingling-admin-api.jar        # Spring Boot 应用
├── web/
│   └── dist/                         # Vue 3 静态文件
├── deploy/
│   ├── start-admin.sh                # 启动脚本
│   └── nginx-lingling-admin.conf     # Nginx配置
└── logs/
    └── admin-api.log                 # 应用日志
```

### 端口分配
| 端口 | 服务 | 监听地址 | 对外访问 |
|------|------|----------|----------|
| **4500** | Nginx | 0.0.0.0 | ✅ 是 |
| **8082** | Spring Boot | 127.0.0.1 | ❌ 否（仅本机） |

### Nginx配置
```nginx
server {
    listen 4500;
    server_name _;
    
    # 前端静态文件
    root /www/wwwroot/lingling-admin/web/dist;
    index index.html;
    
    # API反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # SPA路由支持
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 启动脚本（start-admin.sh）
```bash
#!/bin/bash

JAR_PATH="/www/wwwroot/lingling-admin/backend/lingling-admin-api.jar"
LOG_PATH="/www/wwwroot/lingling-admin/logs/admin-api.log"
PID_FILE="/www/wwwroot/lingling-admin/backend/admin-api.pid"

case "$1" in
    start)
        nohup java -jar $JAR_PATH > $LOG_PATH 2>&1 &
        echo $! > $PID_FILE
        echo "Started"
        ;;
    stop)
        kill $(cat $PID_FILE)
        rm $PID_FILE
        echo "Stopped"
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if [ -f $PID_FILE ]; then
            echo "Running (PID: $(cat $PID_FILE))"
        else
            echo "Not running"
        fi
        ;;
esac
```

### 启动流程
```bash
# 1. 设置环境变量
export JWT_SECRET='your-random-secret-key'
export ADMIN_PASSWORD='your-strong-password'
export BOT_DATA_PATH='/www/wwwroot/qq-bot-workspace/schedule-bot/data'
export BOT_ENV_PATH='/www/wwwroot/qq-bot-workspace/schedule-bot/.env'

# 2. 启动后端
cd /www/wwwroot/lingling-admin
./deploy/start-admin.sh start

# 3. 配置Nginx（首次部署）
include /www/wwwroot/lingling-admin/deploy/nginx-lingling-admin.conf;
nginx -t && nginx -s reload

# 4. 访问
http://101.200.128.14:4500
```

---

## 🔍 数据流分析

### 工单数据流
```
1. QQ群消息
   ↓
2. NoneBot2 处理
   ↓ 写入
3. duty_workflow.json
   ↓ 读取
4. WorkflowFileService
   ↓
5. TicketService (业务逻辑)
   ↓
6. TicketController (API响应)
   ↓
7. 前端展示
```

### 配置修改流
```
1. 前端修改配置
   ↓ PUT /api/settings/env
2. SettingsController
   ↓
3. ConfigService.updateEnvConfig()
   ↓ 白名单检查
4. 写入 .env 文件
   ↓
5. ⚠️ 需重启Bot生效
```

### JWT认证流
```
1. POST /api/auth/login
   ↓
2. AuthController.login()
   ↓ 验证密码
3. JwtService.generateToken()
   ↓
4. 返回Token
   ↓
5. 前端存储Token
   ↓
6. 后续请求携带Token
   ↓ Header: Authorization
7. JwtAuthInterceptor.preHandle()
   ↓ 验证
8. 放行 → Controller
```

---

## ⚠️ 注意事项

### 1. 数据一致性
- JSON文件共享可能有并发问题
- Bot和后台同时写入时存在竞态
- 建议：使用文件锁或迁移到数据库

### 2. 安全性
- **生产环境务必修改**：
  - `JWT_SECRET`
  - `ADMIN_PASSWORD`
- CORS配置生产环境应限制来源
- API Token不要使用默认值

### 3. 性能
- JSON文件I/O频繁
- 大数据量时性能下降
- 建议：缓存常用数据

### 4. 依赖服务
- 课表API（5000端口）需要运行
- Bot数据目录必须可访问
- Nginx正确配置反向代理

### 5. 日志
- 日志路径：`/www/wwwroot/lingling-admin/logs/admin-api.log`
- 建议：配置日志轮转（logrotate）
- 监控：定期查看错误日志

---

## 📚 开发指南

### 本地开发
```bash
# 1. 克隆项目（假设有源码）
git clone <repository>

# 2. 配置环境变量
export BOT_DATA_PATH=/path/to/bot/data
export BOT_ENV_PATH=/path/to/bot/.env
export JWT_SECRET=dev-secret-key
export ADMIN_PASSWORD=dev-password

# 3. 编译运行
mvn clean package
java -jar target/lingling-admin-api-1.0.0.jar

# 或使用Maven运行
mvn spring-boot:run
```

### API测试
```bash
# 登录获取Token
curl -X POST http://localhost:8082/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"lingling2026"}'

# 使用Token访问API
curl http://localhost:8082/api/tickets \
  -H "Authorization: Bearer <token>"
```

---

## 🎯 总结

### 架构特点
✅ **优点**：
- Spring Boot标准分层架构，清晰易维护
- RESTful API设计规范
- JWT认证安全可靠
- 与Bot共享数据，实时同步

⚠️ **待改进**：
- JSON文件存储，建议迁移数据库
- 缺少缓存机制
- 日志不够完善
- 缺少单元测试

### 技术亮点
- 使用JWT实现无状态认证
- 拦截器统一处理认证授权
- 全局异常处理统一响应格式
- 配置外部化，支持环境变量

---

**文档版本**：v1.0  
**最后更新**：2026-09-20  
**维护者**：Ling项目组
