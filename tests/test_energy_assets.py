import pytest
import hashlib
from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from production_zero.ui.machine_art import (
    MACHINE_RASTER_ASSETS,
    _raster_image,
    _scaled_raster,
    draw_machine_art,
)


FINAL_ASSET_HASHES = {
    "solar": "81e0c50517f0cdbf8bf30ab29bc58c1b078c7bb351cc2fddfc5f04d5e691750b",
    "wind": "4862b31869a2457c11a8cff231a5eb1be946e71b44a1688730c60b9aa8194fb5",
    "coal": "d7a19751e2baf085cb49d37096befcefdc0b602f9d364df3f389604137f6cc79",
    "gas": "7183a5107ede4064cf2be544cb507ed3d860cecfbdaf2c62564498b104179e0a",
    "nuclear": "d2682eec04b9196e4b871ceba46382be69c8ff2fcb3b17a1cb5b3e7638313403",
    "extractor": "2042db141c0fe5ff3406432d150783b6913078895fbafae8a6eb647ce197bf4a",
    "fabricator": "e8ed368bddccd597315dfb549c73c4a57b92754958c0d9b61b3acdb579b61b76",
    "processor": "72f92ce54c3beace7fcccadffb39409c4c55880d421ddb29c7f7d79d667c419a",
    "assembler": "c6a011e634dce367fe6efed77ac905e9bbced44e7bd9e9172f7ecb6be9a7e6d5",
}


@pytest.mark.parametrize("family", FINAL_ASSET_HASHES)
def test_final_machine_asset_is_exact_transparent_png(family: str) -> None:
    path = MACHINE_RASTER_ASSETS[family]
    assert path.parent.name == "machines"
    assert path.suffix == ".png"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == FINAL_ASSET_HASHES[family]
    image = _raster_image(family)
    assert image.hasAlphaChannel()
    assert min(image.pixelColor(x, y).alpha() for x, y in ((0, 0), (image.width() - 1, 0), (0, image.height() - 1), (image.width() - 1, image.height() - 1))) == 0
    assert all(image.pixelColor(x, 0).alpha() <= 1 for x in range(image.width()))
    assert all(image.pixelColor(x, image.height() - 1).alpha() <= 1 for x in range(image.width()))
    assert all(image.pixelColor(0, y).alpha() <= 1 for y in range(image.height()))
    assert all(image.pixelColor(image.width() - 1, y).alpha() <= 1 for y in range(image.height()))


@pytest.mark.parametrize("family", FINAL_ASSET_HASHES)
def test_machine_raster_pipeline_preserves_aspect_and_target(family: str) -> None:
    QApplication.instance() or QApplication([])
    source = _raster_image(family)
    scaled = _scaled_raster(family, 140, 90)
    assert scaled.width() <= 140 and scaled.height() <= 90
    assert abs(scaled.width() / scaled.height() - source.width() / source.height()) < .03

    canvas = QImage(180, 130, QImage.Format.Format_ARGB32)
    canvas.fill(0)
    painter = QPainter(canvas)
    painter.setOpacity(.8)
    rect = QRectF(15, 12, 150, 100)
    transform = painter.transform()
    draw_machine_art(painter, rect, family=family)
    assert painter.opacity() == .8
    assert painter.transform() == transform
    painter.end()
    pixels = [(x, y) for y in range(canvas.height()) for x in range(canvas.width()) if canvas.pixelColor(x, y).alpha()]
    assert pixels
    assert all(rect.contains(x + .5, y + .5) for x, y in pixels)


def test_extractor_family_uses_the_final_family_asset() -> None:
    from production_zero.data.definitions import load_card_definitions
    from production_zero.ui.factory_view_v2 import prototype_family_for_definition

    definitions = load_card_definitions(Path("src/production_zero/data/game_definitions.json"))
    family = prototype_family_for_definition(definitions["machine.extractor"])
    assert family == "extractor"
    assert MACHINE_RASTER_ASSETS[family].name == "extractor.png"


def test_machine_family_colors_remain_the_existing_pz_colors() -> None:
    from production_zero.ui.game_ui.rendering.factory import _prototype_family_color

    assert _prototype_family_color("extractor", False).name().lower() == "#d8a642"
    assert _prototype_family_color("fabricator", False).name().lower() == "#df6b2f"
    assert _prototype_family_color("processor", False).name().lower() == "#5d94aa"
    assert _prototype_family_color("assembler", False).name().lower() == "#c83a2b"
