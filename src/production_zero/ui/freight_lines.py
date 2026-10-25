"""Freight rows composed from the existing production-board materials."""
from PySide6.QtCore import Qt, QEvent, QObject, QRect, QPoint
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QRubberBand, QApplication, QGridLayout
from production_zero.ui.factory_view_v2 import FactoryV2TrackPanel, FactoryV2LinePlate, FactoryV2ActiveIndicator, _use_transparent_surface
from production_zero.ui.game_ui import GameButton
from production_zero.ui.interaction_polish import pause_button
from production_zero.ui.production_templates import line_menu, paste_dialog
from production_zero.ui.release_dialogs import inform
from production_zero.core.commands import PauseFreightScope
from production_zero.core.production_pause import freight_line_number
from production_zero.core.freight import FREIGHT_FACILITY_START_SLOTS, freight_facility_expansion_cost, freight_expansion_problem
from production_zero.core.production_templates import copy_templates


def ordered_selection(view):
    return tuple(slot.card_id for slot in view._state.freight.facilities[view._selected_facility_id].slots if slot.card_id in view._selected_vehicles)


def copy_selection(view,whole_line=False):
    ids=ordered_selection(view)
    if whole_line or not ids:
        unit=view._state.freight.facilities[view._selected_facility_id]
        ids=tuple(s.card_id for s in unit.slots if s.card_id and freight_line_number(unit,s.index)==view._focused_freight_line)
    try:view._freight_clipboard=copy_templates(view._state,ids)
    except ValueError as error:inform(view,'Copy vehicles',str(error))


def paste_selection(view):
    if view._focused_freight_line is None:
        inform(view,'Paste vehicles','Focus an unlocked target fleet or line first.');return
    paste_dialog(view,view._freight_clipboard,'freight',view._selected_facility_id,view._focused_freight_line)


class FreightLineInput(QObject):
    def __init__(self,view):super().__init__(view);self.view=view;self.start=None;self.rubber=None

    def eventFilter(self,obj,event):
        view=self.view;kind=event.type()
        if kind==QEvent.Type.MouseButtonPress:
            view._focused_freight_line=obj._freight_line_number;obj.setFocus()
            if event.button()==Qt.MouseButton.LeftButton:
                self.start=event.position().toPoint();self.rubber=QRubberBand(QRubberBand.Shape.Rectangle,obj)
                self.rubber.setGeometry(QRect(self.start,self.start));self.rubber.show();return True
        if kind==QEvent.Type.MouseMove and self.start is not None:
            self.rubber.setGeometry(QRect(self.start,event.position().toPoint()).normalized());return True
        if kind==QEvent.Type.MouseButtonRelease and event.button()==Qt.MouseButton.RightButton:
            view._focused_freight_line=obj._freight_line_number
            line_menu(view,lambda:copy_selection(view,True),lambda:paste_selection(view),bool(view._freight_clipboard));return True
        if kind==QEvent.Type.MouseButtonRelease and self.start is not None:
            rect=self.rubber.geometry();indexes=set()
            for card in view._slot_interaction._cards():
                if obj.isAncestorOf(card) and rect.intersects(QRect(card.mapTo(obj,QPoint()),card.size())):indexes.add(card._freight_destination[1])
            view._slot_interaction.select_positions(indexes, bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier))
            view._slot_interaction.update_selection();self.rubber.deleteLater();self.rubber=None;self.start=None;return True
        return False


