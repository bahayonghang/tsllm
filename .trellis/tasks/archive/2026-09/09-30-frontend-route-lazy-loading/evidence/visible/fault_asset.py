"""Temporarily hold one isolated asset and restore the same bytes."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['hold', 'restore'])
parser.add_argument('module', choices=['RunDetailPage', 'SystemPage'])
args = parser.parse_args()
OUT = Path(__file__).resolve().parent
TASK = OUT.parents[1]
ASSETS = TASK / 'isolation' / 'B1-r1' / 'web' / 'dist' / 'assets'

def stamp(path):
    stat = path.stat()
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns}

receipt = OUT / f'fault-{args.module}-hold.json'
if args.action == 'hold':
    if receipt.exists():
        raise SystemExit('Existing fault attempt is immutable')
    matches = list(ASSETS.glob(args.module + '-*.js'))
    if len(matches) != 1:
        raise SystemExit(f'Expected one module, found {len(matches)}')
    asset = matches[0]
    held = asset.with_suffix(asset.suffix + '.route-lazy-held')
    if held.exists():
        raise SystemExit('Held asset already exists')
    before = stamp(asset)
    asset.rename(held)
    result = {'action': 'hold', 'asset': str(asset), 'held': str(held), 'before': before, 'held_stamp': stamp(held), 'original_absent': not asset.exists()}
else:
    original = json.loads(receipt.read_text(encoding='utf-8'))
    asset = Path(original['asset'])
    held = Path(original['held'])
    if asset.parent.resolve() != ASSETS.resolve() or held.parent.resolve() != ASSETS.resolve():
        raise SystemExit('Asset is outside isolated B1 directory')
    if asset.exists() or stamp(held) != original['before']:
        raise SystemExit('Asset state differs from immutable hold receipt')
    held.rename(asset)
    result = {'action': 'restore', 'asset': str(asset), 'before': original['before'], 'after': stamp(asset), 'held_absent': not held.exists()}
    assert result['before'] == result['after']
destination = OUT / f'fault-{args.module}-{args.action}.json'
with destination.open('x', encoding='utf-8', newline='\n') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
