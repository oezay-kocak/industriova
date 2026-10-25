import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import Qt, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTabWidget, QFrame, QScrollArea
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.main_window import MainWindow
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.contract_product import ContractProductButton
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.ui.research_view import ResearchView
from production_zero.core.progression import production_options
from production_zero.core.consortium import OPEN


@pytest.mark.parametrize("size", [(1366,768), (1600,980), (1920,1080)])
def test_shared_products_quantities_geometry_and_contract_semantics(size):
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    window = MainWindow(development_mode=False)
    try:
        window.resize(*size)
        window.show()
        tabs = window.findChild(QTabWidget)
        view = window.findChild(ContractsView)
        tabs.setCurrentWidget(view)
        for option in production_options(view._definitions):
            view._state.production_progress.unlocked_production_ids.add(option.production_id)
            view._state.ensure_resource(option.output_resource).amount = 25
        view.refresh()
        for controls in list(view._selection_controls.values()):
            for i, combo in enumerate(controls["combos"]):
                combo.setCurrentIndex(i + 1)
        for _ in range(4):
            app.processEvents()
        assert (window.width(), window.height()) == size
        assert view._board_scroll.horizontalScrollBar().maximum() == 0
        if size[1] >= 980:
            assert view._board_scroll.verticalScrollBar().maximum() == 0
        for card in view.findChildren(QFrame, "contractCard"):
            products = card.findChild(QFrame, "contractRequirements")
            rewards = card.findChild(QFrame, "contractRewards")
            assert products.geometry().bottom() < rewards.geometry().top()
            for button in card.findChildren(ContractProductButton):
                assert button.icon is not None
                assert button.rect().contains(button.amount.geometry())
                assert button.amount.fontMetrics().horizontalAdvance(button.amount.text()) <= button.amount.width()
                assert button.amount.property("requiredAmount") > 0
        consortium = window.findChild(ConsortiumView)
        guild = consortium._service.create("UI Test Union", OPEN, 1)
        consortium.refresh()
        tabs.setCurrentWidget(consortium)
        for kind, count in (("daily", 3), ("weekly", 4)):
            consortium._draft_products[kind] = list(consortium._service.contract_candidates(guild.consortium_id, kind)[:count])
            consortium._open_contract(kind)
            for _ in range(4):
                app.processEvents()
            section = consortium.contracts_layout.itemAt(0 if kind == "daily" else 1).widget()
            modules = [m for m in section.findChildren(ContractProductButton) if m.isVisible()]
            assert len(modules) == count
            expected = consortium._service.preview_contract(guild.consortium_id, kind, tuple(consortium._draft_products[kind]))
            assert {m.property("resourceId"): m.amount.property("requiredAmount") for m in modules} == expected
            assert consortium.contracts_page.horizontalScrollBar().maximum() == 0
        research = window.findChild(ResearchView)
        assert len(research.navigation_buttons) == 21
        tabs.setCurrentWidget(research)
        research.navigation_scroll.verticalScrollBar().setValue(research.navigation_scroll.verticalScrollBar().maximum())
        app.processEvents()
        assert research.navigation_scroll.horizontalScrollBar().maximum() == 0
    finally:
        window.close()
        window.deleteLater()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_contract_product_button_keyboard_empty_selected_and_disabled():
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    button = ContractProductButton("PRODUCT 1")
    button.resize(180, 62)
    button.show()
    clicks = []
    button.clicked.connect(lambda: clicks.append(True))
    assert not button.property("selected")
    button.set_product("iron_ore", "A long resource name for a narrow compact module", 12500)
    app.processEvents()
    assert button.icon is not None and button.property("selected")
    assert "12,500" in button.accessibleName()
    button.setFocus()
    QTest.keyClick(button, Qt.Key.Key_Space)
    assert len(clicks) == 1
    button.setEnabled(False)
    QTest.keyClick(button, Qt.Key.Key_Space)
    assert len(clicks) == 1
    button.close()
    button.deleteLater()
