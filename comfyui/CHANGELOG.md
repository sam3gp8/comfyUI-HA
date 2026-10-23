# Changelog

## 0.2.1

- Fix: validate downloaded checkpoints so a **gated-model agreement page** or an
  error page (served as HTTP 200) is never saved as a model. Files under ~20 MB,
  or whose first bytes look like HTML / an LFS pointer, are rejected and removed
  — and a bogus leftover from an earlier run is auto-cleaned on the next start.
  (Anonymous SDXL-base returned a ~1 KB gate page that 0.2.0 saved as the model.)
- New options: **`hf_token`** (masked) for gated HuggingFace models, and
  **`model_url`** / **`model_filename`** to pull any direct link (HF, Civitai, …),
  which overrides the `model` dropdown.

## 0.2.0

- Plug-and-play first start: the add-on can now download a chosen free
  checkpoint and auto-seed a ready-to-use API workflow, so the ComfyUI AI Task
  integration only needs the base URL + the seeded path.
- New Configuration-tab options: `model` (`none` | `sd-1.5` | `sdxl-base-1.0` |
  `sdxl-turbo`), `seed_workflow`, and `extra_args`.
- Seeds `/config/comfyui/txt2img.api.json` with `ckpt_name` auto-filled from the
  present/downloaded model. Idempotent: never clobbers a user-edited copy, and
  repairs a `ckpt_name` that points at a missing model.
- Maps `homeassistant_config:rw` so the add-on can write that workflow.
- All bootstrap steps are best-effort and non-fatal — ComfyUI still starts if a
  download or seed fails.

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
