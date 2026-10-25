"""Apply exactly the approved stored N1 model, verifying the complete N0 source."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
model=json.loads((ROOT/'artifacts/phase11d/models.json').read_text())
path=ROOT/'src/production_zero/data/game_definitions.json'
data=json.loads(path.read_text(encoding='utf-8'));changed=[];seen=set()
for card in data['cards']:
    for option in card.get('production_options',[]):
        rid=option['output_resource'];seen.add(rid);old=model['N0'][rid];new=model['N1'][rid]
        assert option.get('input_resources',card.get('input_resources',{}))==old['inputs']
        assert option.get('output_amount',card['base_output_per_tick'])==old['output']
        if old['inputs']!=new['inputs'] or old['output']!=new['output']:
            option['input_resources']=new['inputs'];option['output_amount']=new['output'];changed.append(rid)
assert len(seen)==353 and len(changed)==178
path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(ROOT/'artifacts/phase11fg/recipe-changes.json').write_text(json.dumps(changed,indent=2),encoding='utf-8')
print('Exact N1 recipes applied:',len(changed))
