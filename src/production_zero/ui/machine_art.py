"""Raster artwork for machine and energy card families."""
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter

from production_zero.core.enums import MachineType


MACHINE_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "machines"
MACHINE_RASTER_ASSETS = {
    "solar": MACHINE_ASSET_DIR / "solar_array.png",
    "wind": MACHINE_ASSET_DIR / "wind_turbine.png",
    "coal": MACHINE_ASSET_DIR / "coal_power_plant.png",
    "gas": MACHINE_ASSET_DIR / "gas_power_plant.png",
    "nuclear": MACHINE_ASSET_DIR / "nuclear_power_plant.png",
    "extractor": MACHINE_ASSET_DIR / "extractor.png",
    "drilling": MACHINE_ASSET_DIR / "drilling_rig.png",
    "agriculture": MACHINE_ASSET_DIR / "agriculture.png",
    "fabricator": MACHINE_ASSET_DIR / "fabricator.png",
    "processor": MACHINE_ASSET_DIR / "processor.png",
    "assembler": MACHINE_ASSET_DIR / "assembler.png",
}


MACHINE_RASTER_FALLBACKS: dict[str, str] = {}


MACHINE_TYPE_RASTER_FAMILIES = {
    MachineType.EXTRACTOR: "extractor",
    MachineType.DRILLING: "drilling",
    MachineType.AGRICULTURE: "agriculture",
    MachineType.PROCESSOR: "processor",
    MachineType.FABRICATOR: "fabricator",
    MachineType.ASSEMBLER: "assembler",
}


def machine_art_family_for_machine_type(machine_type: MachineType) -> str:
    """Resolve runtime machine types to canonical raster keys without display-name inference."""
    return MACHINE_TYPE_RASTER_FAMILIES[machine_type]


@lru_cache(maxsize=11)
def _raster_image(family: str) -> QImage:
    path = MACHINE_RASTER_ASSETS[family]
    if not path.exists() and family in MACHINE_RASTER_FALLBACKS:
        path = MACHINE_RASTER_ASSETS[MACHINE_RASTER_FALLBACKS[family]]
    image = QImage(str(path))
    if image.isNull():
        raise RuntimeError(f"Invalid or missing machine raster asset: {path}")
    return image


@lru_cache(maxsize=16)
def _scaled_raster(family: str, width: int, height: int) -> QImage:
    return _raster_image(family).scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def draw_machine_art(painter: QPainter, rect: QRectF, *, family: str, disabled: bool = False) -> None:
    """Fit a complete transparent asset with padding, preserving its aspect ratio."""
    source = _raster_image(family)
    padding = min(rect.width(), rect.height()) * 0.035
    bounds = rect.adjusted(padding, padding, -padding, -padding)
    scaled = _scaled_raster(family, max(1, round(bounds.width())), max(1, round(bounds.height())))
    target = QRectF(
        rect.center().x() - scaled.width() / 2,
        rect.center().y() - scaled.height() / 2,
        scaled.width(),
        scaled.height(),
    )
    painter.save()
    try:
        if disabled:
            painter.setOpacity(painter.opacity() * 0.62)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(target, scaled)
    finally:
        painter.restore()
