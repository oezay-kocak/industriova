import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QFrame,QScrollArea
from production_zero.core.consortium import ConsortiumMember
from production_zero.ui.contract_product import ContractProductButton
from production_zero.ui.consortium_materials import ConsortiumWorkspaceFrame
from test_consortium_final_ux import scene,settle

SIZES=[(1366,768),(1600,980),(1920,1080)]

@pytest.mark.parametrize('size',SIZES)
def test_members_fixed_bottom_and_roster_scroll_all_capacities(scene,size):
    app,window,view,guild=scene
    window.resize(*size);view.member_tabs.setCurrentWidget(view.members_page)
    positions=[]
    for count in (1,2,10,25,50):
        guild.member_capacity=max(10,count)
        for i in range(1,count):guild.members[str(i)]=ConsortiumMember(str(i),f'Company {i:02}',i+1)
        view.refresh();settle(app)
        footer=view.members_layout.itemAt(2).widget()
        housing=view.members_layout.itemAt(1).widget()
        roster=housing.findChild(QScrollArea,'consortiumRosterScroll')
        positions.append((footer.geometry().y(),footer.height(),housing.height()))
        assert view.members_page.verticalScrollBar().maximum()==0
        assert view.members_page.horizontalScrollBar().maximum()==0
        assert footer.geometry().bottom()==view.members_page.widget().height()-15
        assert footer.height()==148
        assert len(view._member_rows)==count
        assert min(row.y() for row in view._member_rows.values())==0
        assert (roster.verticalScrollBar().maximum()>0)==(count*49-1>roster.viewport().height())
        roster.verticalScrollBar().setValue(roster.verticalScrollBar().maximum());settle(app)
        last=max(view._member_rows.values(),key=lambda row:row.y())
        assert roster.viewport().rect().contains(last.mapTo(roster.viewport(),last.rect().center()))
        assert (window.width(),window.height())==size
    assert len(set(positions))==1

@pytest.mark.parametrize('size',SIZES)
def test_overview_full_height_and_shared_silver_concrete_corners(scene,size):
    app,window,view,guild=scene
    window.resize(*size);settle(app)
    view.member_tabs.setCurrentWidget(view.overview_page);settle(app)
    host=view.overview_page.widget()
    panels=[view.overview_layout.itemAt(0).layout().itemAt(i).widget() for i in range(2)]
    assert panels[0].geometry().top()==panels[1].geometry().top()
    assert panels[0].geometry().bottom()==panels[1].geometry().bottom()==host.height()-15
    assert all(m.height()<110 for m in panels[0].findChildren(QFrame,'consortiumStatModule'))
    for page in (view.overview_page,view.contracts_page,view.members_page,view.progression_page):
        view.member_tabs.setCurrentWidget(page);settle(app)
        frame=page.widget()
        assert isinstance(frame,ConsortiumWorkspaceFrame)
        assert not page.viewport().autoFillBackground() and not frame.autoFillBackground()
        screenshot=window.grab().toImage()
        # Sample the composited parent showing through the rounded top corner.
        corner=frame.mapTo(window,QPoint(0,0))
        rgb=screenshot.pixelColor(corner)
        assert min(rgb.red(),rgb.green(),rgb.blue())>140
        rim=[]
        for x in (3,frame.width()-4):
            color=screenshot.pixelColor(frame.mapTo(window,QPoint(x,40)))
            rim.append((color.red()+color.green()+color.blue())/3)
        assert min(rim)>145 and abs(rim[0]-rim[1])<65
        assert (window.width(),window.height())==size

@pytest.mark.parametrize('size',SIZES)
def test_contracts_fill_workspace_without_changing_product_geometry(scene,size):
    app,window,view,guild=scene
    window.resize(*size);view.member_tabs.setCurrentWidget(view.contracts_page)
    for kind in ('daily','weekly'):
        view._draft_products[kind]=list(view._service.contract_candidates(guild.consortium_id,kind)[:3 if kind=='daily' else 4])
    view._refresh_contracts(guild,'chairman');settle(app)
    first,last=[view.contracts_layout.itemAt(i).widget() for i in range(2)]
    assert first.geometry().bottom()<last.geometry().top()
    assert last.geometry().bottom()==view.contracts_page.widget().height()-15
    assert abs(first.height()-last.height())<=1
    assert all(m.height()==78 for section in (first,last) for m in section.findChildren(ContractProductButton))
    assert view.contracts_page.horizontalScrollBar().maximum()==0
    if size[1]>=980:assert view.contracts_page.verticalScrollBar().maximum()==0


@pytest.mark.parametrize('size', SIZES)
def test_contrast_materials_buttons_and_nested_corners(scene, size):
    from PySide6.QtWidgets import QLabel
    from PySide6.QtGui import QPalette
    from production_zero.ui.pz_controls import RaisedPZButton
    from production_zero.ui.theme import Theme
    app, window, view, guild = scene
    window.resize(*size)
    for page in (view.overview_page, view.contracts_page, view.members_page, view.progression_page):
        view.member_tabs.setCurrentWidget(page); settle(app)
        # All four sides of every visible silver chassis remain light silver.
        for frame in page.findChildren(ConsortiumWorkspaceFrame):
            if not frame.isVisible(): continue
            pix = frame.grab().toImage()
            points = ((3, frame.height()//2), (frame.width()-4, frame.height()//2),
                      (frame.width()//2, 3), (frame.width()//2, frame.height()-4))
            values = [sum(pix.pixelColor(x,y).getRgb()[:3])/3 for x,y in points]
            assert min(values)>185 and max(values)-min(values)<30
            assert not frame.autoFillBackground()
        for module in page.findChildren(QFrame, 'consortiumStatModule'):
            pix = module.grab().toImage()
            assert min(pix.pixelColor(module.width()-15, module.height()//2).getRgb()[:3])>180
            for label in module.findChildren(QLabel):
                assert max(label.palette().color(QPalette.ColorRole.WindowText).getRgb()[:3])<100
        for name in ('consortiumProductSelection','consortiumChairmanSettings'):
            for housing in page.findChildren(QFrame, name):
                for label in housing.findChildren(QLabel):
                    if label.parentWidget() is housing:
                        assert max(label.palette().color(QPalette.ColorRole.WindowText).getRgb()[:3])<100
        if page is view.contracts_page:
            for section in page.findChildren(QFrame, 'consortiumContractSection'):
                assert isinstance(section, ConsortiumWorkspaceFrame)
                # The rounded section corner exposes its graphite parent, not an opaque backing.
                image = window.grab().toImage()
                corner = image.pixelColor(section.mapTo(window, QPoint(0,0)))
                adjacent = image.pixelColor(section.mapTo(window, QPoint(-1,0)))
                assert max(abs(a-b) for a,b in zip(corner.getRgb()[:3],adjacent.getRgb()[:3]))<8
        if page is view.members_page:
            buttons={b.text(): b for b in page.findChildren(RaisedPZButton) if b.isVisible()}
            assert buttons['SAVE SETTINGS'].variant == buttons['INVITE PLAYER'].variant == 'primary'
            assert buttons['DISBAND CONSORTIUM'].variant == 'destructive'
            assert buttons['INVITE PLAYER'].height()<=36
    assert (window.width(),window.height())==size
