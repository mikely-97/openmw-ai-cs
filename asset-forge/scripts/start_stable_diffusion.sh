#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Start a local Stable Diffusion server (Automatic1111 / SD-WebUI).
#
# First-time setup:
#   git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git ~/sd-webui
#   cd ~/sd-webui
#   # Download a checkpoint into models/Stable-diffusion/, e.g.:
#   #   wget -P models/Stable-diffusion/ \
#   #     https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
#   bash webui.sh --api   # first run installs deps automatically
#
# Compatible alternatives: SD-WebUI Forge, ComfyUI with A1111-compat API.
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SD_DIR="${SD_DIR:-$HOME/sd-webui}"
PORT="${SD_PORT:-7860}"

if [[ ! -d "$SD_DIR" ]]; then
    echo "ERROR: SD-WebUI not found at $SD_DIR"
    echo "Clone it first:"
    echo "  git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git $SD_DIR"
    exit 1
fi

cd "$SD_DIR"

echo "Starting Stable Diffusion WebUI API on port $PORT …"
bash webui.sh \
    --api \
    --nowebui \
    --port "$PORT" \
    --xformers           # remove if xformers not installed
