import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QScrollArea
from production_zero.core.resources import create_resource_inventory
from production_zero.core.state import GameState
from production_zero.data.definitions import load_resource_definitions
from production_zero.ui.charts_view import ChartsView, LineChartWidget
from production_zero.ui.theme import APP_STYLESHEET


@pytest.fixture
def charts():
    app = QApplication.instance() or QApplication([])
    fonts = [QFontDatabase.addApplicationFont(f"C:/Windows/Fonts/{name}") for name in ("segoeui.ttf", "segoeuib.ttf", "bahnschrift.ttf")]
    previous = app.styleSheet()
    app.setStyleSheet(APP_STYLESHEET)
    resources = load_resource_definitions(Path("src/production_zero/data/resource_definitions.json"))
    state = GameState(rng_seed=402, resources=create_resource_inventory(resources))
    view = ChartsView(state, resources)
    view.resize(1280, 760)
    view.show()
    app.processEvents()
    yield view
    view.close()
    view.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.setStyleSheet(previous)
    for font in fonts:
        if font >= 0:
            QFontDatabase.removeApplicationFont(font)


def test_compact_filter_deck_fits_and_preserves_secondary_filters(charts):
    scroll = charts.findChild(QScrollArea, "chartFilterScroll")
    assert scroll.widget().width() <= scroll.viewport().width()
    assert charts._resource_search.parentWidget().objectName() == "chartControlGroup"
    charts._activity_filter.setCurrentText("In Stock")
    charts._resource_search.setText("steel")
    charts._state.resources["steel"].amount = 20
    charts.refresh()
    assert [d.resource_id for d in charts._resources.values() if charts._matches_filters(d)] == ["steel"]
    charts._show_resource_detail("steel")
    charts._show_overview()
    assert charts._activity_filter.currentText() == "In Stock"
    assert charts._resource_search.text() == "steel"


def test_sample_ticks_use_actual_sample_positions():
    assert LineChartWidget._sample_ticks(1) == ((1.0, "0"),)
    assert LineChartWidget._sample_ticks(2) == ((0.0, "1"), (1.0, "0"))
    assert LineChartWidget._sample_ticks(4) == ((0.0, "3"), (1 / 3, "2"), (1.0, "0"))


@pytest.mark.parametrize("values", [[], [0], [10, 10, 10], [40, 58, 73, 95], [1e6, 2e6, 1.5e6]])
def test_chart_axes_and_offscreen_edge_cases(charts, values):
    for metric in ("resource.steel", "rate.production.steel", "rate.consumption.steel"):
        for value in values:
            charts._state.history.append(metric, value)
    charts._show_resource_detail("steel")
    QApplication.processEvents()
    assert charts._stock_chart._axis_unit() == "units"
    assert charts._production_chart._axis_unit() == "units/min"
    assert charts._consumption_chart._axis_unit() == "units/min"
    folder = Path("artifacts/charts-polish")
    folder.mkdir(parents=True, exist_ok=True)
    assert charts.grab().save(str(folder / f"detail-{len(values)}-{int(max(values, default=0))}.png"))
    charts._show_overview()
    QApplication.processEvents()
    assert charts.grab().save(str(folder / "overview.png"))
