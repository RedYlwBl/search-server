#!/bin/bash
# LLM Server Systemd Service 安装脚本

SERVICE_NAME="llm_server"
SERVICE_FILE="llm_server.service"
PROJECT_DIR="/data/work/llm_server"
VENV_DIR="/data/work/vllm/.venv"

echo "=========================================="
echo "LLM Server Systemd Service 安装脚本"
echo "=========================================="

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "错误: 请使用 root 权限运行此脚本"
    echo "使用方法: sudo bash install_service.sh"
    exit 1
fi

# 检查项目目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "错误: 项目目录不存在: $PROJECT_DIR"
    exit 1
fi

# 检查 Python 虚拟环境是否存在
if [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "错误: Python 虚拟环境不存在: $VENV_DIR/bin/python"
    exit 1
fi

# 检查服务文件是否存在
if [ ! -f "$PROJECT_DIR/$SERVICE_FILE" ]; then
    echo "错误: 服务文件不存在: $PROJECT_DIR/$SERVICE_FILE"
    exit 1
fi

# 检查 main_robust.py 是否存在
if [ ! -f "$PROJECT_DIR/main_robust.py" ]; then
    echo "错误: main_robust.py 不存在: $PROJECT_DIR/main_robust.py"
    exit 1
fi

echo ""
echo "1. 复制服务文件到 /etc/systemd/system/"
cp "$PROJECT_DIR/$SERVICE_FILE" "/etc/systemd/system/${SERVICE_NAME}.service"

echo "2. 重新加载 systemd 配置"
systemctl daemon-reload

echo "3. 启用服务（开机自启动）"
systemctl enable "${SERVICE_NAME}.service"

echo ""
echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "常用命令："
echo "  启动服务:   sudo systemctl start ${SERVICE_NAME}"
echo "  停止服务:   sudo systemctl stop ${SERVICE_NAME}"
echo "  重启服务:   sudo systemctl restart ${SERVICE_NAME}"
echo "  查看状态:   sudo systemctl status ${SERVICE_NAME}"
echo "  查看日志:   sudo journalctl -u ${SERVICE_NAME} -f"
echo "  禁用自启:   sudo systemctl disable ${SERVICE_NAME}"
echo ""
echo "服务将在下次开机时自动启动。"
echo "如需立即启动，请运行: sudo systemctl start ${SERVICE_NAME}"
echo ""