import json
from pathlib import Path
p = Path(r'd:\Users\DOMAIN\Desktop\ITI\rag_pipeline.ipynb')
nb = json.loads(p.read_text(encoding='utf-8'))
for i, cell in enumerate(nb.get('cells', [])[:50]):
    src = ''.join(cell.get('source', []))
    if src.strip():
        print(f'=== CELL {i} {cell.get("cell_type")} ===')
        print(src[:1500])
        print()
