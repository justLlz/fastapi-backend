#!/bin/bash
set -e

HOME_DIR="${HOME}"
LOCAL_BIN="$HOME_DIR/.local/bin"
BASHRC="$HOME_DIR/.bashrc"

echo "[INFO] 当前用户目录: $HOME_DIR"
echo "[INFO] 目标可执行文件目录: $LOCAL_BIN"

# 1. 安装 nvitop
echo "[INFO] 开始安装 nvitop..."
pip install --user --upgrade nvitop

# 2. 确保 PATH 写入 ~/.bashrc
if ! grep -q "$LOCAL_BIN" "$BASHRC" 2>/dev/null; then
    echo "[INFO] 将 $LOCAL_BIN 添加到 $BASHRC"
    echo "export PATH=\$PATH:$LOCAL_BIN" >> "$BASHRC"
fi

# 3. 强制 source ~/.bashrc
if [[ -f "$BASHRC" ]]; then
    echo "[INFO] 重新加载 $BASHRC ..."
    # shellcheck source=/dev/null
    source "$BASHRC"
fi

# 4. 验证
if command -v nvitop >/dev/null 2>&1; then
    echo "[SUCCESS] nvitop 已安装并可直接使用"
    nvitop --version
else
    echo "[ERROR] nvitop 未能正确安装或 PATH 未生效"
    echo "请尝试手动运行: $LOCAL_BIN/nvitop"
    exit 1
fi

# 5. 提示
echo "Please source nvitop_install.sh"