"""Verify persisted outcomes of the documented native Windows sessions."""
import json,sqlite3
from pathlib import Path

out=Path('artifacts/industriova-ui-repair')
def saved(relative):
    path=(out/relative).resolve()
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        assert db.execute('pragma integrity_check').fetchone()[0]=='ok'
        return json.loads(db.execute("select state_json from saves where slot='company'").fetchone()[0])

source=saved('live/game.sqlite')
fresh=saved('exe-fresh/Production Zero/saves/company.sqlite')
final=saved('exe-carry/Production Zero/saves/company.sqlite')
carry=json.loads((out/'exe-carry-save.json').read_text())
truck='starter-truck-common-001'
assert fresh['cash']['amount']==130 and len(fresh['halls'])==2 and len(fresh['cards'])==8
assert set(source['cards'])<=set(final['cards']) and len(final['cards'])==10
assert final['cards'][truck]['mk_level']==2 and final['cards'][truck]['paused']
assert final['freight']['facilities']['garage-1']['slots'][0]['card_id']==truck
assert final['freight']['assignments'][truck]==source['freight']['assignments'][truck]
assert not final['freight']['outbound_shipments']
assert final['cash']['amount']==carry['cash']==875
assert final['tick']>carry['tick']>source['tick']
assert final['state_schema_version']==source['state_schema_version']==5
assert (out/'exe-relaunch-exit.txt').read_text(encoding='utf-8-sig').strip()=='0'
assert all((out/name).stat().st_size==0 for name in ('exe-fresh-stderr.txt','exe-carry-stderr.txt','exe-relaunch-stderr.txt'))
result={
    'method':'Native Windows SendInput via computer-use, followed by read-only SQLite assertions',
    'fresh_exe':{'regular_exit':0,'cash':130,'cards':8,'halls':2,'slot_installations':['Resources','Energy','Factory'],'later_locked_click_no_purchase':True},
    'continued_exe':{'regular_close':True,'supply_purchase':True,'busy_move_rejected':True,'paused_trip_finished':True,'native_freight_move':'garage-1 slot index 1 to 0','cash_at_close':carry['cash']},
    'relaunch_exe':{'regular_exit':0,'tick':final['tick'],'previous_tick':carry['tick'],'cards':10,'cash':875,'truck_mk':2,'truck_paused':True,'truck_slot_index':0,'route_preserved':True,'active_shipments':0,'no_cash_change_while_paused':True},
    'stderr_bytes':0,'sqlite_integrity':'ok','personal_saves_used':False,
    'manual_pending':['Production native OLE drag; automated gesture not reliable enough to establish cause or approve'],
    'human_gameplay_acceptance':False
}
(out/'exe-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
