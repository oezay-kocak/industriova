"""Keep the informational JSON catalog consistent with the sole C2 resolver."""
from pathlib import Path
import csv,json,math
from production_zero.core.market import BASE_MARKET_PRICES
root=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((root/'docs/industriova-03-phase11e-price-comparison.csv').open(encoding='utf-8-sig')))
assert len(rows)==len(BASE_MARKET_PRICES)==353
for row in rows:
    assert math.isclose(BASE_MARKET_PRICES[row['product_id']],float(row['recommended_N1_C2']),rel_tol=1e-12,abs_tol=1e-12),row['product_id']
path=root/'src/production_zero/data/resource_definitions.json';data=json.loads(path.read_text(encoding='utf-8'))
for item in data['resources']:item['base_market_price']=BASE_MARKET_PRICES[item['id']]
path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print('353 C2 prices match the approved CSV; informational catalog synchronized.')
