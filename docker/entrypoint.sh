#!/usr/bin/env bash
set -e

# uvicorn 默认 worker 数（可通过环境变量 UV_WORKERS 覆盖）
: "${UV_WORKERS:=4}"

# 默认启动命令
DEFAULT_CMD="uv run uvicorn main:app --host 0.0.0.0 --port 8000 --workers $UV_WORKERS"

# 如果传入参数，执行用户命令；否则执行默认
if [ $# -gt 0 ]; then
    exec uv run "$@"
else
    exec $DEFAULT_CMD
fi
