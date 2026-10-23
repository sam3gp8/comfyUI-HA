<div align="center">

# 🖼️🤖 ComfyUI for HAOS GPU-AI

**A Home Assistant add-on that runs [ComfyUI](https://github.com/comfyanonymous/ComfyUI) (Stable Diffusion / Flux) on bare-metal GPU — the image-generation companion to the [HAOS GPU-AI](https://github.com/sam3gp8/haos-gpu-ai) host OS and its Ollama add-on.**

[![Platform](https://img.shields.io/badge/platform-x86__64%20bare--metal-blue)](#)
[![Host](https://img.shields.io/badge/requires-HAOS%20GPU--AI-41BDF5)](https://github.com/sam3gp8/haos-gpu-ai)
[![GPU](https://img.shields.io/badge/GPU-NVIDIA%20(default)%20%2F%20AMD%20%2F%20Intel-76B900)](#)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](LICENSE)

</div>

---

This is a Home Assistant **add-on repository**. Add its URL in the HA add-on
store and install **ComfyUI (GPU-AI Universal)** to get a local, private image
generator running on the same GPU that serves your local LLM.

It is the second GPU-accelerated add-on in the HAOS GPU-AI ecosystem:

| Add-on | Serves | Port | Repo |
|--------|--------|------|------|
| Ollama (GPU-AI Universal) | local LLM / Assist conversation agent | `11434` | [`haos-gpu-ai`](https://github.com/sam3gp8/haos-gpu-ai) (`addon-ollama/`) |
| **ComfyUI (GPU-AI Universal)** | **local image generation (SD / Flux)** | **`8188`** | **this repo** |

## The architecture (same split as the host OS)

ComfyUI is **not** compiled into the read-only HAOS rootfs. It runs in an add-on
container that reaches the GPU at bare-metal speed:

| Layer | Responsibility |
|-------|----------------|
| **Host OS** ([`haos-gpu-ai`](https://github.com/sam3gp8/haos-gpu-ai)) | kernel drivers, `/dev` nodes, NVIDIA driver user-space, baked `default-runtime: nvidia`, Container Toolkit injection hook |
| **This add-on** | the compute runtime — PyTorch + its bundled CUDA libs + ComfyUI |

The add-on sets `NVIDIA_VISIBLE_DEVICES=all` + `NVIDIA_DRIVER_CAPABILITIES=compute,utility`,
which is exactly what triggers the host's conditional nvidia runtime to inject
`libcuda` into the container. On an Intel/AMD-only host the same runtime hook
no-ops, and `full_access` still exposes `/dev/dri` / `/dev/kfd` (rebuild with a
ROCm/XPU base for those — see below).

## Quick start

1. **Settings → Add-ons → Add-on store → ⋮ → Repositories**, add:
   ```
   https://github.com/sam3gp8/comfyui-ha
   ```
2. Install & start **ComfyUI (GPU-AI Universal)**. First build is large/slow.
3. Open the web UI (button on the add-on page, or `http://<HA_HOST_IP>:8188`).
4. Put checkpoints in `/share/comfyui/models/checkpoints`.

Full install, model layout, Home Assistant wiring (REST automations and the
`ai_task.generate_image` path), tuning, and non-NVIDIA rebuilds are in
[`comfyui/DOCS.md`](comfyui/DOCS.md).

## Layout

```
comfyui-ha/
├── repository.yaml          # makes this a Home Assistant add-on repository
└── comfyui/
    ├── config.yaml          # add-on manifest (GPU access, port, /share map)
    ├── Dockerfile           # CUDA base → PyTorch → ComfyUI (build args: CUDA / torch / ComfyUI ref)
    ├── run.sh               # entrypoint: GPU probe, /share persistence, launch
    ├── DOCS.md
    └── CHANGELOG.md
```

## Defaults & versions

Defaults target the HAOS GPU-AI reference box (RTX 4090, driver 595.84 / CUDA
13.2). The image uses a CUDA 12.8 base + **`cu130` PyTorch** (ComfyUI 0.42+ needs
cu130 for its optimized CUDA/Triton kernels; the torch wheels bundle their own
CUDA 13 runtime, so the base image version is independent) — all set as `ARG`s at
the top of [`comfyui/Dockerfile`](comfyui/Dockerfile) (`BUILD_FROM`,
`TORCH_INDEX_URL`, `COMFYUI_REF`); edit those to retune. Ubuntu 24.04 (Python
3.12, which ComfyUI targets) is the base.

> **Validated on hardware** (RTX 4090): GPU visible in the container, SDXL base
> auto-downloaded, and the workflow auto-wired. Tune the pins the same way the
> host OS does if you move to a different driver/CUDA line.

## License

[MIT](LICENSE). ComfyUI and Home Assistant are the property of their respective
projects; this repo packages ComfyUI as an add-on and does not redistribute it
(the Dockerfile clones it at build time).
