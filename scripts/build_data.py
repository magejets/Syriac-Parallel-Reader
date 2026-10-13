"""Dependency-free OSIS + Text-Fabric subset exporter. No runtime backend."""
import json, re, hashlib, shutil
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / 'sources', ROOT / 'public/data'
NS = {'o': 'http://www.bibletechnologies.net/2003/OSIS/namespace', 'l': 'http://openscriptures.github.com/morphhb/namespace'}
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
def tf(name, edges=False):
    """Read explicit/range/implicit node numbers; retain significant whitespace."""
    lines = (SRC / 'syriac' / f'{name}.tf').read_text().splitlines()
    start = lines.index('') + 1
    result, previous = {}, 0
    for line in lines[start:]:
        fields = line.split('\t')
        if len(fields) == 1:
            nodes, value = [previous + 1], fields[0]
        else:
            spec, value = fields
            nodes = expand(spec)
        for node in nodes:
            result[node] = expand(value) if edges else value
        previous = nodes[-1]
    return result
def expand(spec):
    result = []
    for segment in spec.split(','):
        if '-' in segment:
            a, b = map(int, segment.split('-'))
            result.extend(range(a, b + 1))
        elif segment:
            result.append(int(segment))
    return result
def text(element):
    return ''.join(element.itertext()).strip() if element is not None else ''
