"""Generate original PWA icons and content-addressed offline inventory."""
import hashlib, json, struct, zlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
def png(size):
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            a, b = x / size, y / size
            ink = (33,63,72)
            # Open book mark, kept within the maskable icon safe zone.
            if .24 < a < .47 and .29 < b < .7 or .53 < a < .76 and .29 < b < .7:
                ink = (251,250,246)
            if .32 < a < .41 and any(lo < b < lo+.018 for lo in [.4,.48,.56]) or .59 < a < .68 and any(lo < b < lo+.018 for lo in [.4,.48,.56]):
                ink = (174,137,87)
            row.extend(ink)
        rows.append(row)
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
icons = PUBLIC / 'icons'
icons.mkdir(exist_ok=True)
for size in [192,512]:
    (icons / f'icon-{size}.png').write_bytes(png(size))
(PUBLIC / '.nojekyll').touch()
assets = sorted(p for p in PUBLIC.rglob('*') if p.is_file() and p.name not in ['release.js','sw.js','.nojekyll'])
digest = hashlib.sha256()
digest.update((PUBLIC / 'sw.js').read_bytes())
for p in assets:
    digest.update(p.relative_to(PUBLIC).as_posix().encode())
    digest.update(p.read_bytes())
release = digest.hexdigest()[:16]
def offline_asset(path):
    relative = path.relative_to(PUBLIC).as_posix()
    return not (relative.startswith('data/lexicon/') or relative == 'data/occurrences.json')
offline_assets = [p for p in assets if offline_asset(p)]
paths = ['./'+p.relative_to(PUBLIC).as_posix() for p in offline_assets]
(PUBLIC / 'release.js').write_text(f'self.RELEASE = {json.dumps(release)};\nself.PRECACHE = {json.dumps(paths)};\n')
print(f'Release {release}: {len(offline_assets)} offline assets, {sum(p.stat().st_size for p in offline_assets)/1024**2:.1f} MiB; dictionaries/concordances online only')
