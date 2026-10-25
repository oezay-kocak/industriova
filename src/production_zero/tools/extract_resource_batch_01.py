"""Extract the approved resource artwork from the first fixed batch image.

This is a deterministic technical extraction.  It never synthesizes pixels: the
RGB channels come directly from the supplied source and only the alpha canvas is
created here.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


SOURCE = Path.home() / 'Downloads/ChatGPT Image 7. Sept. 2026, 23_09_40.png'
ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "resources"


@dataclass(frozen=True, slots=True)
class Extraction:
    resource_id: str
    crop: tuple[int, int, int, int]
    threshold: int
    seed_bottom: bool = True
    largest_component_only: bool = False


EXTRACTIONS = (
    Extraction("iron_ore", (20, 135, 420, 410), 10),
    Extraction("coal", (410, 150, 810, 410), 10),
    Extraction("quartz", (800, 135, 1180, 415), 11),
    Extraction("wheat", (1180, 135, 1500, 415), 12),
    Extraction("crude_oil", (60, 490, 410, 760), 10),
    Extraction("bauxite", (390, 500, 820, 750), 11),
    Extraction("sulfur", (795, 495, 1160, 750), 11),
    # The approved Copper Ore motif meets the source's lower edge.  Do not use
    # that edge as a background seed, so every supplied artwork pixel survives.
    Extraction(
        "copper_ore",
        (480, 760, 950, 1024),
        10,
        seed_bottom=False,
        largest_component_only=True,
    ),
)


def _background_from_edges(rgb: np.ndarray, threshold: int, *, seed_bottom: bool) -> np.ndarray:
    """Flood smooth background gradients from the crop perimeter."""
    height, width, _ = rgb.shape
    background = np.zeros((height, width), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def seed(x: int, y: int) -> None:
        if not background[y, x]:
            background[y, x] = True
            queue.append((x, y))

    for x in range(width):
        seed(x, 0)
        if seed_bottom:
            seed(x, height - 1)
    for y in range(height):
        seed(0, y)
        seed(width - 1, y)

    rgb16 = rgb.astype(np.int16)
    while queue:
        x, y = queue.popleft()
        current = rgb16[y, x]
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if nx < 0 or ny < 0 or nx >= width or ny >= height or background[ny, nx]:
                continue
            delta = np.abs(rgb16[ny, nx] - current)
            if int(delta.max()) <= threshold and int(delta.sum()) <= threshold * 2:
                background[ny, nx] = True
                queue.append((nx, ny))
    return background


def _drop_small_islands(mask: np.ndarray, minimum: int = 18) -> np.ndarray:
    """Remove tiny background-texture islands without losing artwork fragments."""
    height, width = mask.shape
    seen = np.zeros_like(mask)
    result = np.zeros_like(mask)
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or seen[y, x]:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            component: list[tuple[int, int]] = []
            while stack:
                cx, cy = stack.pop()
                component.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if len(component) >= minimum:
                for cx, cy in component:
                    result[cy, cx] = True
    return result


def _largest_component(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    seen = np.zeros_like(mask)
    largest: list[tuple[int, int]] = []
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or seen[y, x]:
                continue
            stack = [(x, y)]
            seen[y, x] = True
            component: list[tuple[int, int]] = []
            while stack:
                cx, cy = stack.pop()
                component.append((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((nx, ny))
            if len(component) > len(largest):
                largest = component
    result = np.zeros_like(mask)
    for x, y in largest:
        result[y, x] = True
    return result


def extract(entry: Extraction, source: Image.Image) -> Image.Image:
    crop = source.crop(entry.crop).convert("RGB")
    rgb = np.asarray(crop)
    background = _background_from_edges(rgb, entry.threshold, seed_bottom=entry.seed_bottom)
    foreground = _drop_small_islands(~background)
    if entry.largest_component_only:
        foreground = _largest_component(foreground)
    alpha = Image.fromarray((foreground * 255).astype(np.uint8), "L").filter(
        ImageFilter.GaussianBlur(0.65)
    )
    rgba = crop.convert("RGBA")
    rgba.putalpha(alpha)

    bbox = alpha.getbbox()
    if bbox is None:
        raise RuntimeError(f"Extraction produced an empty asset: {entry.resource_id}")
    artwork = rgba.crop(bbox)
    fitted = artwork.copy()
    fitted.thumbnail((430, 430), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((512 - fitted.width) // 2, (512 - fitted.height) // 2))
    return canvas


def main() -> None:
    source = Image.open(SOURCE).convert("RGB")
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for entry in EXTRACTIONS:
        extract(entry, source).save(ASSET_DIR / f"{entry.resource_id}.png", optimize=True)


if __name__ == "__main__":
    main()
