# =============================================================================
# ComfyUI GPU-AI Universal add-on
#
# Architecture (matches the HAOS GPU-AI host/container split): the HOST provides
# the GPU drivers, device nodes, NVIDIA driver user-space libs, and the Container
# Toolkit injection hook. This CONTAINER provides the compute *runtime* — here
# PyTorch's bundled CUDA runtime libs (cudart/cublas/cudnn), which talk to the
# host libcuda that the toolkit injects when NVIDIA_VISIBLE_DEVICES is set.
#
# Nothing CUDA-specific is baked into the HAOS rootfs; it all lives here.
#
# BUILD_FROM / TORCH_INDEX_URL are overridable (see build.yaml) so you can retune
# the CUDA line or build an AMD (ROCm) / Intel (XPU) variant without editing this
# file. Ubuntu 24.04 ships Python 3.12, which ComfyUI targets.
# =============================================================================
ARG BUILD_FROM=nvidia/cuda:12.8.1-runtime-ubuntu24.04
FROM ${BUILD_FROM}

ARG COMFYUI_REPO=https://github.com/comfyanonymous/ComfyUI.git
ARG COMFYUI_REF=master
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PYTHONUNBUFFERED=1

# System deps: Python, git, and the handful of native libs ComfyUI + common
# custom nodes link against (libGL / glib for OpenCV-style image ops).
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-dev python3-pip python3-venv \
      git ca-certificates curl \
      libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI into the image. --branch works for a branch or tag; to pin a bare
# commit SHA, switch build.yaml to a tag/branch or add a fetch+checkout step.
WORKDIR /opt
RUN git clone --depth 1 --branch "${COMFYUI_REF}" "${COMFYUI_REPO}" comfyui

# PyTorch first (its wheels bundle a self-contained CUDA runtime), then ComfyUI's
# own requirements.
WORKDIR /opt/comfyui
RUN python3 -m pip install --upgrade pip \
    && python3 -m pip install torch torchvision torchaudio --index-url "${TORCH_INDEX_URL}" \
    && python3 -m pip install -r requirements.txt

COPY run.sh /run.sh
RUN chmod +x /run.sh

# The CUDA base image sets no app entrypoint; our script owns PID 1.
ENTRYPOINT []
CMD [ "/run.sh" ]
