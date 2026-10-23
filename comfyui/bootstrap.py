#!/usr/bin/env python3
"""First-start bootstrap for the ComfyUI GPU-AI add-on.

Reads the add-on options and, to make image generation plug-and-play:
  * optionally downloads a user-chosen free checkpoint (if none is present), and
  * seeds an API-format workflow into the Home Assistant config dir with
    ckpt_name auto-filled, so the ComfyUI AI Task integration needs only the
    base URL + that path.

Every step is best-effort and non-fatal: ComfyUI still starts if any of this
fails. Paths can be overridden with env vars (used by the test harness).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

OPTIONS = Path(os.environ.get("COMFYUI_OPTIONS", "/data/options.json"))
SHARE = Path(os.environ.get("COMFYUI_SHARE", "/share/comfyui"))
CKPT_DIR = SHARE / "models" / "checkpoints"
TEMPLATE = Path(os.environ.get("COMFYUI_WF_TEMPLATE", "/opt/addon/workflow.template.json"))
# The HA config dir is mounted here when `homeassistant_config:rw` (or the legacy
# `config:rw`) is mapped; HA Core reads the same directory as /config.
HA_CONFIG_CANDIDATES = [
    Path(p) for p in os.environ.get("COMFYUI_HA_CONFIG", "/homeassistant:/config").split(":")
]

# Curated free, no-auth checkpoints. URLs are best-effort; the download is
# non-fatal, so a dead URL just means "add a model yourself". Edit freely.
MODELS = {
    "sd-1.5": (
        "v1-5-pruned-emaonly.safetensors",
        "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/"
        "resolve/main/v1-5-pruned-emaonly.safetensors",
    ),
    "sdxl-base-1.0": (
        "sd_xl_base_1.0.safetensors",
        "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/"
        "resolve/main/sd_xl_base_1.0.safetensors",
    ),
    "sdxl-turbo": (
        "sd_xl_turbo_1.0_fp16.safetensors",
        "https://huggingface.co/stabilityai/sdxl-turbo/"
        "resolve/main/sd_xl_turbo_1.0_fp16.safetensors",
    ),
}


def log(msg: str) -> None:
    print(f"[comfyui-bootstrap] {msg}", flush=True)


def read_options() -> dict:
    try:
        return json.loads(OPTIONS.read_text())
    except Exception as exc:  # missing file, bad JSON, etc.
        log(f"no options read ({exc}); using defaults")
        return {}


def first_checkpoint() -> str | None:
    if not CKPT_DIR.is_dir():
        return None
    for p in sorted(CKPT_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in (".safetensors", ".ckpt") and p.stat().st_size > 0:
            return p.name
    return None


def download_model(key: str) -> str | None:
    if key not in MODELS:
        log(f"unknown model '{key}'; skipping download")
        return None
    fname, url = MODELS[key]
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    dest = CKPT_DIR / fname
    if dest.exists() and dest.stat().st_size > 0:
        log(f"model already present: {fname}")
        return fname
    tmp = CKPT_DIR / (fname + ".part")
    log(f"downloading '{key}' -> {fname} (large; first start only)")
    try:
        subprocess.run(
            ["curl", "-fL", "--retry", "3", "--retry-delay", "5", "-o", str(tmp), url],
            check=True,
        )
        tmp.replace(dest)
        log(f"downloaded {fname}")
        return fname
    except Exception as exc:
        log(f"download failed ({exc}); add a model to {CKPT_DIR} manually")
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return None


def ha_config_dir() -> Path | None:
    for p in HA_CONFIG_CANDIDATES:
        if p.is_dir():
            return p
    return None


def _set_ckpt(doc: dict, name: str) -> None:
    node = doc.get("4")
    if isinstance(node, dict) and node.get("class_type") == "CheckpointLoaderSimple":
        node.setdefault("inputs", {})["ckpt_name"] = name


def seed_workflow(ckpt: str | None) -> None:
    cfg = ha_config_dir()
    if cfg is None:
        log("HA config dir not mapped; skipping workflow seed "
            "(needs `homeassistant_config:rw` in the add-on map)")
        return
    try:
        template = json.loads(TEMPLATE.read_text())
    except Exception as exc:
        log(f"no workflow template ({exc}); skipping seed")
        return

    out_dir = cfg / "comfyui"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "txt2img.api.json"

    if not target.exists():
        if ckpt:
            _set_ckpt(template, ckpt)
        target.write_text(json.dumps(template, indent=2) + "\n")
        log(f"seeded workflow -> {target} (ckpt={ckpt or 'template default'})")
        return

    # Exists: don't clobber a user-edited copy, but repair a dangling ckpt_name
    # (points at a model that isn't on disk) when we have a real one.
    try:
        existing = json.loads(target.read_text())
    except Exception:
        log(f"existing {target} is not valid JSON; leaving untouched")
        return
    cur = existing.get("4", {}).get("inputs", {}).get("ckpt_name") if isinstance(existing, dict) else None
    cur_ok = bool(cur) and (CKPT_DIR / cur).exists()
    if ckpt and not cur_ok:
        _set_ckpt(existing, ckpt)
        target.write_text(json.dumps(existing, indent=2) + "\n")
        log(f"updated ckpt_name in {target} -> {ckpt}")
    else:
        log(f"workflow already present at {target}; leaving untouched")


def main() -> None:
    opts = read_options()
    model = str(opts.get("model", "none")).strip()
    seed = bool(opts.get("seed_workflow", True))

    ckpt = first_checkpoint()
    if model and model != "none":
        downloaded = download_model(model)
        if downloaded:
            ckpt = downloaded
    if ckpt is None:
        log(f"no checkpoint present yet; add a .safetensors to {CKPT_DIR} "
            "or pick a model in the add-on config")

    if seed:
        seed_workflow(ckpt)


if __name__ == "__main__":
    main()
