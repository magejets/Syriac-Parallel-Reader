"""Fetch pinned inputs, preserving revisions and SHA256s. Network needed only here."""
import json, hashlib, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'sources'
DEST.mkdir(exist_ok=True)
lock_path = ROOT / 'sources.lock.json'
lock = json.loads(lock_path.read_text()) if lock_path.exists() else {'repositories': {}, 'files': {}}
repos = {'hebrew': ('openscriptures/morphhb', 'master'), 'syriac': ('ETCBC/syriac', 'v0.9'), 'lexicon': ('openscriptures/HebrewLexicon', 'master'), 'fonts': ('google/fonts', 'main')}
def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Hebrew-Syriac-reader-prototype'})
    return urllib.request.urlopen(req, timeout=90).read()
for key, (repo, ref) in repos.items():
    if key not in lock['repositories']:
        sha = json.loads(get(f'https://api.github.com/repos/{repo}/commits/{ref}'))['sha']
        lock['repositories'][key] = {'repo': repo, 'revision': sha}
    lock_path.write_text(json.dumps(lock, indent=2) + '\n')
def fetch(key, remote, local):
    r = lock['repositories'][key]
    url = f'https://raw.githubusercontent.com/{r["repo"]}/{r["revision"]}/{remote}'
    target = DEST / local
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(get(url))
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if local in lock['files'] and lock['files'][local]['sha256'] != digest:
        raise ValueError(f'Checksum mismatch: {local}')
    lock['files'][local] = {'url': url, 'sha256': digest}
    lock_path.write_text(json.dumps(lock, indent=2) + '\n')
fetch('hebrew', 'wlc/Gen.xml', 'Gen.xml')
fetch('hebrew', 'README.md', 'hebrew-README.md')
for name in ['otype','oslots','book','chapter','verse','g_cons_utf8','lex','gloss','sp','vs','vt','gn','nu','ps','st','trailer']:
    fetch('syriac', f'tf/0.9/{name}.tf', f'syriac/{name}.tf')
for name in ['LICENSE', 'README.md']:
    fetch('syriac', name, f'syriac-{name}')
for name in ['AugIndex.xml', 'LexicalIndex.xml', 'BrownDriverBriggs.xml', 'readme.md']:
    fetch('lexicon', name, name)
for family, filename in [('notosanssyriac', 'NotoSansSyriac[wght].ttf'), ('notoserifhebrew', 'NotoSerifHebrew[wdth,wght].ttf')]:
    fetch('fonts', f'ofl/{family}/{filename}', filename)
    fetch('fonts', f'ofl/{family}/OFL.txt', f'{family}-OFL.txt')
print(f'Fetched and verified {len(lock["files"])} pinned files.')
