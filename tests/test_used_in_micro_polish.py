"""Rendered layout and semantic typography checks for the final micro pass."""
from types import SimpleNamespace
import pytest
from PySide6.QtWidgets import QFrame, QLabel, QWidget, QScrollArea
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.ui.production_board_views import ResourcesViewV2
from production_zero.ui.freight_view import FreightView
from production_zero.ui.secondary_views import ResourceBrowser
from test_final_language_alignment import window, cargo
from test_factory_ui import _app, _install_factory_card_from_selection, _open_production_selection_for_slot


@pytest.mark.parametrize("size", [(1366,768),(1600,980),(1920,1080)])
def test_used_in_left_grid_and_wrap_at_actual_window(window, size):
    window.resize(*size)
    f = window.findChild(FactoryViewV2)
    original = f._guide_recipe_index
    entries = original.used_in("copper")
    for count in (0, 1, 2, 3, "full", "overflow", len(entries)):
        f._guide_recipe_index = original
        f._open_used_in_detail("copper")
        _app().processEvents()
        host = f.findChild(QWidget, "usedInDetailGridHost")
        columns = (host.width() + 14) // 282
        actual_count = columns if count == "full" else columns + 1 if count == "overflow" else count
        f._guide_recipe_index = SimpleNamespace(used_in=lambda rid: entries[:actual_count])
        f._open_used_in_detail("copper")
        for _ in range(4): _app().processEvents()
        host = f.findChild(QWidget, "usedInDetailGridHost")
        rows = host._rows
        columns = max(1, (host.width() + 14) // 282)
        assert (window.width(), window.height()) == size
        assert len(rows) == actual_count
        assert host.property("guideRecipeColumns") == columns
        assert columns >= 2
        if not rows:
            assert host.findChild(QLabel, "emptyStateTitle").text() == "NO DOWNSTREAM PRODUCTS"
        for i, card in enumerate(rows):
            assert (card.width(), card.height()) == (268, 208)
            assert card.x() == (i % columns) * 282
            assert card.y() == (i // columns) * 222
            assert card.geometry().right() < host.width()
        scroll = f.findChild(QScrollArea, "usedInDetailScroll")
        assert scroll.horizontalScrollBar().maximum() == 0
        if actual_count == len(entries):
            assert scroll.verticalScrollBar().maximum() > 0
    f._guide_recipe_index = original


def test_secondary_metadata_roles_and_flow_hierarchy(window):
    f = window.findChild(FactoryViewV2)
    f._open_production_guide()
    _app().processEvents()
    labels = f.findChildren(QLabel)
    metadata = [label for label in labels if label.property("secondaryTextRole") == "metadata"]
    assert metadata
    reference = metadata[0].font()
    assert all(label.font() == reference for label in metadata)
    statuses = [label for label in labels if label.property("secondaryTextRole") == "status"]
    assert statuses and len({label.font().toString() for label in statuses}) == 1
    f._open_chain_from_guide("iron")
    _app().processEvents()
    assert f.findChild(QLabel, "chainInspectorNavLabel") is None
    assert f.findChild(QLabel, "chainInspectorScrollHint") is None
    summary_family = f.findChild(QLabel, "chainSummaryMachineFamily")
    summary_title = f.findChild(QLabel, "chainSummaryProductName")
    assert summary_family.property("secondaryTextRole") is None
    assert summary_family.font().pixelSize() < summary_title.font().pixelSize()
    r = window.findChild(ResourcesViewV2)
    r._on_slot_clicked(0)
    _install_factory_card_from_selection(r, "Extractor")
    _open_production_selection_for_slot(r)
    _app().processEvents()
    assert r.findChild(QLabel, "productionTileCategory").font() == reference
    assert r.findChild(QLabel, "productionTileStage").font() == reference
    g = cargo(window)
    g._state.ensure_resource("steel").amount = 2
    g.refresh_runtime(); _app().processEvents()
    assert g.findChild(QLabel, "freightAssignmentTileMeta").font() == reference
    assert g.findChild(ResourceBrowser)
