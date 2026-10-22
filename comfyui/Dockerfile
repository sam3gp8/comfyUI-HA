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
# Retune by editing the ARGs below (BUILD_FROM / TORCH_INDEX_URL / COMFYUI_REF)
# to change the CUDA line or build an AMD (ROCm) / Intel (XPU) variant. These
# live in the Dockerfile (not build.yaml, which the Supervisor now deprecates).
# Ubuntu 24.04 ships Python 3.12, which ComfyUI targets.
# =============================================================================
ARG BUILD_FROM=nvidia/cuda:12.8.1-runtime-ubuntu24.04
FROM ${BUILD_FROM}

ARG COMFYUI_REPO=https://github.com/comfyanonymous/ComfyUI.git
# Pin a ComfyUI release tag (e.g. "v0.3.40") for reproducible builds; "master"
# tracks latest.
ARG COMFYUI_REF=master
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

# System deps: Python, git, and the handful of native libs ComfyUI + common
# custom nodes link against (libGL / glib for OpenCV-style image ops).
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-dev python3-venv \
      git ca-certificates curl \
      libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Build into a venv. Ubuntu's system pip is dpkg-managed (no RECORD file), so
# `pip install --upgrade pip` against it fails with "Cannot uninstall pip ...";
# a venv gets its own pip (upgradable) and avoids PEP 668 entirely. This is also
# ComfyUI's own recommended install method.
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Clone ComfyUI into the image. --branch works for a branch or tag; to pin a bare
# commit SHA, add a fetch+checkout step instead.
WORKDIR /opt
RUN git clone --depth 1 --branch "${COMFYUI_REF}" "${COMFYUI_REPO}" comfyui

# PyTorch first (its wheels bundle a self-contained CUDA runtime), then ComfyUI's
# own requirements. `pip` here is the venv's, so the upgrade is safe.
WORKDIR /opt/comfyui
RUN pip install --upgrade pip \
    && pip install torch torchvision torchaudio --index-url "${TORCH_INDEX_URL}" \
    && pip install -r requirements.txt

COPY run.sh /run.sh
RUN chmod +x /run.sh

# The CUDA base image sets no app entrypoint; our script owns PID 1. run.sh calls
# `python3`, which resolves to the venv via the PATH set above.
ENTRYPOINT []
CMD [ "/run.sh" ]
