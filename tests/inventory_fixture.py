"""Synthetic historical snapshot builders for saved-data/parser tests, never execution."""
from pathlib import Path
import runpy
BUNDLE = Path(__file__).resolve().parents[1] / 'recipes/system/inventory/overview'
COLLECTOR = runpy.run_path(str(BUNDLE / 'main.py'))

def historical_metadata():
    return {'id':'inventory-system', 'version':'0.2.0', 'access_mode':'read',
            'retention':{'contract':'inventory-observations','version':'0.1.0',
                         'description':'Historical synthetic inventory observations.',
                         'schema':'retention.schema.json'}}
