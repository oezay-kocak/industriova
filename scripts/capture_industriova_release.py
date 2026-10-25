"""Render supported resolutions and release interaction states without user saves."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from dataclasses import replace
from pathlib import Path
from PySide6.QtWidgets import QApplication, QTabWidget
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtCore import QTimer
from production_zero.ui.main_window import MainWindow
from production_zero.ui.factory_view_v2 import FactoryViewV2
from production_zero.core.commands import UnlockProductionSlot, BuildFreightFacility
from production_zero.core.supply import buy_common_supply_cards
from production_zero.core.machine_operations import configure_machines
from production_zero.core.enums import CardKind, Rarity
from production_zero.core.cards import create_card_instance
from production_zero.ui.release_dialogs import IndustrialDialog

OUT = Path("artifacts/industriova-stabilization/visuals")


def seed(window):
    board = window.findChild(FactoryViewV2)
    board.pause_simulation()
    state = window._session_state
    definitions = board._definitions
    state.cash.amount = 1e12
    state.company.level = 75
    state.warehouse_capacity = 1e8
    state.production_progress.unlocked_production_ids.update(p.production_id for d in definitions.values() if hasattr(d, "available_production_options") for p in d.available_production_options)
    for rid, stock in state.resources.items():
        stock.amount = 1000.
    for kind, units in (("resources", state.resource_sites), ("energy", state.energy_plants)):
        unit = next(iter(units.values()))
        line = unit.production_lines[0]
        for _ in range(2):
            UnlockProductionSlot(unit.hall_id, line.line_id, kind).apply(state)
    for did, quantity in (("machine.extractor", 3), ("machine.processor", 3), ("machine.fabricator", 2), ("machine.assembler", 1), ("energy.solar_array", 1), ("energy.coal_power_plant", 1), ("energy.gas_power_plant", 1), ("freight.truck", 2)):
        buy_common_supply_cards(state, definitions, did, quantity)
    # UUIDs are intentionally unique, but visual MK/quality fixtures must stay
    # identical across resolutions and reruns.
    ids = [slot.card_id for unit in state.all_production_units() for slot in unit.slots if slot.card_id]
    for index, cid in enumerate(ids):
        card = state.cards[cid]
        definition = definitions[card.definition_id]
        state.cards[cid] = replace(card, mk_level=(1, 2, 10, 50, 99)[index % 5])
        if hasattr(definition, "available_production_options"):
            option = definition.available_production_options[0]
            configure_machines(state, definitions, (cid,), option.production_id)
            state.machine_production[cid].status = "running"
    factory_ids = [cid for cid in ids if state.cards[cid].definition_id in {"machine.processor", "machine.fabricator", "machine.assembler"}]
    for cid, rarity, bonus in zip(factory_ids, (Rarity.LEGENDARY, Rarity.EPIC, Rarity.RARE), (200, 150, 100)):
        original = state.cards[cid]
        quality = create_card_instance(cid, original.definition_id, original.card_kind, rarity, bonus_tenths=bonus)
        state.cards[cid] = replace(quality, mk_level=99, acquisition_cost=original.acquisition_cost)
    board._selected_machines = set(factory_ids)
    state.cards[factory_ids[-1]] = replace(state.cards[factory_ids[-1]], paused=True)
    board._simulation.advance_time(state, 0.)
    for view in (window.findChild(QTabWidget, "mainTabs").widget(i) for i in range(window.findChild(QTabWidget, "mainTabs").count())):
        if hasattr(view, "refresh_view"):
            view.refresh_view()
        elif hasattr(view, "refresh"):
            view.refresh()
    window._global_header.refresh()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    from production_zero.tools.ui_contact_sheet import _load_qa_fonts
    _load_qa_fonts()
    for width, height in ((1366, 768), (1600, 980), (1920, 1080)):
        window = MainWindow(development_mode=False)
        window.resize(width, height)
        window.show()
        app.processEvents()
        window.grab().save(str(OUT / f"empty_{width}x{height}.png"))
        seed(window)
        tabs = window.findChild(QTabWidget, "mainTabs")
        for index in range(tabs.count()):
            tabs.setCurrentIndex(index)
            for _ in range(8):
                app.processEvents()
            if (window.width(), window.height()) != (width, height):
                raise AssertionError(f"Window exceeded target resolution on {tabs.tabText(index)}: {window.size()}")
            window.grab().save(str(OUT / f"{tabs.tabText(index).replace(' ', '_')}_{width}x{height}.png"))
        window._global_resources.toggle()
        window._global_resources.drawer._set_inventory_mode(True)
        for _ in range(8):
            app.processEvents()
        window.grab().save(str(OUT / f"global_resources_{width}x{height}.png"))
        window._global_resources.toggle()
        from production_zero.ui.freight_view import FreightView
        freight = window.findChild(FreightView)
        tabs.setCurrentWidget(freight)
        freight._open_assignment_view(next(iter(window._session_state.installed_freight_card_ids())))
        for _ in range(8):
            app.processEvents()
        window.grab().save(str(OUT / f"freight_configuration_{width}x{height}.png"))
        def capture_browser(name, open_browser):
            def snapshot():
                modal = QApplication.activeModalWidget()
                for _ in range(8):
                    app.processEvents()
                assert modal.width() <= width and modal.height() <= height
                modal.grab().save(str(OUT / f"{name}_{width}x{height}.png"))
                from production_zero.ui.contracts_view import ContractProductPicker
                picker = modal.findChild(ContractProductPicker)
                picker.search.setText('iron')
                app.processEvents()
                modal.grab().save(str(OUT / f"{name}_search_{width}x{height}.png"))
                modal.reject()
            QTimer.singleShot(50, snapshot)
            open_browser()
        from production_zero.ui.research_view import ResearchView
        research = window.findChild(ResearchView)
        tabs.setCurrentWidget(research)
        research.select_tree('industry.metals')
        capture_browser('research_products', research._show_category_products)
        from production_zero.ui.leaderboard_view import LeaderboardView
        leaderboard = window.findChild(LeaderboardView)
        tabs.setCurrentWidget(leaderboard)
        leaderboard._tabs.setCurrentIndex(2)
        capture_browser('production_rankings', leaderboard._open_product_picker)
        dialog = IndustrialDialog("Maschinen verkaufen", "Processor MK99 · Legendary\nErlös: $12,480,000.00\nThe machine will be removed.", window, accept_text="JA – Verkaufen")
        dialog.show()
        app.processEvents()
        dialog.grab().save(str(OUT / f"sale_dialog_{width}x{height}.png"))
        dialog.close()
        from production_zero.core.mk_upgrades import mk_upgrade_cost
        from production_zero.core.supply import common_card_price
        board = window.findChild(FactoryViewV2)
        upgradable = [window._session_state.cards[cid] for cid in board._ordered_selection() if window._session_state.cards[cid].mk_level < 99]
        total = sum(mk_upgrade_cost(card, board._definitions[card.definition_id]) for card in upgradable)
        details = '\n'.join(f"{board._definitions[card.definition_id].name} MK{card.mk_level} → MK{card.mk_level + 1}" for card in upgradable)
        dialog = IndustrialDialog("MK Upgrade", f"{details}\nInputs, output and power scale equally.\nTotal: ${total:,.2f}", window)
        dialog.show()
        app.processEvents()
        dialog.grab().save(str(OUT / f"upgrade_dialog_{width}x{height}.png"))
        dialog.close()
        dialog = IndustrialDialog("Machine purchase", "Processor MK1 · Common\nMachines are installed in compatible free slots.", window, quantity=100, price=common_card_price(board._definitions['machine.processor']))
        dialog.quantity.setValue(42)
        dialog.show()
        app.processEvents()
        dialog.grab().save(str(OUT / f"purchase_dialog_{width}x{height}.png"))
        dialog.close()
        window.close()
        window.deleteLater()
        app.processEvents()
    print(f"Rendered {len(list(OUT.glob('*.png')))} views")


if __name__ == "__main__":
    main()
