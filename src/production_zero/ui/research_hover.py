"""Bounded research information, derived from the canonical domain assignments."""
from PySide6.QtCore import QObject, QEvent, QTimer, QPoint, Qt
from PySide6.QtWidgets import QLabel, QWidget, QGridLayout, QScrollArea, QHBoxLayout
from production_zero.ui.card_hover import CardHoverInfoPopup
from production_zero.core.research import research_catalog, research_domains, research_products, specialization_catalog
from production_zero.core.modifiers import modifier_bonus
from production_zero.ui.resource_icons import ResourceIconWidget


def hover_products(state,tree_id,slot_id=None):
    product=state.research.specializations.get(slot_id) if slot_id else None
    domain=tree_id.removeprefix('industry.')
    products=research_products()
    ids=[rid for rid,d in research_domains().items() if d==domain and (product is None or rid==product)]
    return sorted(((rid,products[rid]['name'],modifier_bonus(state.research,'value',rid)) for rid in ids),key=lambda p:p[1])


class ResearchHover(CardHoverInfoPopup):
    def __init__(self,parent):
        super().__init__(parent,object_name='researchHoverInfo',embedded=True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,False)
        self.dismiss=QTimer(self);self.dismiss.setSingleShot(True);self.dismiss.timeout.connect(self._dismiss_if_left)
        self.anchor=None

    def _dismiss_if_left(self):
        if not self.underMouse() and (self.anchor is None or not self.anchor.underMouse()):self.hide()

    def leaveEvent(self,event):self.dismiss.start(180);super().leaveEvent(event)
    def enterEvent(self,event):self.dismiss.stop();super().enterEvent(event)

    def display(self,anchor,state,tree_id,slot_id=None):
        self.anchor=anchor;self.dismiss.stop()
        tree=research_catalog()[0][tree_id];products=hover_products(state,tree_id,slot_id)
        description='Industry value research affects the following products and resources.'
        if slot_id:description='Product specialization adds an exact-product value bonus. Choose an eligible product after researching the attached Major.'
        self.set_details(tree.name + (' · Specialization' if slot_id else ''),None,[('Scope',description),('Products',str(len(products)))],(tree_id,slot_id))
        bounds=self.parentWidget().rect().adjusted(12,12,-12,-12)
        width=min(720,bounds.width());columns=max(1,min(3,width//225))
        scroll=QScrollArea();scroll.setObjectName('researchHoverProducts');scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        host=QWidget();grid=QGridLayout(host);grid.setContentsMargins(5,5,5,5);grid.setSpacing(8)
        for i,(rid,name,bonus) in enumerate(products):
            entry=QWidget();entry.setObjectName('researchHoverProductEntry')
            row=QHBoxLayout(entry);row.setContentsMargins(0,0,0,0);row.setSpacing(6)
            icon=ResourceIconWidget(rid,size=28);icon.setObjectName('researchHoverProductIcon')
            label=QLabel(f'{name}\nCurrent value bonus: +{bonus*100:g}%');label.setObjectName('researchHoverProduct');label.setProperty('resourceId',rid);label.setWordWrap(True);label.setMinimumWidth(0)
            row.addWidget(icon,0,Qt.AlignmentFlag.AlignVCenter);row.addWidget(label,1)
            grid.addWidget(entry,i//columns,i%columns)
        grid.setRowStretch((len(products)+columns-1)//columns,1);scroll.setWidget(host)
        scroll.setMinimumHeight(80);self._layout.addWidget(scroll,1)
        height=min(bounds.height(),max(240,165+min(10,(len(products)+columns-1)//columns)*48))
        self.resize(width,height)
        point=anchor.mapTo(self.parentWidget(),QPoint(anchor.width()+8,0))
        if point.x()+width>bounds.right():point.setX(anchor.mapTo(self.parentWidget(),QPoint()).x()-width-8)
        point.setX(max(bounds.left(),min(point.x(),bounds.right()-width)))
        point.setY(max(bounds.top(),min(point.y(),bounds.bottom()-height)))
        self.move(point);self.show();self.raise_()


class ResearchHoverBinding(QObject):
    def __init__(self,widget,state,tree_id,slot_id=None):
        super().__init__(widget);self.widget=widget;self.state=state;self.tree_id=tree_id;self.slot_id=slot_id
        widget.installEventFilter(self)

    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.Enter:
            window=obj.window()
            popup=getattr(window,'_research_hover_popup',None)
            if popup is None:popup=ResearchHover(window);window._research_hover_popup=popup
            popup.display(obj,self.state,self.tree_id,self.slot_id)
        elif event.type()==QEvent.Type.Leave:
            popup=getattr(obj.window(),'_research_hover_popup',None)
            if popup is not None:popup.dismiss.start(180)
        elif event.type()==QEvent.Type.ToolTip:return True
        elif event.type() in (QEvent.Type.Hide,QEvent.Type.MouseButtonPress):
            popup=getattr(obj.window(),'_research_hover_popup',None)
            if popup is not None:popup.hide()
        return False


def bind_research_hover(widget,state,tree_id,slot_id=None):
    if tree_id.startswith('industry.'):
        widget._research_hover_binding=ResearchHoverBinding(widget,state,tree_id,slot_id)