def main():
    lock = json.loads((ROOT / 'sources.lock.json').read_text())
    for name, item in lock['files'].items():
        assert hashlib.sha256((SRC / name).read_bytes()).hexdigest() == item['sha256'], name
    lex_entries = {e.get('id'): e for e in ET.parse(SRC / 'LexicalIndex.xml').findall('.//l:entry', NS)}
    aug = {w.get('aug'): text(w) for w in ET.parse(SRC / 'AugIndex.xml').findall('l:w', NS)}
    bdb = {e.get('id'): e for e in ET.parse(SRC / 'BrownDriverBriggs.xml').findall('.//l:entry', NS)}
    lexicon, occurrences, roots, bdb_shards = {}, defaultdict(list), defaultdict(list), defaultdict(dict)
    def root_for(entry, seen=None):
        seen = set() if seen is None else seen
        if entry is None or entry.get('id') in seen:
            return None
        seen.add(entry.get('id'))
        etym = entry.find('l:etym', NS)
        if etym is None:
            return None
        if etym.get('root'):
            return {'text': etym.get('root'), 'id': entry.get('id')}
        if etym.get('type') == 'sub':
            return root_for(lex_entries.get(text(etym)), seen)
        return None
    def hebrew_lemma(raw):
        key = re.sub(r'\s+', '', raw)
        lid = f'he:{key}'
        if lid in lexicon:
            return lid
        entry = lex_entries.get(aug.get(key))
        word = entry.find('l:w', NS) if entry is not None else None
        xref = entry.find('l:xref', NS) if entry is not None else None
        bid = xref.get('bdb') if xref is not None else None
        root = root_for(entry)
        lexicon[lid] = {'headword': text(word) or raw, 'gloss': text(entry.find('l:def', NS)) if entry is not None else 'No bundled lexical entry', 'transliteration': word.get('xlit', '') if word is not None else '', 'root': root['text'] if root else None, 'rootId': root['id'] if root else None, 'bdb': bid, 'source': 'Open Scriptures Hebrew Lexicon', 'license': 'CC BY 4.0'}
        if bid and bid in bdb:
            # Plain text: never ship/execute arbitrary source XML or HTML.
            e = bdb[bid]
            def content_text(element):
                result = element.text or ''
                for child in element:
                    if child.tag.split('}')[-1] not in ['status','page']:
                        result += content_text(child)
                    result += child.tail or ''
                return result
            body = ' '.join(content_text(e).split())
            bdb_shards[bid[0]][bid] = {'id': bid, 'body': body, 'status': text(e.find('l:status', NS)), 'source': 'Open Scriptures abridged BDB transcription', 'license': 'CC BY 4.0; underlying 1906 text public domain'}
        return lid
    hebrew = {}
    for verse in ET.parse(SRC / 'Gen.xml').findall('.//o:verse', NS):
        ref = verse.get('osisID')
        words = []
        for child in verse:
            kind = child.tag.split('}')[-1]
            if kind == 'w':
                surface = text(child).replace('/', '')
                lemmas = [hebrew_lemma(s) for s in child.get('lemma', '').split('/') if s]
                words.append({'id': child.get('id'), 'text': surface, 'after': ' ', 'lemmas': lemmas, 'morphology': child.get('morph', ''), 'variant': child.get('type', '')})
            elif kind == 'seg' and words:
                preceding = '' if words[-1]['after'] == ' ' else words[-1]['after']
                words[-1]['after'] = preceding + text(child) + (' ' if child.get('type') != 'x-maqqef' else '')
            elif kind == 'note' and child.get('type') == 'variant' and words:
                words[-1]['qere'] = ' '.join(text(w).replace('/', '') for w in child.findall('.//o:w', NS))
        hebrew[ref] = words
    f = {n: tf(n) for n in ['otype','book','chapter','verse','g_cons_utf8','lex','gloss','sp','vs','vt','gn','nu','ps','st','trailer']}
    slots = tf('oslots', True)
    booknode = next(n for n, v in f['book'].items() if v == 'Genesis')
    bookslots = set(slots[booknode])
    chapter_for = {}
    for node, c in f['chapter'].items():
        if slots[node][0] in bookslots:
            for s in slots[node]:
                chapter_for[s] = int(c)
    syriac = {}
    for node, v in f['verse'].items():
        if slots[node][0] not in bookslots:
            continue
        ref = f'Gen.{chapter_for[slots[node][0]]}.{v}'
        assert ref not in syriac, ref
        groups, group = [], None
        for s in slots[node]:
            lid = 'syr:' + f['lex'].get(s, '')
            lexicon.setdefault(lid, {'headword': f['lex'].get(s, ''), 'gloss': f['gloss'].get(s, ''), 'root': None, 'source': 'ETCBC/CACCHT Syriac Corpus 0.9', 'license': 'See Syriac data notice; noncommercial deployment only'})
            part = {'text': f['g_cons_utf8'].get(s, ''), 'lemma': lid, 'morphology': {k: f[k][s] for k in ['sp','vs','vt','gn','nu','ps','st'] if f[k].get(s)}}
            if group is None:
                group = {'id': f's{s}', 'text': '', 'after': '', 'lemmas': [], 'parts': []}
                groups.append(group)
            group['text'] += part['text']
            group['lemmas'].append(lid)
            group['parts'].append(part)
            trailer = f['trailer'].get(s, '')
            group['after'] = trailer
            if trailer:
                group = None
        syriac[ref] = groups
    chapters = defaultdict(list)
    for ref in sorted(set(hebrew) | set(syriac), key=lambda r: tuple(map(int, r.split('.')[1:]))):
        _, c, v = ref.split('.')
        row = {'id': ref, 'verse': int(v), 'he': hebrew.get(ref, []), 'syr': syriac.get(ref, []), 'alignment': 'reference-match' if ref in hebrew and ref in syriac else 'missing-side'}
        chapters[int(c)].append(row)
        for lang in ['he','syr']:
            for i, word in enumerate(row[lang]):
                for part, lid in enumerate(word['lemmas']):
                    hit = {'ref': ref, 'word': i, 'part': part, 'text': word['text']}
                    occurrences[lid].append(hit)
                    root = lexicon[lid].get('rootId')
                    if root:
                        roots[f'{lang}:{root}'].append(hit)
    for c, rows in chapters.items():
        write(OUT / 'chapters' / f'Gen.{c}.json', rows)
    write(OUT / 'lexicon/index.json', lexicon)
    bdb_dir = OUT / 'lexicon/bdb'
    # Only delete generated BDB JSON files; inputs and unrelated files are untouched.
    if bdb_dir.exists():
        for generated in bdb_dir.glob('*.json'):
            generated.unlink()
    for shard, entries in bdb_shards.items():
        write(bdb_dir / f'{shard}.json', entries)
    write(OUT / 'occurrences.json', {'lemmas': occurrences, 'roots': roots, 'scope': 'Genesis; Hebrew ketiv only'})
    unmatched = [r['id'] for rows in chapters.values() for r in rows if r['alignment'] != 'reference-match']
    report = {'hebrewVerses': len(hebrew), 'syriacVerses': len(syriac), 'alignedRows': sum(map(len, chapters.values())), 'unmatched': unmatched, 'note': 'Matching reference labels only. No semantic or word-to-word equivalence claimed.'}
    write(OUT / 'alignment-report.json', report)
    write(OUT / 'catalog.json', {'schemaVersion': 1, 'books': [{'id': 'Gen', 'name': 'Genesis', 'chapters': {str(c): [r['verse'] for r in rows] for c, rows in chapters.items()}}], 'scope': 'Genesis', 'provenance': lock['repositories']})
    shutil.copy(ROOT / 'sources.lock.json', OUT / 'sources.lock.json')
    for src, dst in [('NotoSansSyriac[wght].ttf','NotoSansSyriac.ttf'),('NotoSerifHebrew[wdth,wght].ttf','NotoSerifHebrew.ttf'),('notosanssyriac-OFL.txt','Syriac-OFL.txt'),('notoserifhebrew-OFL.txt','Hebrew-OFL.txt')]:
        shutil.copy(SRC / src, ROOT / 'public/fonts' / dst)
    notices = ROOT / 'notices'
    notices.mkdir(exist_ok=True)
    for name in ['hebrew-README.md','readme.md','syriac-README.md','syriac-LICENSE']:
        shutil.copy(SRC / name, notices / name)
    print(json.dumps(report, indent=2))
if __name__ == '__main__':
    main()
