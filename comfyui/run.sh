#!/usr/bin/env bash
# ComfyUI GPU-AI add-on entrypoint.
set -euo pipefail

echo "[comfyui-addon] starting; probing GPU visibility inside container"

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
	echo "[comfyui-addon] NVIDIA GPU visible:"
	nvidia-smi -L || true
elif [ -e /dev/kfd ] && [ -d /dev/dri ]; then
	echo "[comfyui-addon] AMD ROCm compute node (/dev/kfd) + render node visible"
	echo "[comfyui-addon] NOTE: this image ships CUDA/PyTorch — for AMD, rebuild with a"
	echo "[comfyui-addon]       ROCm BUILD_FROM + ROCm torch wheels (TORCH_INDEX_URL=rocm)."
elif [ -d /dev/dri ]; then
	echo "[comfyui-addon] Intel/other DRI render node visible (/dev/dri)"
	echo "[comfyui-addon] NOTE: this image ships CUDA/PyTorch — Intel needs an XPU/IPEX torch build."
else
	echo "[comfyui-addon] WARNING: no GPU device visible; ComfyUI will fall back to CPU (very slow)."
fi

# Persist models, inputs, outputs, and the user dir on the HA /share mapping
# (map: share:rw) so multi-GB checkpoints and generated images survive add-on
# rebuilds and updates.
BASE="${COMFYUI_SHARE:-/share/comfyui}"
for d in \
	input output user \
	models/checkpoints models/vae models/loras models/clip models/clip_vision \
	models/controlnet models/upscale_models models/embeddings \
	models/diffusion_models models/unet; do
	mkdir -p "${BASE}/${d}"
done

# Point ComfyUI's model search paths at /share via its documented
# extra_model_paths.yaml mechanism (regenerated each start; idempotent).
cat > /opt/comfyui/extra_model_paths.yaml <<EOF
comfyui_share:
  base_path: ${BASE}
  checkpoints: models/checkpoints
  vae: models/vae
  loras: models/loras
  clip: models/clip
  clip_vision: models/clip_vision
  controlnet: models/controlnet
  upscale_models: models/upscale_models
  embeddings: models/embeddings
  diffusion_models: models/diffusion_models
  unet: models/unet
EOF

# Plug-and-play first-start bootstrap: optional model download + seeding the API
# workflow into the HA config dir. Best-effort; never blocks ComfyUI from starting.
python3 /opt/addon/bootstrap.py || echo "[comfyui-addon] bootstrap had a non-fatal issue; continuing"

export COMFYUI_PORT="${COMFYUI_PORT:-8188}"
# Extra ComfyUI CLI flags. Prefer the add-on option (Configuration tab), then the
# COMFYUI_EXTRA_ARGS env var, else none. Space-separated, e.g. "--lowvram".
OPT_EXTRA="$(python3 -c 'import json,sys
try:
    sys.stdout.write(json.load(open("/data/options.json")).get("extra_args","") or "")
except Exception:
    pass' 2>/dev/null || true)"
EXTRA_ARGS="${COMFYUI_EXTRA_ARGS:-${OPT_EXTRA}}"

cd /opt/comfyui
echo "[comfyui-addon] launching ComfyUI on 0.0.0.0:${COMFYUI_PORT} (data under ${BASE})"
# shellcheck disable=SC2086  # EXTRA_ARGS is intentionally word-split.
exec python3 main.py \
	--listen 0.0.0.0 \
	--port "${COMFYUI_PORT}" \
	--extra-model-paths-config /opt/comfyui/extra_model_paths.yaml \
	--input-directory "${BASE}/input" \
	--output-directory "${BASE}/output" \
	--user-directory "${BASE}/user" \
	${EXTRA_ARGS}
