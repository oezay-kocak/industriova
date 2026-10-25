"""Freeze approved audit references for regression independent of audit tools."""
from pathlib import Path
import csv,json
r=Path(__file__).resolve().parents[1]
m=json.loads((r/'artifacts/phase11d/models.json').read_text())
p={row['product_id']:float(row['recommended_N1_C2']) for row in csv.DictReader((r/'docs/industriova-03-phase11e-price-comparison.csv').open(encoding='utf-8-sig'))}
target=r/'tests/fixtures/economy-n1-c2.json';target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps({rid:dict(old=m['N0'][rid],new=m['N1'][rid],price=p[rid]) for rid in p},indent=2),encoding='utf-8')
print('353 approved regression fixtures')
