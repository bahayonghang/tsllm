"""Record the permitted repository and protected evidence baseline."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
TASK = Path(__file__).resolve().parents[1]
OUT = TASK / 'evidence' / 'scope'
OUT.mkdir(parents=True, exist_ok=True)

def command(*args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True, encoding='utf-8', check=True)
    return result.stdout

def record(path):
    stat = path.stat()
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}

def tree(path):
    return {p.relative_to(ROOT).as_posix(): record(p) for p in sorted(path.rglob('*')) if p.is_file()} if path.exists() else {}

tracked = command('git', 'ls-files', '-z').split('\0')
private = ('data/', 'ref/', 'runs/', 'cache/')
assert not any(p.startswith(private) for p in tracked)
status = command('git', 'status', '--porcelain=v1', '-uall')
diff = command('git', 'diff', 'e9ce26a7bd1a4ed67cd30d257354e7345c44dec1', '--', 'web')
assert diff == ''
snapshot = {
    'head': command('git', 'rev-parse', 'HEAD').strip(),
    'branch': command('git', 'branch', '--show-current').strip(),
    'initial_branch': 'codex/frontend-load-assessment',
    'tracked': {p: record(ROOT / p) for p in tracked if p and (ROOT / p).is_file()},
    'old_assessment': tree(ROOT / '.trellis/tasks/09-30-frontend-load-assessment'),
    'old_dist': tree(ROOT / 'web/dist'),
    'launch': record(ROOT / '.claude/launch.json') if (ROOT / '.claude/launch.json').exists() else None,
    'protected_roots_existence_only': {p: (ROOT / p).exists() for p in ['data', 'ref', 'runs', 'cache', 'cache/datasets/ETTh1.acc-backup']},
    'staged': command('git', 'diff', '--cached', '--name-only'),
    'product_diff': diff,
}
for name, content in [('preflight.json', json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n'), ('git-status-before.txt', status), ('product-baseline.diff', diff)]:
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(content)
print(json.dumps({'tracked': len(snapshot['tracked']), 'old_assessment': len(snapshot['old_assessment']), 'old_dist': len(snapshot['old_dist']), 'head': snapshot['head'], 'branch': snapshot['branch']}))