def build_lines(view,facility):
    scroll=QScrollArea();scroll.setObjectName('freightSlotsScroll');scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    _use_transparent_surface(scroll)
    scroll.viewport().setObjectName('freightSlotsViewport')
    _use_transparent_surface(scroll.viewport())
    scroll.viewport().setStyleSheet('background: transparent; border: 0;')
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet('QScrollArea { background: transparent; border: 0; }');view._slots_scroll=scroll
    host=QWidget();host.setObjectName('freightLinesContent');rows=QVBoxLayout(host);rows.setContentsMargins(0,0,0,14);rows.setSpacing(10)
    _use_transparent_surface(host)
    capacity=facility.line_capacity
    columns=view._slot_grid_columns(capacity);view._slot_grid_column_count=columns
    count=(len(facility.slots)+capacity-1)//capacity
    label={'garage_depot':'FLEET','rail_station':'RAIL LINE','airport':'AIR ROUTE','harbor':'SHIPPING LINE'}[facility.facility_type]
    specs={s[0]:s for s in view._locked_slot_specs(facility)}
    for number in range(count+1):
        panel=FactoryV2TrackPanel(number+1,label);panel.setObjectName('freightBayTrack' if number==0 else 'freightLineTrack');panel.setProperty('lineNumber',number);panel.setProperty('trackAccentActive',False)
        panel.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        panel._freight_line_number=number;panel.installEventFilter(view._line_input)
        box=QVBoxLayout(panel);box.setContentsMargins(12,8,12,12);header=QHBoxLayout();plate=FactoryV2LinePlate(f'{label} {number+1:02d}');plate.setObjectName('freightBayPlate' if number==0 else 'freightLinePlate');header.addWidget(plate)
        # Match the existing warning-plate renderer's font and side insets.
        from PySide6.QtGui import QFontMetricsF
        from production_zero.ui.game_ui.tokens import GAME_UI_TOKENS
        plate_font=GAME_UI_TOKENS.typography.industrial_title();plate_font.setPointSize(15)
        plate.setFixedWidth(max(154, int(QFontMetricsF(plate_font).horizontalAdvance(plate.text()))+50))
        if number<count:
            button=pause_button(view,lambda:(),view._state,view._command_bus,view.refresh_runtime,name='sectorPauseButton',
                                scope=lambda n=number:n in facility.paused_lines,command=lambda paused,n=number:PauseFreightScope(facility.facility_id,paused,n))
            header.addWidget(button)
        header.addStretch(1);indicator=FactoryV2ActiveIndicator();indicator.setProperty('lineNumber',number);indicator.setProperty('lineLocked',number>=count);indicator.setProperty('scopePaused',number>=count or facility.paused or number in facility.paused_lines);indicator.setObjectName('freightBayStatus' if number==0 else 'freightLineStatus');header.addWidget(indicator);box.addLayout(header)
        if number==count:
            next_index=number*capacity
            line_cost=freight_facility_expansion_cost(facility,slot_index=next_index)
            button=GameButton(f'UNLOCK ${line_cost:,.2f}',variant='primary');button.setObjectName('unlockFreightLineButton');button.setProperty('slotIndex',next_index);button.setProperty('slotState','locked');button.setProperty('unlockCost',line_cost);button.setProperty('clickEnabled',len(facility.slots)%capacity==0 and view._state.cash.amount>=line_cost)
            problem = freight_expansion_problem(facility, next_index)
            enabled = not problem and view._state.cash.amount >= line_cost
            button.setEnabled(enabled);button.setProperty('clickEnabled',enabled);button.setFixedSize(186,38)
            button.setToolTip(problem or f'Unlock next line · ${line_cost:,.2f}')
            button.clicked.connect(lambda checked=False,idx=next_index,cost=line_cost,fid=facility.facility_id:view._expand_facility(idx,cost,fid));box.addWidget(button,0,Qt.AlignmentFlag.AlignLeft);panel.setMinimumHeight(112)
        else:
            grid_host=QWidget();grid_host.setObjectName('freightSlotGridHost');_use_transparent_surface(grid_host);grid_host._freight_line_number=number;grid_host.installEventFilter(view._line_input)
            slots=QGridLayout(grid_host);slots.setContentsMargins(0,0,0,0);slots.setSpacing(8)
            for index in range(number*capacity,(number+1)*capacity):
                if index in facility.unlocked_slot_indexes():card=view._build_slot_card(index,facility.slots[index].card_id)
                else:
                    spec=specs.get(index)
                    if spec is None:continue
                    card=view._build_locked_slot_card(*spec)
                offset=index-number*capacity;slots.addWidget(card,offset//columns,offset%columns)
            slots.setColumnStretch(columns,1);box.addWidget(grid_host);panel.setMinimumHeight(50+((capacity+columns-1)//columns)*272)
        rows.addWidget(panel)
    host.setMinimumHeight(sum(rows.itemAt(i).widget().minimumHeight() for i in range(rows.count()))+rows.spacing()*count+14);rows.addStretch(1);scroll.setWidget(host)
    return scroll
