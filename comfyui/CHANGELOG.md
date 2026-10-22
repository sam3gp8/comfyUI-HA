# Changelog

## 0.1.0

- Initial ComfyUI GPU-AI Universal add-on.
- Universal GPU access via `full_access` + NVIDIA Container Toolkit env vars,
  matching the HAOS GPU-AI host/container split.
- Models, inputs, outputs, and the user directory persisted on `/share/comfyui`.
- Overridable CUDA base image / PyTorch channel / ComfyUI ref via `build.yaml`.
