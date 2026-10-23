# ComfyUI (GPU-AI Universal)

Runs [ComfyUI](https://github.com/comfyanonymous/ComfyUI) as a Home Assistant
add-on on the **HAOS GPU-AI** host, using the GPU at bare-metal speed via the
same host/container split as the Ollama add-on: the OS provides the driver +
device nodes + the NVIDIA Container Toolkit injection hook; this add-on ships
the PyTorch/CUDA runtime.

> **Requires the HAOS GPU-AI host OS** (`sam3gp8/haos-gpu-ai`). On stock Home
> Assistant OS there is no GPU passthrough and no baked `default-runtime: nvidia`,
> so this add-on will only find the CPU.

## Install

1. In Home Assistant: **Settings → Add-ons → Add-on store → ⋮ → Repositories**,
   add `https://github.com/sam3gp8/comfyui-ha`.
2. Install **ComfyUI (GPU-AI Universal)**. The first build is large (CUDA base
   image + PyTorch) and slow — expect several minutes.
3. **Start** it, then open the **Log** tab. A healthy start prints the detected
   GPU (`nvidia-smi -L`) and `launching ComfyUI on 0.0.0.0:8188`.
4. Use the **OPEN WEB UI** button, or browse to `http://<HA_HOST_IP>:8188`.

`boot: manual` by default — ComfyUI holds VRAM while running and shares the GPU
with Ollama, so it does not auto-start. Set `boot: auto` in `config.yaml` if you
want it always up.

## Plug-and-play first start (options)

On the add-on's **Configuration** tab:

- **`model`** — pick a free, no-auth checkpoint to **auto-download on first
  start if none is present**: `sd-1.5` (~2 GB, fast), `sdxl-base-1.0` (~6.5 GB,
  best quality), `sdxl-turbo` (fast few-step), or `none` (bring your own). The
  download is best-effort and runs before ComfyUI serves, so first start can take
  a while; it only happens once.
- **`seed_workflow`** (default on) — writes a ready-to-use API workflow to
  **`/config/comfyui/txt2img.api.json`** with `ckpt_name` auto-filled from the
  present/downloaded model. It never clobbers a copy you've edited, and repairs a
  `ckpt_name` that points at a model no longer on disk.
- **`extra_args`** — extra ComfyUI CLI flags (e.g. `--lowvram`).

So the fast path is: set **`model`** → start the add-on → the model and the
workflow file are ready. Then all you do on the integration side is point it at
the base URL and that seeded path (below).

## Where models and output live

Everything persists on the Home Assistant `/share` mount, so it survives add-on
rebuilds and updates:

```
/share/comfyui/
├── models/{checkpoints,vae,loras,clip,controlnet,upscale_models,...}
├── input/
├── output/
└── user/            # ComfyUI settings + saved workflows
```

Drop your `.safetensors` checkpoints into `/share/comfyui/models/checkpoints`
(via Samba/SSH add-ons or the file editor), then refresh ComfyUI.

> **Custom nodes** installed through the ComfyUI Manager live inside the image
> and are lost on a rebuild. For now, reinstall them after an update, or bake the
> ones you rely on into the `Dockerfile`.

## Connecting it to Home Assistant

The add-on exposes the standard ComfyUI HTTP + WebSocket API on port `8188`.

**Reaching it from Home Assistant Core** — Core runs in its own container, so
`localhost` does **not** mean the add-on. Use the Home Assistant host address and
the mapped port, e.g. `http://homeassistant.local:8188` or
`http://<HA_HOST_IP>:8188`. (The port is mapped to the host in `config.yaml`.)

There are two ways to actually use it from HA:

1. **REST + automations (works today, no extra integration).** Queue a workflow
   with a `rest_command`/`shell_command` POST to `/prompt` and read the result
   back over the API. See, e.g., this write-up:
   <https://mustafa.net/2026/07/02/comfyui-home-assistant-triggering-image-generation-from-automations/>.

2. **An AI-Task image-generation integration (populates the empty "Image
   generation tasks" dropdown).** Home Assistant's `ai_task.generate_image`
   action needs a custom integration that registers a ComfyUI-backed AI Task
   *entity* and points at `http://<HA_HOST_IP>:8188`. These are third-party and
   still evolving (there is no official first-party ComfyUI AI Task integration
   yet). This add-on only provides the backend API — it does not itself register
   an `ai_task` entity.

   The community one is `Incipiens/ComfyUI-Home-Assistant` ("ComfyUI AI Task")
   via HACS. With the add-on's plug-and-play options (above), its setup is:

   - **Base URL** → the add-on, e.g. `http://homeassistant.local:8188` (not
     `localhost`, per above).
   - **"Workflow JSON"** → the **path** `/config/comfyui/txt2img.api.json`. This
     field is a **file path under `/config/`**, *not* pasted JSON — and with
     `seed_workflow` on (default), the add-on has already written that file for
     you, in API format with your model filled in. (If you'd rather hand-make
     it, the same file is in [`examples/txt2img.api.json`](examples/txt2img.api.json);
     it must be **API format** — the integration rejects the ComfyUI UI/graph
     export.)
   - On the integration's **second step**, pick **node 6** as the prompt-text
     node (6 = positive, 7 = negative; resolution and seed auto-select). Set the
     width/height to suit the model (512×512 for SD 1.5, 1024×1024 for SDXL).

   See [`examples/README.md`](examples/README.md) for the workflow's node map and
   the guaranteed-correct "Save (API Format)" export route from your own ComfyUI.

## Tuning

Most knobs are on the **Configuration** tab (see *Plug-and-play first start*
above): `model`, `seed_workflow`, `extra_args`.

Lower-level defaults live in `environment:` in `config.yaml` and are read by
`run.sh`:

- `COMFYUI_PORT` — listen port (default `8188`).
- `COMFYUI_EXTRA_ARGS` — extra ComfyUI CLI flags; if unset, the `extra_args`
  option is used instead.
- `COMFYUI_SHARE` — persistence base (default `/share/comfyui`).

## Non-NVIDIA GPUs

The default image ships CUDA/PyTorch. The run log warns when it detects an
AMD (`/dev/kfd`) or Intel (`/dev/dri`) GPU instead. For those, rebuild with a
matching base + torch channel by editing the `BUILD_FROM` / `TORCH_INDEX_URL`
`ARG`s at the top of the `Dockerfile`:

- **AMD:** a ROCm base image + ROCm PyTorch wheels (`TORCH_INDEX_URL` → the ROCm
  channel).
- **Intel:** an oneAPI/IPEX base + Intel XPU PyTorch build.
