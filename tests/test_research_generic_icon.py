import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QTabWidget
from production_zero.core.research import grant_research_points, purchase_research, purchase_specialization, research_catalog
from production_zero.ui.main_window import MainWindow
from production_zero.ui.research_view import ResearchView
from production_zero.ui.resource_art import RESEARCH_GENERIC_ASSET, RESEARCH_GENERIC_ICON, resource_raster_image, _scaled_resource_raster
from production_zero.tools.ui_contact_sheet import _load_qa_fonts


def settle(app):
    for _ in range(6):
        app.processEvents()


def test_generic_asset_has_real_alpha_and_preserves_aspect_ratio():
    image = resource_raster_image(RESEARCH_GENERIC_ICON)
    assert RESEARCH_GENERIC_ASSET.is_file() and image.hasAlphaChannel()
    assert RESEARCH_GENERIC_ASSET.read_bytes()[25] == 6  # RGBA PNG, not RGB.
    assert all(image.pixelColor(x, y).alpha() == 0 for x, y in
               ((0, 0), (image.width()-1, 0), (0, image.height()-1), (image.width()-1, image.height()-1)))
    assert image.pixelColor(image.width() // 2, image.height() // 2).alpha() == 255
    rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    alpha = bytes(rgba.constBits())[3::4]
    assert alpha.count(0) > len(alpha) // 10
    assert alpha.count(255) > len(alpha) // 3
    scaled = _scaled_resource_raster(RESEARCH_GENERIC_ICON, 40, 40)
    assert scaled.width() <= 40 and scaled.height() <= 40
    assert abs(scaled.width() / scaled.height() - image.width() / image.height()) < .03


def test_all_tree_icon_hierarchy_purchase_cache_and_captures():
    app = QApplication.instance() or QApplication([])
    assert app.platformName() == "offscreen"
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    view = window.findChild(ResearchView)
    window.findChild(QTabWidget).setCurrentWidget(view)
    window.resize(1600, 900)
    window.show()
    settle(app)
    for timer in window.findChildren(QTimer):
        timer.stop()
    output = Path("artifacts/ui/research-generic-icon")
    output.mkdir(parents=True, exist_ok=True)
    try:
        for tree_id in research_catalog()[0]:
            view.select_tree(tree_id)
            settle(app)
            for button in view.canvas.buttons.values():
                assert button.icon.resource_id == (button.node.icon_resource if button.major else RESEARCH_GENERIC_ICON)
                assert button.icon.size().toTuple() == ((60, 60) if button.major else (40, 40))
                assert button.icon.pos().toTuple() == ((24, 40) if button.major else (15, 34))
            assert all(button.icon is None for button in view.canvas.specialization_buttons.values())
        grant_research_points(view._state, 50, "Icon QA")
        for tree_id, filename in (("company.general", "01-company"), ("industry.electronics", "02-industry")):
            view.select_tree(tree_id)
            settle(app)
            view.scroll.verticalScrollBar().setValue(100)
            settle(app)
            before = (resource_raster_image.cache_info().misses, _scaled_resource_raster.cache_info().misses)
            geometry = {nid: button.geometry() for nid, button in view.canvas.buttons.items()}
            view._purchase(f"{tree_id}.s1.major")
            view._purchase(f"{tree_id}.s1.n1")
            settle(app)
            assert before == (resource_raster_image.cache_info().misses, _scaled_resource_raster.cache_info().misses)
            assert geometry == {nid: button.geometry() for nid, button in view.canvas.buttons.items()}
            # Capture a fully painted frame rather than a partial backing-store
            # update after the two rapid synthetic purchase clicks.
            view.canvas.update()
            for button in view.canvas.buttons.values():
                button.update()
            settle(app)
            assert window.grab().save(str(output / f"{filename}.png"))
        tree_id = "industry.electronics"
        for node in research_catalog()[1].values():
            if node.tree_id == tree_id and node.row <= 3 and node.id not in view._state.research.unlocked_node_ids:
                purchase_research(view._state, node.id)
        purchase_specialization(view._state, "industry.electronics.specialization.1", "microchip")
        view.refresh()
        view.scroll.verticalScrollBar().setValue(420)
        settle(app)
        slot = view.canvas.specialization_buttons["industry.electronics.specialization.1"]
        assert slot.icon.resource_id == "microchip"
        assert window.grab().save(str(output / "03-selected-product.png"))
        assert view.scroll.horizontalScrollBar().maximum() == 0
    finally:
        window.close()
        window.deleteLater()
        settle(app)
