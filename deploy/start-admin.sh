#!/usr/bin/env bash
# 灵灵后台 - 服务器启动脚本
# 部署根目录: /www/wwwroot/lingling-admin
# 用法: /www/wwwroot/lingling-admin/deploy/start-admin.sh [start|stop|restart|status]

set -euo pipefail

ROOT_DIR="/www/wwwroot/lingling-admin"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ "$SCRIPT_DIR" == */deploy ]]; then
  ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

JAR="$ROOT_DIR/backend/lingling-admin-api.jar"
PID_FILE="$ROOT_DIR/backend/admin-api.pid"
LOG_DIR="$ROOT_DIR/logs"
LOG_FILE="$LOG_DIR/admin-api.log"

export SPRING_PROFILES_ACTIVE="${SPRING_PROFILES_ACTIVE:-prod}"
export SERVER_PORT="${SERVER_PORT:-8082}"
export BOT_DATA_PATH="${BOT_DATA_PATH:-/www/wwwroot/qq-bot-workspace/schedule-bot/data}"
export BOT_ENV_PATH="${BOT_ENV_PATH:-/www/wwwroot/qq-bot-workspace/schedule-bot/.env}"
export SCHEDULE_API_BASE="${SCHEDULE_API_BASE:-http://127.0.0.1:5000}"

mkdir -p "$LOG_DIR"

start() {
  if [[ ! -f "$JAR" ]]; then
    echo "找不到 JAR: $JAR"
    exit 1
  fi
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "已在运行 PID=$(cat "$PID_FILE")"
    exit 0
  fi
  cd "$ROOT_DIR/backend"
  nohup java -jar "$JAR" >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  echo "已启动 PID=$(cat "$PID_FILE") 端口=$SERVER_PORT"
  echo "日志: $LOG_FILE"
}

stop() {
  if [[ ! -f "$PID_FILE" ]]; then
    echo "未运行"
    exit 0
  fi
  kill "$(cat "$PID_FILE")" 2>/dev/null || true
  rm -f "$PID_FILE"
  echo "已停止"
}

case "${1:-start}" in
  start) start ;;
  stop) stop ;;
  restart) stop; sleep 1; start ;;
  status)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "运行中 PID=$(cat "$PID_FILE")"
      echo "JAR: $JAR"
      echo "日志: $LOG_FILE"
    else
      echo "未运行"
    fi
    ;;
  *) echo "用法: $0 {start|stop|restart|status}"; exit 1 ;;
esac
