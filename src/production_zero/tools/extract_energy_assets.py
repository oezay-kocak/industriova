"""Extract five transparent energy assets from the supplied contact image."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path.home() / 'Downloads/ChatGPT Image 7. Sept. 2026, 16_01_31.png'
OUTPUT = ROOT / "src" / "production_zero" / "assets" / "energy"
QA = ROOT / "artifacts" / "energy_asset_extraction"

# Crops contain only the illustration field, never the frame or label.
SPECS = {
    "coal_power_plant": (42, 43, 482, 444),
    "gas_power_plant": (548, 55, 982, 444),
    "nuclear_power_plant": (1052, 42, 1493, 444),
    "solar_array": (280, 614, 733, 927),
    "wind_turbine": (806, 525, 1252, 933),
}


def _grabcut(crop: np.ndarray, name: str) -> np.ndarray:
    height, width = crop.shape[:2]
    if name == "wind_turbine":
        return _wind_mask(crop)
    mask = np.full((height, width), cv2.GC_PR_BGD, np.uint8)
    mask[4:-4, 4:-4] = cv2.GC_PR_FGD
    mask[:4] = mask[-4:] = cv2.GC_BGD
    mask[:, :4] = mask[:, -4:] = cv2.GC_BGD

    # Certain object cores guide GrabCut while leaving every edge data-driven.
    seeds: dict[str, list[tuple[int, int, int, int]]] = {
        "coal_power_plant": [(15, 230, width - 12, height - 6), (48, 90, 70, 260), (90, 105, 220, 300), (260, 165, 370, 310)],
        "gas_power_plant": [(8, 205, width - 8, height - 5), (65, 65, 305, 330), (285, 205, 405, 370)],
        "nuclear_power_plant": [(8, 220, width - 8, height - 5), (35, 120, 270, 330), (250, 110, 395, 335)],
        "solar_array": [(5, 25, width - 5, height - 35)],
        "wind_turbine": [(15, 5, width - 12, height - 18)],
    }
    for x1, y1, x2, y2 in seeds[name]:
        mask[y1:y2, x1:x2] = cv2.GC_PR_FGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(crop, mask, None, bgd, fgd, 8, cv2.GC_INIT_WITH_MASK)
    binary = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    cleaned = np.zeros_like(binary)
    for index in range(1, count):
        if stats[index, cv2.CC_STAT_AREA] >= 18:
            cleaned[labels == index] = 255
    alpha = cv2.GaussianBlur(cleaned, (0, 0), 0.65)
    alpha[alpha < 8] = 0
    alpha[alpha > 247] = 255
    return alpha


def _wind_mask(crop: np.ndarray) -> np.ndarray:
    height, width = crop.shape[:2]
    candidate = np.zeros((height, width), np.uint8)
    certain = np.zeros_like(candidate)
    rotors = (
        ((87, 208), ((77, 135), (21, 254), (157, 253))),
        ((237, 125), ((87, 108), (305, 13), (296, 260))),
        ((383, 206), ((399, 126), (305, 212), (429, 271))),
    )
    for hub, tips in rotors:
        for tip in tips:
            cv2.line(candidate, hub, tip, 30, cv2.LINE_AA)
            cv2.line(certain, hub, tip, 3, cv2.LINE_AA)
        cv2.circle(candidate, hub, 22, 255, -1, cv2.LINE_AA)
        cv2.circle(certain, hub, 5, 255, -1, cv2.LINE_AA)
    towers = (
        np.array(((80, 205), (94, 205), (100, 342), (76, 342)), np.int32),
        np.array(((225, 120), (249, 120), (263, 384), (211, 384)), np.int32),
        np.array(((376, 202), (391, 202), (400, 346), (369, 346)), np.int32),
    )
    tower_cores = (
        np.array(((84, 208), (91, 208), (95, 336), (81, 336)), np.int32),
        np.array(((231, 126), (244, 126), (251, 378), (220, 378)), np.int32),
        np.array(((380, 207), (388, 207), (394, 340), (374, 340)), np.int32),
    )
    for broad, core in zip(towers, tower_cores, strict=True):
        cv2.fillPoly(candidate, [broad], 255)
        cv2.fillPoly(certain, [core], 255)
    cv2.rectangle(candidate, (182, 295), (326, 397), 255, -1)
    cv2.rectangle(certain, (194, 310), (315, 390), 255, -1)

    mask = np.full((height, width), cv2.GC_BGD, np.uint8)
    mask[candidate > 0] = cv2.GC_PR_FGD
    mask[certain > 0] = cv2.GC_FGD
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(crop, mask, None, bgd, fgd, 10, cv2.GC_INIT_WITH_MASK)
    binary = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    alpha = cv2.GaussianBlur(binary, (0, 0), 0.6)
    alpha[alpha < 8] = 0
    alpha[alpha > 247] = 255
    return alpha


def extract() -> None:
    source = cv2.imread(str(SOURCE), cv2.IMREAD_UNCHANGED)
    if source is None:
        raise RuntimeError(f"Cannot read {SOURCE}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    for name, (x1, y1, x2, y2) in SPECS.items():
        crop = source[y1:y2, x1:x2, :3].copy()
        alpha = _grabcut(crop, name)
        if name == "wind_turbine":
            edge = (alpha > 0) & (alpha < 255)
            blue_fringe = edge & (crop[:, :, 0].astype(np.int16) > crop[:, :, 2].astype(np.int16) + 18)
            neutral = crop.min(axis=2)
            crop[blue_fringe] = np.repeat(neutral[:, :, None], 3, axis=2)[blue_fringe]
        rgba = cv2.cvtColor(crop, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = alpha
        points = cv2.findNonZero(alpha)
        x, y, width, height = cv2.boundingRect(points)
        pad = 10
        left, top = max(0, x - pad), max(0, y - pad)
        right, bottom = min(rgba.shape[1], x + width + pad), min(rgba.shape[0], y + height + pad)
        result = rgba[top:bottom, left:right]
        if not cv2.imwrite(str(OUTPUT / f"{name}.png"), result):
            raise RuntimeError(f"Cannot write {name}")


def qa() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    tile_w, tile_h = 300, 250
    sheet = np.zeros((tile_h * 2 + 70, tile_w * 5 + 40, 4), np.uint8)
    sheet[:, :, 3] = 255
    sheet[: tile_h + 35, :, :3] = (28, 31, 33)
    sheet[tile_h + 35 :, :, :3] = (230, 232, 228)
    report = {}
    for column, name in enumerate(SPECS):
        image = cv2.imread(str(OUTPUT / f"{name}.png"), cv2.IMREAD_UNCHANGED)
        assert image is not None and image.shape[2] == 4
        scale = min((tile_w - 28) / image.shape[1], (tile_h - 42) / image.shape[0])
        size = (max(1, round(image.shape[1] * scale)), max(1, round(image.shape[0] * scale)))
        resized = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
        for row, base_y in enumerate((28, tile_h + 52)):
            x = 20 + column * tile_w + (tile_w - resized.shape[1]) // 2
            y = base_y + (tile_h - 38 - resized.shape[0]) // 2
            target = sheet[y:y + resized.shape[0], x:x + resized.shape[1]]
            alpha = resized[:, :, 3:4].astype(np.float32) / 255
            target[:, :, :3] = (resized[:, :, :3] * alpha + target[:, :, :3] * (1 - alpha)).astype(np.uint8)
        alpha = image[:, :, 3]
        points = cv2.findNonZero(alpha)
        x, y, width, height = cv2.boundingRect(points)
        bounds = [int(x), int(y), int(x + width - 1), int(y + height - 1)]
        assert bounds[0] > 0 and bounds[1] > 0
        assert bounds[2] < image.shape[1] - 1 and bounds[3] < image.shape[0] - 1
        report[name] = {
            "size": [int(image.shape[1]), int(image.shape[0])],
            "alpha_min": int(alpha.min()),
            "alpha_max": int(alpha.max()),
            "transparent_pixels": int(np.count_nonzero(alpha == 0)),
            "partial_alpha_pixels": int(np.count_nonzero((alpha > 0) & (alpha < 255))),
            "alpha_bounds": bounds,
            "transparent_padding": True,
        }
    cv2.imwrite(str(QA / "energy_assets_dark_light_qa.png"), sheet[:, :, :3])
    (QA / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("extract", "qa", "all"), default="all", nargs="?")
    args = parser.parse_args()
    if args.action in {"extract", "all"}:
        extract()
    if args.action in {"qa", "all"}:
        qa()
    print(OUTPUT)


if __name__ == "__main__":
    main()
