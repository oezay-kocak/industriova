"""Five focused offscreen captures for the Playtest-2 consistency follow-up."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QTabWidget

from production_zero.core.cards import create_card_instance
from production_zero.core.commands import AddCard, AddCash, InstallCardInHall
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.packs import DAILY_MINI_PACK, grant_pack
from production_zero.tools.ui_contact_sheet import _load_qa_fonts
from production_zero.ui.contracts_view import ContractsView
from production_zero.ui.event_feed import EventFeedWidget, FeedEvent
from production_zero.ui.factory_view import ProductionSelectionTile
from production_zero.ui.main_window import MainWindow
from production_zero.ui.packs_view import PacksView
from production_zero.ui.production_board_views import ResourcesViewV2
from production_zero.ui.supply_view import SupplyView

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "artifacts" / "ui" / "playtest2-consistency-followup"


def settle(app, ms=0):
    if ms:
        QTest.qWait(ms)
    for _ in range(8):
        app.processEvents()


def save(widget, app, name):
    settle(app)
    path = OUTPUT / name
    assert widget.grab().save(str(path))
    return path


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    captures = []
    window = MainWindow(development_mode=True)
    window.resize(1600, 900)
    window.show()
    feed = window.findChild(EventFeedWidget, "eventFeed")
    feed.push(FeedEvent("xp", "Company Progress", 24))
    feed.push(FeedEvent("cash", "Coal Delivery", 480))
    feed.flush_pending()
    for _ in range(80):
        feed._advance_ticker()
    captures.append(save(window, app, "01_navigation_moving_ticker_dev.png"))

    contracts = window.findChild(ContractsView)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(contracts)
    contracts._state.production_progress.unlocked_production_ids.add("recipe.processor.steel")
    contracts._state.ensure_resource("steel").amount = 1
    contracts.refresh()
    slot = contracts.findChild(QPushButton, "contractProductSlot")
    slot.click()
    settle(app)
    captures.append(save(contracts._product_picker, app, "02_contract_visual_product_picker.png"))
    contracts._product_picker.close()

    supply = window.findChild(SupplyView)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(supply)
    supply.findChildren(QPushButton, "supplySectionButton")[1].click()
    supply._bus.dispatch(AddCash(50_000))
    supply.refresh()
    x4 = next(chip for chip in supply.findChildren(QPushButton, "supplyFilterChip") if chip.property("filterGroup") == "buy" and chip.text() == "X4")
    x4.click()
    captures.append(save(window, app, "03_industrial_supply_x4_total.png"))

    resources = window.findChild(ResourcesViewV2)
    card = create_card_instance("qa-drilling", "machine.drilling", CardKind.MACHINE, Rarity.COMMON)
    resources._command_bus.dispatch(AddCard(card))
    resources._command_bus.dispatch(InstallCardInHall("site-1", 0, card.card_id))
    resources._open_production_drawer(card.card_id)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(resources)
    captures.append(save(window, app, "04_machine_picker_next_locked.png"))

    packs = window.findChild(PacksView)
    pack_id = grant_pack(packs._state, DAILY_MINI_PACK, "qa-followup")
    packs.refresh(force=True)
    window.findChild(QTabWidget, "mainTabs").setCurrentWidget(packs)
    packs._open_pack(pack_id, "general")
    packs._deal_timer.stop()
    packs._focus.hide()
    for reveal in packs._reveal_cards:
        reveal.deal()
        reveal.reveal()
    settle(app, 550)
    captures.append(save(window, app, "05_pack_reveal_neutral_canonical_icons.png"))
    window.close()
    print("\n".join(str(path) for path in captures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
