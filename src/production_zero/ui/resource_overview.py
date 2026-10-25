"""Production plans and measured Freight rates on responsive resource cards."""
from PySide6.QtCore import QEvent, QRect
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
from production_zero.core.analytics import calculate_resource_flows, ResourceFlow
from production_zero.core.research import research_products
from production_zero.ui.material_frame import MaterialFrame
from production_zero.ui.game_ui import MaterialLevel
from production_zero.ui.resource_categories import research_category
from production_zero.ui.resource_icons import ResourceIconWidget, resource_icon_key, resource_accent_key
from production_zero.ui.resource_prices import base_price_text, price_tooltip
from production_zero.ui.resource_tiles import ElidedResourceLabel
from production_zero.ui.widget_lifecycle import hide_detach_delete

CARD_HEIGHT = 244
CARD_GAP = 8
ROW_PITCH = CARD_HEIGHT + CARD_GAP


class ResourceOverviewCard(MaterialFrame):
    def __init__(self, state, flow, *, price_cache=None):
        super().__init__(level=MaterialLevel.INSET)
        self._state, self._resource_id = state, flow.resource_id
        self._price_cache = price_cache if price_cache is not None else {}
        self._stock_value = self._flow_value = self._rate_value = self._price_value = None
        self.setObjectName('resourceOverviewCard')
        self.setProperty('resourceId', flow.resource_id)
        self.setMinimumWidth(300)
        self.setFixedHeight(CARD_HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)
        header = QHBoxLayout()
        # 38 px uses the existing small-image atlas instead of decoding full source PNGs.
        header.addWidget(ResourceIconWidget(flow.resource_id, resource_icon_key(flow.resource_id), resource_accent_key(flow.resource_id), 38))
        name = research_products().get(flow.resource_id, {}).get('name', flow.resource_id.replace('_', ' '))
        title = ElidedResourceLabel(name.upper(), tooltip_text=name)
        title.setObjectName('resourceOverviewName')
        title.setStyleSheet('color: #eff8f4; font-size: 13px; font-weight: 900;')
        header.addWidget(title, 1)
        layout.addLayout(header)
        category = ElidedResourceLabel('RESEARCH · ' + research_category(flow.resource_id).upper())
        category.setObjectName('resourceResearchCategory')
        category.setStyleSheet('color: #ffd21f; font-size: 11px;')
        category.setFixedHeight(18)
        layout.addWidget(category)
        self.stock = QLabel()
        self.stock.setStyleSheet('color: #eff8f4; font-size: 12px; font-weight: 800;')
        layout.addWidget(self.stock)
        self.production = QLabel()
        self.production.setObjectName('resourcePlannedFlow')
        self.production.setWordWrap(True)
        self.production.setStyleSheet('color: #eff8f4; font-size: 11px;')
        self.production.setToolTip('Configured company-wide production plan in units/min. Assumes full power, inputs and storage. Freight is measured separately below.')
        layout.addWidget(self.production)
        self.freight = QLabel()
        self.freight.setObjectName('resourceMeasuredFreight')
        self.freight.setWordWrap(True)
        self.freight.setStyleSheet('color: #53c8e8; font-size: 11px;')
        self.freight.setToolTip('Actual completed deliveries over the last 60 simulation seconds. During startup, normalized over observed seconds. Loaded/in-transit goods are excluded. Event freight is not yet available.')
        layout.addWidget(self.freight)
        self.price = ElidedResourceLabel('')
        self.price.setStyleSheet('color: #ffd21f; font-size: 11px;')
        self.price.setFixedHeight(18)
        layout.addWidget(self.price)
        self.update_flow(flow)

    def update_flow(self, flow):
        from production_zero.core.market import market_price_for
        from production_zero.core.modifiers import market_sale_price
        stock = self._state.resources.get(self._resource_id)
        amount = stock.amount if stock else 0
        if amount != self._stock_value:
            self._stock_value = amount
            self.stock.setText(f'{amount:,.0f} STORED')
        if flow != self._flow_value:
            self._flow_value = flow
            self.production.setText(f'PLAN / min:  PROD +{flow.produced_per_minute:,.1f}\nUSE −{flow.consumed_per_minute:,.1f}  ·  NET {flow.net_per_minute:+,.1f}')
            self.setProperty('producedPerMinute', flow.produced_per_minute)
            self.setProperty('consumedPerMinute', flow.consumed_per_minute)
            self.setProperty('netPerMinute', flow.net_per_minute)
        rate = self._state.freight.delivery_statistics.resource_rate(self._resource_id)
        rate_value = rate.sell, rate.contract, rate.consortium, rate.event, rate.measuring
        if rate_value != self._rate_value:
            self._rate_value = rate_value
            warmup = ' · measuring' if rate.measuring else ''
            self.freight.setText(f'DELIVERED / min{warmup}\nMARKET {rate.sell:,.1f}  ·  CONTRACT {rate.contract:,.1f}\nCONSORTIUM {rate.consortium:,.1f}  ·  EVENT {rate.event:,.1f}')
            self.setProperty('deliveredPerMinute', rate.total)
        price_value = market_price_for(self._state.market, self._resource_id), market_sale_price(self._state, self._resource_id)
        if price_value != self._price_value:
            self._price_value = price_value
            cached = self._price_cache.get(self._resource_id)
            if cached is None or cached[0] != price_value:
                cached = (price_value, base_price_text(self._resource_id, self._state, compact=True),
                          price_tooltip(self._state, self._resource_id))
                self._price_cache[self._resource_id] = cached
            self.price.setText(cached[1])
            self.price.set_tooltip_text(cached[2])
            self.setToolTip('Research: ' + research_category(self._resource_id) + '\n' + cached[2])
            self.setProperty('baseSellPrice', price_value[0])


