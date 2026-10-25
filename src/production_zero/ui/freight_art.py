"""Freight artwork shared by the existing card surfaces."""
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QRectF, QSizeF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


FREIGHT_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "freight"
FREIGHT_RASTER_ASSETS = {
    family: FREIGHT_ASSET_DIR / f"{family}.png"
    for family in ("truck", "train", "ship", "aircraft")
}
FREIGHT_SVG_ASSETS: dict[str, Path] = {}
FREIGHT_ASSETS = {**FREIGHT_RASTER_ASSETS, **FREIGHT_SVG_ASSETS}


@lru_cache(maxsize=4)
def _renderer(family: str) -> QSvgRenderer:
    renderer = QSvgRenderer(str(FREIGHT_SVG_ASSETS[family]))
    if not renderer.isValid():
        raise RuntimeError(f"Invalid or missing Freight SVG: {FREIGHT_SVG_ASSETS[family]}")
    return renderer


@lru_cache(maxsize=1)
def _raster_image(family: str) -> QImage:
    image = QImage(str(FREIGHT_RASTER_ASSETS[family]))
    if image.isNull():
        raise RuntimeError(f"Invalid or missing Freight raster asset: {FREIGHT_RASTER_ASSETS[family]}")
    return image


@lru_cache(maxsize=16)
def _scaled_raster(family: str, width: int, height: int) -> QImage:
    return _raster_image(family).scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def draw_freight_art(painter: QPainter, rect: QRectF, *, family: str, disabled: bool = False) -> None:
    """Fit the complete asset with padding; never crop or stretch."""
    if family in FREIGHT_RASTER_ASSETS:
        source = _raster_image(family)
        padding = min(rect.width(), rect.height()) * 0.035
        bounds = rect.adjusted(padding, padding, -padding, -padding)
        size = QSizeF(source.width(), source.height())
        size.scale(bounds.size(), Qt.AspectRatioMode.KeepAspectRatio)
    else:
        renderer = _renderer(family)
        size = renderer.viewBoxF().size()
        size.scale(rect.size(), Qt.AspectRatioMode.KeepAspectRatio)
    target = QRectF(rect.center().x() - size.width() / 2,
                    rect.center().y() - size.height() / 2, size.width(), size.height())
    painter.save()
    try:
        if disabled:
            painter.setOpacity(painter.opacity() * 0.62)
        if family in FREIGHT_RASTER_ASSETS:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            scaled = _scaled_raster(family, max(1, round(target.width())), max(1, round(target.height())))
            final_target = QRectF(rect.center().x() - scaled.width() / 2,
                                  rect.center().y() - scaled.height() / 2,
                                  scaled.width(), scaled.height())
            painter.drawImage(final_target, scaled)
        else:
            renderer.render(painter, target)
    finally:
        painter.restore()
