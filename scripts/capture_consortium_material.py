"""Material/layout review fixtures; no real save changes."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import json
from pathlib import Path
from PySide6.QtCore import QTimer, QPoint
from PySide6.QtWidgets import QApplication,QTabWidget,QFrame,QScrollArea
from production_zero.tools.ui_contact_sheet import _load_qa_fonts,_save_contact_sheet
from production_zero.ui.main_window import MainWindow
from production_zero.ui.consortium_view import ConsortiumView
from production_zero.core.consortium import OPEN,ConsortiumMember
from capture_consortium_v1 import seed_products,start

OUT = Path(os.environ.get('PZ_CAPTURE_OUTPUT', 'artifacts/consortium_material'))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    app=QApplication.instance() or QApplication([])
    _load_qa_fonts()
    manifest=[]; geometry=[]
    for width,height in ((1366,768),(1600,980),(1920,1080)):
        w=MainWindow(development_mode=False)
        for timer in w.findChildren(QTimer): timer.stop()
        tabs=w.findChild(QTabWidget,'mainTabs')
        v=w.findChild(ConsortiumView)
        w.resize(width,height);w.show()
        captures=[]
        def settle():
            for _ in range(6): app.processEvents()
        def save(name):
            settle()
            assert (w.width(),w.height())==(width,height)
            path=f'{name}_{width}x{height}.png'
            pix=w.grab();assert pix.save(str(OUT/path))
            captures.append((name,pix));manifest.append(dict(state=name,resolution=[width,height],path=path))
        for title in ('Resources','Factory','Inventory'):
            tabs.setCurrentIndex(next(i for i in range(tabs.count()) if tabs.tabText(i)==title))
            save(title.lower()+'_reference')
        tabs.setCurrentWidget(v);seed_products(v)
        guild=v._service.create('Northstar Industries',OPEN,1);v.refresh()
        save('overview_sparse')
        v.member_tabs.setCurrentWidget(v.contracts_page)
        save('contracts_empty')
        v._draft_products['daily']=list(v._service.contract_candidates(guild.consortium_id,'daily')[:3])
        v._refresh_contracts(guild,'chairman');save('contracts_daily_selected')
        v._draft_products['weekly']=list(v._service.contract_candidates(guild.consortium_id,'weekly')[:4])
        v._refresh_contracts(guild,'chairman');save('contracts_both_selected')
        start(v,guild,'daily');start(v,guild,'weekly');v.refresh();save('contracts_active')
        v.contracts_page.verticalScrollBar().setValue(v.contracts_page.verticalScrollBar().maximum());save('contracts_active_bottom')
        v.member_tabs.setCurrentWidget(v.progression_page);save('progression_default')
        v.member_tabs.setCurrentWidget(v.members_page)
        for count in (1,2,10,25,50):
            guild.member_capacity=max(10,count)
            for i in range(1,count): guild.members[str(i)]=ConsortiumMember(str(i),f'Precision Industries {i:02}',i+2)
            v.refresh();settle();save(f'members_{count}')
            settings=next(x for x in v.members_page.findChildren(QFrame,'consortiumChairmanSettings') if x.isVisible())
            roster=next(x for x in v.members_page.findChildren(QScrollArea,'consortiumRosterScroll') if x.isVisible())
            geometry.append(dict(resolution=[width,height],members=count,settings_y=settings.mapTo(v.members_page,QPoint()).y(),settings_height=settings.height(),roster_height=roster.height(),page_scroll=v.members_page.verticalScrollBar().maximum(),roster_scroll=roster.verticalScrollBar().maximum()))
        roster.verticalScrollBar().setValue(roster.verticalScrollBar().maximum());save('members_50_last_row')
        guild.members={k:m for k,m in guild.members.items() if k==v._service.current_company_id or k in ('1','2','3')}
        v._service._award_consortium_xp(guild,35000);v.refresh()
        v.member_tabs.setCurrentWidget(v.overview_page);save('overview_populated')
        v.member_tabs.setCurrentWidget(v.progression_page);save('progression')
        _save_contact_sheet(captures,OUT/f'contact_{width}x{height}.png')
        w.close();w.deleteLater()
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (OUT/'geometry.json').write_text(json.dumps(geometry,indent=2),encoding='utf-8')
    print(f'{len(manifest)} captures')

if __name__=='__main__':main()
