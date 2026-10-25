"""Read the complete approved reference corpus and inventory every CSV row."""
from pathlib import Path
import csv, hashlib, json
root=Path(__file__).resolve().parents[1]
names=['complete-recipe-economy-audit.md','phase11b-capacity-audit.md','phase11c-economy-model-analysis.md','phase11d-recipe-normalization-analysis.md','phase11d-recipe-normalization-comparison.csv','phase11d-chain-balance-comparison.csv','phase11e-final-economy-calibration.md','phase11e-price-comparison.csv','phase11e-economy-comparison.csv']
result=[]
for suffix in names:
    path=root/'docs'/('industriova-03-'+suffix)
    content=path.read_text(encoding='utf-8-sig')
    row=dict(path=str(path.relative_to(root)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),characters=len(content))
    if suffix.endswith('.csv'):
        rows=list(csv.DictReader(content.splitlines()));row.update(rows=len(rows),columns=list(rows[0]))
        assert rows and all(None not in r for r in rows)
    else:
        row['headings']=[line for line in content.splitlines() if line.startswith('#')]
    result.append(row)
(root/'artifacts/phase11fg/reference-corpus.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
