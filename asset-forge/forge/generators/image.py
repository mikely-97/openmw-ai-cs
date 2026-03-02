"""
Stable Diffusion generator — A1111-compatible API client.

Handles:
  • Reference images (for Hunyuan3D conditioning)
  • Inventory icons
  • Seamless PBR diffuse textures
"""
from __future__ import annotations

import base64
import io
from pathlib import Path

import httpx
from PIL import Image

from ..config import settings


def _post_txt2img(payload: dict) -> Image.Image:
    url = f"{settings.sd_api_url.rstrip('/')}/sdapi/v1/txt2img"
    with httpx.Client(timeout=settings.sd_timeout) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
    data = resp.json()
    img_b64 = data["images"][0]
    return Image.open(io.BytesIO(base64.b64decode(img_b64)))


def _override_checkpoint_if_set(payload: dict) -> dict:
    if settings.sd_model_checkpoint:
        payload["override_settings"] = {
            "sd_model_checkpoint": settings.sd_model_checkpoint,
        }
        payload["override_settings_restore_afterwards"] = True
    return payload


# ── Reference image ────────────────────────────────────────────────────────────

def generate_reference_image(
    prompt: str,
    negative_prompt: str,
    size: int = 512,
    steps: int = 30,
    cfg_scale: float = 7.0,
    output_path: Path | None = None,
) -> Image.Image:
    """
    Generate a clean reference render to feed into Hunyuan3D as conditioning.
    Single object, white/plain background, studio lighting.
    """
    payload = _override_checkpoint_if_set({
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": size,
        "height": size,
        "sampler_name": "DPM++ 2M Karras",
        "batch_size": 1,
    })
    img = _post_txt2img(payload)
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
    return img


# ── Inventory icon ─────────────────────────────────────────────────────────────

def generate_icon(
    prompt: str,
    negative_prompt: str,
    size: int = 128,
    steps: int = 30,
    cfg_scale: float = 7.0,
    output_path: Path | None = None,
) -> Image.Image:
    """
    Generate an inventory icon.
    Converts to RGBA and removes near-white background so OpenMW renders it cleanly.
    """
    # Pad prompt with icon-specific quality tags
    full_prompt = (
        f"{prompt}, game icon, item icon, transparent background, "
        "clean edges, no shadows, flat lighting"
    )
    payload = _override_checkpoint_if_set({
        "prompt": full_prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": size,
        "height": size,
        "sampler_name": "DPM++ 2M Karras",
        "batch_size": 1,
    })
    img = _post_txt2img(payload)

    # Best-effort background removal: convert near-white pixels to transparent.
    img = img.convert("RGBA")
    img = _remove_white_background(img, threshold=240)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="PNG")
    return img


def _remove_white_background(img: Image.Image, threshold: int = 240) -> Image.Image:
    """Simple white-to-alpha conversion. Good enough for studio-lit icon renders."""
    import numpy as np

    data = np.array(img)
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
    white_mask = (r > threshold) & (g > threshold) & (b > threshold)
    data[white_mask, 3] = 0
    return Image.fromarray(data, "RGBA")


# ── Seamless PBR texture ───────────────────────────────────────────────────────

def generate_texture(
    prompt: str,
    negative_prompt: str,
    size: int = 512,
    steps: int = 30,
    cfg_scale: float = 7.0,
    output_path: Path | None = None,
) -> Image.Image:
    """
    Generate a seamless tileable PBR diffuse texture.
    Uses the 'tiling' flag available in A1111.
    """
    full_prompt = (
        f"{prompt}, seamless texture, tileable, PBR diffuse, "
        "no seams, uniform lighting, flat material"
    )
    payload = _override_checkpoint_if_set({
        "prompt": full_prompt,
        "negative_prompt": negative_prompt,
        "steps": steps,
        "cfg_scale": cfg_scale,
        "width": size,
        "height": size,
        "sampler_name": "DPM++ 2M Karras",
        "tiling": True,  # A1111 tiling flag
        "batch_size": 1,
    })
    img = _post_txt2img(payload)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="PNG")
    return img
