"""Vehicle upgrade, pause and resale with existing industrial dialog controls."""

from dataclasses import replace

from PySide6.QtWidgets import QHBoxLayout, QLineEdit

from production_zero.core.machine_operations import pause_machines, sell_machines, resale_value

from production_zero.core.mk_upgrades import mk_upgrade_cost, upgrade_cards

from production_zero.core.commands import UpgradeMachines, SellMachines, PauseMachines, SellFreightBuilding

from production_zero.ui.release_dialogs import IndustrialDialog, confirm, inform

from production_zero.ui.pz_controls import RaisedPZButton





def vehicle_actions(view, card_id):

    from PySide6.QtWidgets import QGridLayout

    from production_zero.ui.game_ui import GameButton, Accent

    from production_zero.ui.freight_lines import ordered_selection, copy_selection, paste_selection

    from production_zero.core.freight import is_freight_card_busy

    if card_id not in view._selected_vehicles:view._slot_interaction._select(card_id)

    ids=ordered_selection(view)

    dialog=IndustrialDialog('Machine actions',f'{len(ids)} selected vehicles. Pause prevents new departures; current deliveries finish normally.',view)

    dialog.accept_button.hide();grid=QGridLayout()

    def route():

        view._open_assignment_view(ids[0], ids)

    def pause():view._command_bus.dispatch(PauseMachines(ids,not all(view._state.cards[cid].paused for cid in ids)));view.refresh_runtime()

    def sale():

        total=sum(resale_value(view._state.cards[cid],view._definitions[view._state.cards[cid].definition_id]) for cid in ids)

        if confirm(view,'Sell vehicles',f'{len(ids)} vehicles will be removed.\nProceeds: ${total:,.2f}','YES – SELL'):

            view._command_bus.dispatch(SellMachines(ids,view._definitions));view._selected_vehicles.clear();view.refresh()

            if callback := getattr(view, '_card_operation_changed', None):
                callback()

    def upgrade():
        from production_zero.ui.freight_upgrade import upgrade_vehicles
        upgrade_vehicles(view, ids)

    def return_to_inventory():
        from production_zero.core.commands import ReturnMachinesToInventory
        view._command_bus.dispatch(ReturnMachinesToInventory(ids))
        view._selected_vehicles.clear()
        view.refresh()
        if callback := getattr(view, '_card_operation_changed', None):
            callback()

    actions=[('ROUTE / DELIVERY TARGET',route),('RESUME' if all(view._state.cards[cid].paused for cid in ids) else 'PAUSE',pause),('COPY',lambda:copy_selection(view)),('PASTE',lambda:paste_selection(view)),('RETURN TO INVENTORY',return_to_inventory),('SELL',sale),('MK UPGRADE',upgrade)]

    for i,(label,callback) in enumerate(actions):

        button=GameButton(label,variant='primary',accent=Accent.DANGER if label=='SELL' else Accent.BUILD);button.setObjectName('machineContextAction');button.setFixedSize(230,48)

        if label=='SELL':button.setEnabled(not any(is_freight_card_busy(view._state.freight,cid) for cid in ids))

        if label in {'SELL', 'RETURN TO INVENTORY'} and any(is_freight_card_busy(view._state.freight,cid) for cid in ids):
            button.setToolTip('A vehicle has an active reserved delivery. Pause and wait for arrival before returning or selling the group.')

        if label=='PASTE':button.setEnabled(bool(view._freight_clipboard))

        def run(callback=callback):

            dialog.accept()

            try:callback()

            except (ValueError,KeyError) as error:inform(view,'Freight',str(error))

        button.clicked.connect(run);grid.addWidget(button,i//2,i%2)

    dialog.layout().itemAt(0).widget().layout().insertLayout(2,grid);dialog.exec();dialog.deleteLater()





def rename_facility(view, facility_id=None):

    from production_zero.ui.interaction_polish import rename_building

    facility = view._state.freight.facilities[facility_id or view._selected_facility_id]

    def apply(name):

        facility.name = name

        view.refresh()

    rename_building(view, facility.name, apply)





def sell_facility(view, facility_id=None):

    from production_zero.core.infrastructure import sell_freight_building

    facility = view._state.freight.facilities[facility_id or view._selected_facility_id]

    if len(view._state.freight.facilities) <= 1:

        inform(view, "Freight building", "Keep one freight building available.")

        return

    ids = tuple(s.card_id for s in facility.slots if s.card_id)

    from production_zero.core.freight import is_freight_card_busy

    if any(is_freight_card_busy(view._state.freight, cid) for cid in ids):

        inform(view, "Freight building", "A vehicle is in transit. Pause and wait for arrival before selling this building.")

        return

    machines = sum(resale_value(view._state.cards[cid], view._definitions[view._state.cards[cid].definition_id]) for cid in ids)

    value = facility.building_investment * .6

    if confirm(view, "Sell building", f"{facility.name}\n{len(ids)} included vehicles will be sold and removed.\nBuilding: ${value:,.2f} · Vehicles: ${machines:,.2f}\nTotal proceeds: ${value + machines:,.2f}", "YES – SELL"):

        view._command_bus.dispatch(SellFreightBuilding(facility.facility_id, view._definitions, True))

        view._selected_facility_id = next(iter(view._state.freight.facilities))

        view.refresh()
