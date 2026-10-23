#!/usr/bin/env python3
"""First-start bootstrap for the ComfyUI GPU-AI add-on.

Reads the add-on options and, to make image generation plug-and-play:
  * optionally downloads a checkpoint (a curated free one, or any direct URL
    you supply) if none is present, and
  * seeds an API-format workflow into the Home Assistant config dir with
    ckpt_name auto-filled, so the ComfyUI AI Task integration needs only the
    base URL + that path.

Every step is best-effort and non-fatal: ComfyUI still starts if any of this
fails. Downloads are *validated* so a gated-model gate page or an error page
(served as HTTP 200) is never saved as a checkpoint. Paths can be overridden
with env vars (used by the test harness).
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

OPTIONS = Path(os.environ.get("COMFYUI_OPTIONS", "/data/options.json"))
SHARE = Path(os.environ.get("COMFYUI_SHARE", "/share/comfyui"))
CKPT_DIR = SHARE / "models" / "checkpoints"
TEMPLATE = Path(os.environ.get("COMFYUI_WF_TEMPLATE", "/opt/addon/workflow.template.json"))
# The HA config dir is mounted here when `homeassistant_config:rw` (or the legacy
# `config:rw`) is mapped; HA Core reads the same directory as /config.
HA_CONFIG_CANDIDATES = [
    Path(p) for p in os.environ.get("COMFYUI_HA_CONFIG", "/homeassistant:/config").split(":")
]

# Smallest plausible checkpoint. Real .safetensors models are >1 GB; gate pages
# and LFS pointers are a few KB. Anything under this is treated as "not a model".
MIN_MODEL_BYTES = int(os.environ.get("COMFYUI_MIN_MODEL_BYTES", str(20 * 1024 * 1024)))

# Curated checkpoints. URLs are best-effort; some HuggingFace models are gated
# (they return a ~1 KB agreement page to anonymous requests) and need `hf_token`.
# For anything else, set `model_url` to a direct link (HF, Civitai, …).
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

_HTML_SNIFF = (b"<!doctype", b"<html", b"<?xml", b"{\"error", b"version https://git-lfs")


def log(msg: str) -> None:
    print(f"[comfyui-bootstrap] {msg}", flush=True)


def read_options() -> dict:
    try:
        return json.loads(OPTIONS.read_text())
    except Exception as exc:  # missing file, bad JSON, etc.
        log(f"no options read ({exc}); using defaults")
        return {}


def is_model_file(path: Path) -> bool:
    """A real checkpoint: big enough, and not an HTML/error/LFS-pointer page."""
    try:
        if not path.is_file() or path.stat().st_size < MIN_MODEL_BYTES:
            return False
        with open(path, "rb") as fh:
            head = fh.read(64).lstrip().lower()
        return not any(head.startswith(sig) for sig in _HTML_SNIFF)
    except Exception:
        return False


def first_checkpoint() -> str | None:
    if not CKPT_DIR.is_dir():
        return None
    for p in sorted(CKPT_DIR.iterdir()):
        if p.suffix.lower() in (".safetensors", ".ckpt") and is_model_file(p):
            return p.name
    return None


def _resolve_source(opts: dict) -> tuple[str, str] | None:
    """Return (filename, url) for the chosen model, or None."""
    url = str(opts.get("model_url", "")).strip()
    if url:
        fname = str(opts.get("model_filename", "")).strip() or os.path.basename(urlsplit(url).path)
        if not fname:
            log("model_url set but no filename could be derived; set model_filename")
            return None
        return fname, url
    key = str(opts.get("model", "none")).strip()
    if key and key != "none":
        if key in MODELS:
            return MODELS[key]
        log(f"unknown model '{key}'; skipping download")
    return None


def download_model(fname: str, url: str, token: str = "") -> str | None:
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    dest = CKPT_DIR / fname
    if dest.exists():
        if is_model_file(dest):
            log(f"model already present: {fname}")
            return fname
        # A leftover gate page / truncated file from an earlier run — drop it.
        log(f"removing bogus/undersized {fname} ({dest.stat().st_size} bytes)")
        try:
            dest.unlink()
        except Exception:
            pass

    tmp = CKPT_DIR / (fname + ".part")
    cmd = ["curl", "-fL", "--retry", "3", "--retry-delay", "5"]
    if token:
        cmd += ["-H", f"Authorization: Bearer {token}"]
    cmd += ["-o", str(tmp), url]
    log(f"downloading -> {fname} (large; first start only)")
    try:
        subprocess.run(cmd, check=True)
    except Exception as exc:
        log(f"download failed ({exc}); add a model to {CKPT_DIR} manually")
        _rm(tmp)
        return None

    if not is_model_file(tmp):
        size = tmp.stat().st_size if tmp.exists() else 0
        log(f"downloaded {size} bytes that are not a model (gated page or error?); "
            "discarding. For gated HuggingFace models set `hf_token`, or use "
            "`model_url` for a direct link.")
        _rm(tmp)
        return None

    tmp.replace(dest)
    log(f"downloaded {fname}")
    return fname


def _rm(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except Exception:
        pass


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
    cur_ok = bool(cur) and is_model_file(CKPT_DIR / cur)
    if ckpt and not cur_ok:
        _set_ckpt(existing, ckpt)
        target.write_text(json.dumps(existing, indent=2) + "\n")
        log(f"updated ckpt_name in {target} -> {ckpt}")
    else:
        log(f"workflow already present at {target}; leaving untouched")


def main() -> None:
    opts = read_options()
    seed = bool(opts.get("seed_workflow", True))
    token = str(opts.get("hf_token", "")).strip()

    ckpt = first_checkpoint()
    source = _resolve_source(opts)
    if source and ckpt is None:
        downloaded = download_model(source[0], source[1], token)
        if downloaded:
            ckpt = downloaded
    if ckpt is None:
        log(f"no usable checkpoint yet; add a .safetensors to {CKPT_DIR}, pick a "
            "model, or set model_url in the add-on config")

    if seed:
        seed_workflow(ckpt)


if __name__ == "__main__":
    main()
