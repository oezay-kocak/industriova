import hashlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from production_zero.ui.freight_art import (
    FREIGHT_ASSETS,
    FREIGHT_RASTER_ASSETS,
    _raster_image,
    _scaled_raster,
    draw_freight_art,
)


@pytest.mark.parametrize("family", FREIGHT_ASSETS)
@pytest.mark.parametrize("disabled", (False, True))
def test_small_freight_art_stays_in_target_and_preserves_painter(family, disabled):
    app = QApplication.instance() or QApplication([])
    image = QImage(120, 100, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    painter.setOpacity(.8)
    rect = QRectF(10, 10, 98, 79.64)
    transform = painter.transform()
    draw_freight_art(painter, rect, family=family, disabled=disabled)
    assert painter.opacity() == .8
    assert painter.transform() == transform
    painter.end()
    pixels = [(x, y) for y in range(100) for x in range(120) if image.pixelColor(x, y).alpha()]
    assert len(pixels) > 900
    assert all(rect.contains(x + .5, y + .5) for x, y in pixels)


def test_truck_uses_the_exact_transparent_golden_sample_png():
    path = FREIGHT_RASTER_ASSETS["truck"]
    assert path == FREIGHT_ASSETS["truck"]
    assert path.suffix == ".png"
    assert not path.with_suffix(".svg").exists()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "ef243c4bf902e28c2522fa4847bf3fdfb1637e0da6d1415cb89027ed3d5aa39e"
    image = _raster_image("truck")
    assert image.size().toTuple() == (1721, 914)
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0
    scaled = _scaled_raster("truck", 97, 79)
    assert scaled.width() <= 97 and scaled.height() <= 79
    assert abs(scaled.width() / scaled.height() - image.width() / image.height()) < .03


def test_train_uses_the_exact_transparent_golden_sample_png():
    path = FREIGHT_RASTER_ASSETS["train"]
    assert path == FREIGHT_ASSETS["train"]
    assert path.suffix == ".png"
    assert not path.with_suffix(".svg").exists()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "d1d218fe910710424f7681a7ba5a783f749b78d500b47a6e3236cbd64bd4c3f2"
    image = _raster_image("train")
    assert image.size().toTuple() == (1721, 914)
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0
    scaled = _scaled_raster("train", 97, 79)
    assert scaled.width() <= 97 and scaled.height() <= 79
    assert abs(scaled.width() / scaled.height() - image.width() / image.height()) < .03


def test_train_family_uses_the_primary_pz_red():
    from production_zero.ui.game_ui.rendering.factory import _prototype_family_color
    from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS
    from production_zero.ui.theme import APP_STYLESHEET, Theme

    assert GAME_UI_TOKENS.colors.train == GAME_UI_TOKENS.colors.area_anchor_red == "#c83a2b"
    assert Theme.TRAIN == "#c83a2b"
    assert _prototype_family_color("train", False).name().lower() == "#c83a2b"


def test_aircraft_uses_the_exact_transparent_final_png():
    path = FREIGHT_RASTER_ASSETS["aircraft"]
    assert path == FREIGHT_ASSETS["aircraft"]
    assert path.suffix == ".png"
    assert not path.with_suffix(".svg").exists()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "45a9622e78a5f508120914038afd7868c89c9ea218128ab688369bcf61213f09"
    image = _raster_image("aircraft")
    assert image.size().toTuple() == (1721, 914)
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0
    scaled = _scaled_raster("aircraft", 97, 79)
    assert scaled.width() <= 97 and scaled.height() <= 79
    assert abs(scaled.width() / scaled.height() - image.width() / image.height()) < .03


def test_aircraft_family_keeps_its_existing_violet_identity():
    from production_zero.ui.game_ui.rendering.factory import _prototype_family_color

    assert _prototype_family_color("aircraft", False).name().lower() == "#9bb8ef"


def test_ship_uses_the_exact_transparent_final_png():
    path = FREIGHT_RASTER_ASSETS["ship"]
    assert path == FREIGHT_ASSETS["ship"]
    assert path.suffix == ".png"
    assert not path.with_suffix(".svg").exists()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "21e5b3d9522a92d1a5e6d99d7b6806ad0575919d86db65cf06b8b3145e734159"
    image = _raster_image("ship")
    assert image.size().toTuple() == (1721, 914)
    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0
    scaled = _scaled_raster("ship", 97, 79)
    assert scaled.width() <= 97 and scaled.height() <= 79
    assert abs(scaled.width() / scaled.height() - image.width() / image.height()) < .03


def test_ship_family_keeps_its_existing_cyan_identity():
    from production_zero.ui.game_ui.rendering.factory import _prototype_family_color
    from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS

    assert GAME_UI_TOKENS.colors.storage == "#25b9e8"
    assert _prototype_family_color("ship", False).name().lower() == "#25b9e8"
