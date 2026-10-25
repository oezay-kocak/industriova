"""In-memory final Consortium UX fixtures and exact-size visual evidence."""
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
import json
from pathlib import Path
from PySide6.QtCore import QTimer, QPoint
from PySide6.QtWidgets import QApplication, QTabWidget, QScrollArea
from production_zero.tools.ui_contact_sheet import _load_qa_fonts, _save_contact_sheet
from production_zero.ui.main_window import MainWindow
from production_zero.ui.consortium_view import ConsortiumView, ConfirmConsortiumDialog
from production_zero.ui.event_feed import EventFeedWidget, EventFeedController
from production_zero.core.consortium import OPEN, ConsortiumMember, MEMBER, BOARD_MEMBER
from production_zero.core.company_xp import record_accepted_production_xp, CONTINUITY_DAILY_CAP, CONTINUITY_XP_PER_MINUTE
from capture_consortium_v1 import seed_products, start

OUT = Path('artifacts/consortium_final_ux')

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    _load_qa_fonts()
    manifest = []
    for size in ((1366,768), (1600,980), (1920,1080)):
        w = MainWindow(development_mode=False)
        for timer in w.findChildren(QTimer): timer.stop()
        v = w.findChild(ConsortiumView)
        w.findChild(QTabWidget, 'mainTabs').setCurrentWidget(v)
        w.resize(*size); w.show()
        seed_products(v)
        guild = v._service.create('Northstar Industries', OPEN, 1)
        owner = v._service.current_company_id
        v.refresh()
        captures = []
        def save(name):
            for _ in range(6): app.processEvents()
            assert (w.width(), w.height()) == size
            path = f'{name}_{size[0]}x{size[1]}.png'
            pix = w.grab(); assert pix.save(str(OUT/path))
            captures.append((name, pix))
            manifest.append(dict(state=name, resolution=list(size), path=path))
        save('overview_one')
        v.member_tabs.setCurrentWidget(v.contracts_page)
        save('contracts_empty')
        for kind in ('daily', 'weekly'):
            v._draft_products[kind] = list(v._service.contract_candidates(guild.consortium_id, kind)[:3 if kind=='daily' else 4])
        v._refresh_contracts(guild, 'chairman')
        save('contracts_selected')
        start(v, guild, 'daily'); v.refresh()
        save('contracts_daily_active')
        start(v, guild, 'weekly'); v.refresh()
        save('contracts_both_active')
        for kind, contract in guild.contracts.items():
            rid, required = next(iter(contract.requirements.items()))
            v._state.ensure_resource(rid).amount = required
            v._service.contribute(guild.consortium_id, owner, kind, rid, required // 2)
        v.refresh(); save('contracts_progress')
        v.contracts_page.verticalScrollBar().setValue(v.contracts_page.verticalScrollBar().maximum())
        save('contracts_progress_scrolled')
        v.member_tabs.setCurrentWidget(v.progression_page); save('progression_default')
        v.member_tabs.setCurrentWidget(v.members_page); save('members_one_owner')
        for count in (10,25,50):
            guild.member_capacity = count
            for i in range(1,count):
                guild.members[f'fixture-{i}'] = ConsortiumMember(f'fixture-{i}', f'Precision Industries {i:02}', 8+i, BOARD_MEMBER if i==1 else MEMBER, 1500+i, i*125)
            v.refresh(); save(f'members_{count}')
        row = v._member_rows['fixture-1']
        menu = v._member_menu(guild, 'chairman', guild.members['fixture-1'], row.mapToGlobal(QPoint(220,20)))
        for _ in range(3): app.processEvents()
        # Native Qt popup is captured separately because window.grab excludes it.
        menu.grab().save(str(OUT/f'member_context_menu_{size[0]}x{size[1]}.png'))
        manifest.append(dict(state='member_context_menu', resolution=list(size), path=f'member_context_menu_{size[0]}x{size[1]}.png'))
        save('members_context_anchor'); menu.close()
        roster = v.members_page.findChild(QScrollArea,'consortiumRosterScroll')
        roster.verticalScrollBar().setValue(roster.verticalScrollBar().maximum())
        v.members_page.verticalScrollBar().setValue(v.members_page.verticalScrollBar().maximum())
        save('members_50_bottom_actions')
        v._confirm_disband(guild); save('disband_confirmation')
        next(d for d in w.centralWidget().findChildren(ConfirmConsortiumDialog) if d.isVisible()).reject()
        v._state.consortium.current_company_id = 'fixture-2'; v.refresh()
        save('members_normal_member')
        v._confirm_leave(guild); save('leave_confirmation')
        next(d for d in w.centralWidget().findChildren(ConfirmConsortiumDialog) if d.isVisible()).reject()
        v._state.consortium.current_company_id = owner
        guild.members = {key: value for key, value in guild.members.items() if key == owner or key in {f'fixture-{i}' for i in range(1, 10)}}
        v._service._award_consortium_xp(guild,35000); v.refresh()
        v.member_tabs.setCurrentWidget(v.overview_page); save('overview_populated')
        v.member_tabs.setCurrentWidget(v.progression_page); save('progression_progressed')
        feed = w.findChild(EventFeedWidget)
        feed._history.clear()
        feed._clear_ticker_tape()
        v._state.communications.pending_activity.clear()
        controller = EventFeedController(v._state, feed, definitions=v._definitions)
        # Unknown fixture output bypasses first-product/efficiency awards; tests
        # separately exercise real production and preserve its meaningful events.
        record_accepted_production_xp(v._state, {'qa_unknown':1}, 1, v._definitions)
        controller.observe(); feed.flush_pending(); save('daily_activity_before')
        record_accepted_production_xp(v._state, {'qa_unknown':1}, CONTINUITY_DAILY_CAP/CONTINUITY_XP_PER_MINUTE*60, v._definitions)
        controller.observe(); feed.flush_pending()
        for _ in range(350): feed._advance_ticker()
        save('daily_activity_complete')
        feed._show_history()
        for _ in range(4): app.processEvents()
        history_path = f'daily_activity_history_popup_{size[0]}x{size[1]}.png'
        feed._history_panel.grab().save(str(OUT/history_path))
        manifest.append(dict(state='daily_activity_history_popup', resolution=list(size), path=history_path))
        save('daily_activity_history')
        _save_contact_sheet(captures, OUT/f'contact_{size[0]}x{size[1]}.png')
        w.close(); w.deleteLater()
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'{len(manifest)} captures')

if __name__ == '__main__': main()
