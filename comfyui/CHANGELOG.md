# Changelog

## 0.1.1

- Fix build failure: install into a venv instead of upgrading Ubuntu's
  dpkg-managed system pip (which failed with "Cannot uninstall pip ...,
  RECORD file not found").
- Drop `build.yaml` (deprecated by the Supervisor); build args now live as
  `ARG`s in the `Dockerfile`.

## 0.1.0

- Initial ComfyUI GPU-AI Universal add-on.
- Universal GPU access via `full_access` + NVIDIA Container Toolkit env vars,
  matching the HAOS GPU-AI host/container split.
- Models, inputs, outputs, and the user directory persisted on `/share/comfyui`.
- Overridable CUDA base image / PyTorch channel / ComfyUI ref via Dockerfile ARGs.
