#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Start the Hunyuan3D-2 local Gradio server.
#
# First-time setup:
#   git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git ~/hunyuan3d
#   cd ~/hunyuan3d
#   python -m venv .venv && source .venv/bin/activate
#   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
#   pip install -r requirements.txt
#   # Custom CUDA ops (required for texture generation):
#   pip install git+https://github.com/NVlabs/nvdiffrast.git
#   pip install -e .
#
# Model weights are downloaded automatically on first run from HuggingFace.
# Required VRAM:
#   Shape only:            ~11.5 GB
#   Shape + texture (PBR): ~24.5 GB
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

HUNYUAN_DIR="${HUNYUAN_DIR:-$HOME/hunyuan3d}"
PORT="${HUNYUAN_PORT:-8080}"

if [[ ! -d "$HUNYUAN_DIR" ]]; then
    echo "ERROR: Hunyuan3D not found at $HUNYUAN_DIR"
    echo "Clone it first:"
    echo "  git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2.git $HUNYUAN_DIR"
    exit 1
fi

cd "$HUNYUAN_DIR"
source .venv/bin/activate

echo "Starting Hunyuan3D Gradio server on port $PORT …"
python app.py \
    --host 0.0.0.0 \
    --port "$PORT" \
    --enable-tex \
    --low-vram-mode        # remove this flag if you have 24+ GB VRAM