class ResourceOverviewGrid(QWidget):
    """Keep the full logical catalogue, materializing only viewport rows plus a buffer."""
    def __init__(self, state, definitions, resources, *, scroll_area=None):
        super().__init__()
        self._state, self._definitions, self._resources = state, definitions, resources
        self._all_stored = False
        self.search_text = self.category_id = ''
        self._items = {}
        self._flows = {}
        self._resource_ids = ()
        self._price_cache = {}
        self._categories = {rid: research_category(rid) for rid in resources}
        self._search_index = {rid: (r.name + ' ' + rid + ' ' + self._categories[rid]).casefold()
                              for rid, r in resources.items()}
        self._columns = 1
        self._scroll = scroll_area
        self._updating_items = False
        if scroll_area is not None:
            scroll_area.verticalScrollBar().valueChanged.connect(self._update_visible_items)
            scroll_area.viewport().installEventFilter(self)
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self._empty = QLabel('No resources match this view.\nChoose ALL STORED or adjust the filters.', self)
        self._empty.setWordWrap(True)
        self._empty.setStyleSheet('color: #bdc9c3; font-size: 13px; padding: 12px;')

    def _resource_flows(self):
        flows = calculate_resource_flows(self._state, self._definitions)
        rates = self._state.freight.delivery_statistics
        delivered_ids = {rid for entries in rates.resource_buckets.values() for rid in entries}
        ids = ({rid for rid, stock in self._state.resources.items() if stock.amount > 0} if self._all_stored
               else set(flows) | {rid for rid in delivered_ids if rates.resource_rate(rid).total > 0})
        return {rid: flows.get(rid, ResourceFlow(rid, 0, 0)) for rid in ids if rid in self._resources
                and (not self.search_text or self.search_text in self._search_index[rid])
                and (not self.category_id or self._categories[rid] == self.category_id)}

    def refresh(self):
        if not self.isVisible():
            return
        self._flows = self._resource_flows()
        self._resource_ids = tuple(sorted(self._flows, key=lambda r: self._resources[r].name))
        self._relayout_items()

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._relayout_items()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self._update_visible_items()

    def eventFilter(self, watched, event):
        if self._scroll is not None and watched is self._scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._relayout_items()
        return super().eventFilter(watched, event)

    def _relayout_items(self):
        width = self._scroll.viewport().width() if self._scroll is not None else self.width()
        self._columns = max(1, (width + CARD_GAP) // 328)
        rows = (len(self._resource_ids) + self._columns - 1) // self._columns
        height = rows * ROW_PITCH - CARD_GAP if rows else 80
        if height != self.minimumHeight():
            self.setMinimumHeight(height)
        self._empty.setVisible(not self._resource_ids)
        self._empty.setGeometry(0, 0, self.width(), 80)
        self._update_visible_items()

    def _update_visible_items(self, *args):
        if not self.isVisible() or self._updating_items:
            return
        self._updating_items = True
        try:
            width = self._scroll.viewport().width() if self._scroll is not None else self.width()
            top = self._scroll.verticalScrollBar().value() if self._scroll is not None else 0
            height = self._scroll.viewport().height() if self._scroll is not None else self.height()
            first = max(0, top // ROW_PITCH - 1) * self._columns
            last = ((top + height) // ROW_PITCH + 2) * self._columns
            wanted = self._resource_ids[first:last]
            for rid in tuple(self._items):
                if rid not in wanted:
                    hide_detach_delete(self._items.pop(rid))
            column_width = max(300, (width - (self._columns - 1) * CARD_GAP) // self._columns)
            for index, rid in enumerate(wanted, first):
                item = self._items.get(rid)
                if item is None:
                    item = ResourceOverviewCard(self._state, self._flows[rid], price_cache=self._price_cache)
                    item.setParent(self)
                    self._items[rid] = item
                else:
                    item.update_flow(self._flows[rid])
                rect = QRect((index % self._columns) * (column_width + CARD_GAP),
                             (index // self._columns) * ROW_PITCH, column_width, CARD_HEIGHT)
                if item.geometry() != rect:
                    item.setGeometry(rect)
                item.show()
        finally:
            self._updating_items = False
