# Example workflows

## `txt2img.api.json`

A minimal **API-format** text-to-image workflow (the standard ComfyUI default
graph) for use with the [`Incipiens/ComfyUI-Home-Assistant`](https://github.com/Incipiens/ComfyUI-Home-Assistant)
"ComfyUI AI Task" integration, which fills HA's `ai_task.generate_image`
dropdown.

> **You usually don't need to place this by hand.** With the add-on's
> `seed_workflow` option on (default), the add-on already writes this file to
> `/config/comfyui/txt2img.api.json` with `ckpt_name` filled in from your model —
> just point the integration at that path. This copy is the template it seeds
> from, and a manual fallback.

That integration wants a **file path under `/config/`** pointing at an
**API-format** workflow (it rejects the UI/graph export), and auto-detects the
nodes it drives:

| Role it injects | Node it looks for | In this file |
|-----------------|-------------------|--------------|
| Prompt text (your instructions) | a node with `inputs.text` | node **6** (positive) — also node 7 (negative); pick **6** |
| Resolution (overridden per call) | a node with `inputs.width` + `inputs.height` | node **5** (`EmptyLatentImage`) |
| Seed (randomized per call) | a node with `inputs.seed` | node **3** (`KSampler`) |

### Use it

1. **Have a checkpoint.** Put a model in
   `/share/comfyui/models/checkpoints/` and set node 4's `ckpt_name` to match
   it. The placeholder here is `v1-5-pruned-emaonly.safetensors` (SD 1.5). For
   SDXL, also set the AI Task's width/height to 1024×1024.
2. **Copy this file onto the HA host** somewhere under `/config/`, e.g.
   `/config/comfyui/txt2img.api.json` (use the File Editor / Samba / VS Code
   add-on).
3. In the integration's config, set **Workflow JSON** to that **path**
   (`/config/comfyui/txt2img.api.json`) — not the JSON contents.
4. On the next step, choose **node 6** as the prompt-text node (6 is positive,
   7 is negative); resolution and seed auto-select.

### Guaranteed-correct alternative

Build any text-to-image graph in the ComfyUI web UI (the add-on at
`:8188`) — which fills in your real `ckpt_name` automatically — then
**Save (API Format)** and drop that file under `/config/`. Exporting from your
own instance avoids checkpoint/node-name mismatches.
