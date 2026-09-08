"""Read native EasyEDA history and preserve live sources before board repair."""
import base64
import collections
import gzip
import json
from pathlib import Path
import sqlite3
import subprocess
import urllib.request
import urllib.error

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.cache' / 'pcb-repair-20260908'
DOCS = ['484a25750631f0fe', '86c9249a00f4733c', 'cff2555ab025a4cb', '4b6aafcf375345b9']

def api(code):
    body = json.dumps({'code': code}).encode()
    req = urllib.request.Request('http://127.0.0.1:49620/execute', body, {'Content-Type': 'application/json'})
    try:
        result = json.load(urllib.request.urlopen(req, timeout=45))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(exc.read().decode('utf-8', errors='replace')) from exc
    if not result.get('success'):
        raise RuntimeError(result)
    return result.get('result')

def records(source):
    doc = client = ''
    for line in source.splitlines():
        if '||' not in line:
            continue
        meta, data = line.split('||', 1)
        meta = json.loads(meta)
        data = data.removesuffix('|')
        data = json.loads(data) if data else None
        if meta['type'] == 'DOCHEAD':
            doc, client = data['uuid'], data.get('client', '')
        yield doc, client, meta, data

def resolve(sources):
    result = {}
    for source in sources:
        for doc, client, meta, data in records(source):
            if meta['type'] in ('DOCHEAD', 'EDIT_HEAD'):
                continue
            key = (doc, meta['type'], meta.get('id', meta['type']))
            old = result.get(key)
            ticket = meta.get('ticket', 0)
            if old is None or ticket > old[0] or (ticket == old[0] and client < old[1]):
                result[key] = (ticket, client, meta, data)
    return {k: v for k, v in result.items() if v[3] not in (None, '')}

def git_state(ref):
    db = sqlite3.connect(':memory:')
    db.deserialize(subprocess.check_output(['git', 'show', ref + ':board/Ichiping uno q.eprj2'], cwd=ROOT))
    db.row_factory = sqlite3.Row
    branch = db.execute('select uuid,history_uuid from branches where delete_status=0 order by id desc limit 1').fetchone()
    rows = {r['uuid']: r for r in db.execute('select * from project_history_' + branch['uuid'].replace('-', '_'))}
    chain, uid = [], branch['history_uuid']
    while uid in rows:
        row = rows[uid]
        chain.append(row)
        uid = row['parent']
    sources = []
    for row in reversed(chain):
        for i in range(row['num'] + 1):
            uid = row['uuid'] + ('-' + str(i) if i else '')
            data = db.execute('select dataStr from history_data where uuid=?', (uid,)).fetchone()
            if data:
                raw = AESGCM(bytes.fromhex(row['key'])).decrypt(bytes.fromhex(row['uuid']), base64.b64decode(data[0]), None)
                sources.append(gzip.decompress(raw).decode())
    return resolve(sources)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    live = []
    for doc in DOCS:
        api('await eda.dmt_EditorControl.openDocument(' + json.dumps(doc) + '); return await eda.dmt_SelectControl.getCurrentDocumentInfo();')
        source = api('return await eda.sys_FileManager.getDocumentSource();')
        if not source:
            raise RuntimeError('Empty source ' + doc)
        path = OUT / (doc + '-before.txt')
        if not path.exists():
            path.write_text(source, encoding='utf-8')
        live.append(source)
    state = resolve(live)
    for ref in ['origin/main', 'stash@{0}']:
        other = git_state(ref)
        counts = collections.Counter()
        for key in state.keys() | other.keys():
            if key[0] not in DOCS:
                continue
            a, b = state.get(key), other.get(key)
            if (a[3] if a else None) != (b[3] if b else None):
                counts[(key[0], key[1])] += 1
        print(ref, dict(counts))
    print('Backups:', OUT)

def restore_local():
    base, local, remote = (git_state(ref) for ref in ['stash@{0}^1', 'stash@{0}', 'origin/main'])
    for doc in DOCS[:2]:
        backup = OUT / (doc + '-before.txt')
        if not backup.exists():
            raise RuntimeError('Run audit first')
        api('return await eda.dmt_EditorControl.openDocument(' + json.dumps(doc) + ');')
        source = api('return await eda.sys_FileManager.getDocumentSource();')
        live = resolve([source])
        changes = {}
        for key in base.keys() | local.keys() | remote.keys():
            if key[0] != doc:
                continue
            a, b, r = base.get(key), local.get(key), remote.get(key)
            data = lambda v: v[3] if v else None
            if data(a) != data(b) or data(r) != data(b):
                if key[1] in ('ACTIVE_LAYER', 'META_MODIFY', 'META'):
                    continue
                if key[1] == 'META':
                    value = dict(live[key][3])
                    value['title'] = b[3]['title']
                else:
                    value = data(b)
                changes[key] = value
        ticket = max(v[0] for v in live.values()) + 1
        result = []
        applied = set()
        for d, client, meta, value in records(source):
            key = (d, meta['type'], meta.get('id', meta['type']))
            if key in changes:
                value = changes[key]
                meta['ticket'] = ticket
                ticket += 1
                applied.add(key)
                if value is None:
                    continue
            result.append(json.dumps(meta) + '||' + json.dumps(value, ensure_ascii=False) + '|')
        for key in changes.keys() - applied:
            if changes[key] is not None:
                result.append(json.dumps({'type':key[1], 'id':key[2], 'ticket':ticket}) + '||' + json.dumps(changes[key]) + '|')
                ticket += 1
        target = '\n'.join(result)
        (OUT / (doc + '-local-restored.txt')).write_text(target, encoding='utf-8')
        ok = api('return await eda.sys_FileManager.setDocumentSource(' + json.dumps(target) + ');')
        if not ok:
            raise RuntimeError('Source rejected ' + doc)
        verify = resolve([api('return await eda.sys_FileManager.getDocumentSource();')])
        failures = [key for key, value in changes.items() if key[1] != 'META' and (verify[key][3] if key in verify else None) != value]
        print(doc, 'restored records', len(changes), 'verification differences', len(failures))
        if failures:
            print(failures[:10])
            raise RuntimeError('Readback mismatch')

if __name__ == '__main__':
    import sys
    restore_local() if '--restore-local' in sys.argv else main()
