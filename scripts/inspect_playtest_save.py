"""Read-only integrity and progress probe for the packaged native smoke test."""
from contextlib import closing
import json
from math import isfinite
from pathlib import Path
import sqlite3
import sys

path = Path(sys.argv[1]).resolve()
with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
    integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    payload = json.loads(db.execute("SELECT state_json FROM saves WHERE slot='company'").fetchone()[0])
result = dict(integrity=integrity, tick=payload['tick'], cash=payload['cash']['amount'],
              schema=payload['state_schema_version'], cards=len(payload['cards']),
              resources_nonnegative=all(isfinite(stock['amount']) and stock['amount'] >= 0 for stock in payload['resources'].values()),
              unopened_packs=len(payload['packs']['unopened']))
assert integrity == 'ok' and result['schema'] == 5 and result['resources_nonnegative'] and result['unopened_packs'] == 0
print(json.dumps(result))
