"""Dependency-free 39-book OSIS + Text-Fabric exporter. No runtime backend."""
import json, re, hashlib, shutil
import unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC, OUT = ROOT / 'sources', ROOT / 'public/data'
NS = {'o': 'http://www.bibletechnologies.net/2003/OSIS/namespace', 'l': 'http://openscriptures.github.com/morphhb/namespace'}
BOOKS = [
    ('Gen','Genesis'),('Exod','Exodus'),('Lev','Leviticus'),('Num','Numbers'),('Deut','Deuteronomy'),
    ('Josh','Joshua'),('Judg','Judges'),('Ruth','Ruth'),('1Sam','1 Samuel'),('2Sam','2 Samuel'),
    ('1Kgs','1 Kings'),('2Kgs','2 Kings'),('1Chr','1 Chronicles'),('2Chr','2 Chronicles'),
    ('Ezra','Ezra'),('Neh','Nehemiah'),('Esth','Esther'),('Job','Job'),('Ps','Psalms'),
    ('Prov','Proverbs'),('Eccl','Ecclesiastes'),('Song','Song of Songs'),('Isa','Isaiah'),
    ('Jer','Jeremiah'),('Lam','Lamentations'),('Ezek','Ezekiel'),('Dan','Daniel'),('Hos','Hosea'),
    ('Joel','Joel'),('Amos','Amos'),('Obad','Obadiah'),('Jonah','Jonah'),('Mic','Micah'),
    ('Nah','Nahum'),('Hab','Habakkuk'),('Zeph','Zephaniah'),('Hag','Haggai'),('Zech','Zechariah'),('Mal','Malachi'),
]
SYRIAC_BOOKS = {
    'Genesis':'Gen','Exodus':'Exod','Leviticus':'Lev','Numbers':'Num','Deuteronomy':'Deut',
    'Joshua':'Josh','Judges':'Judg','Ruth':'Ruth','1_Samuel':'1Sam','2_Samuel':'2Sam',
    '1_Kings':'1Kgs','2_Kings':'2Kgs','1_Chronicles':'1Chr','2_Chronicles':'2Chr',
    'Ezra':'Ezra','Nehemiah':'Neh','Esther':'Esth','Job':'Job','Psalms':'Ps','Proverbs':'Prov',
    'Ecclesiastes':'Eccl','Song_of_Songs':'Song','Isaiah':'Isa','Jeremiah':'Jer','Lamentations':'Lam',
    'Ezekiel':'Ezek','Daniel':'Dan','Hosea':'Hos','Joel':'Joel','Amos':'Amos','Obadiah':'Obad',
    'Jonah':'Jonah','Micah':'Mic','Nahum':'Nah','Habakkuk':'Hab','Zephaniah':'Zeph','Haggai':'Hag',
    'Zechariah':'Zech','Malachi':'Mal',
}
PESHITTA_BOOKS = {
    'Gn':'Gen','Ex':'Exod','Lv':'Lev','Nm':'Num','Dt':'Deut','Jos':'Josh','Jd':'Judg','Ru':'Ruth',
    'Sm1':'1Sam','Sm2':'2Sam','Rg1':'1Kgs','Rg2':'2Kgs','Chr1':'1Chr','Chr2':'2Chr',
    'Ezr':'Ezra','Neh':'Neh','Est':'Esth','Jb':'Job','Ps':'Ps','Pr':'Prov','Ec':'Eccl','Ct':'Song',
    'Is':'Isa','Jr':'Jer','Thr':'Lam','Ez':'Ezek','Dn':'Dan','Hs':'Hos','Jl':'Joel','Am':'Amos',
    'Ob':'Obad','Jon':'Jonah','Mi':'Mic','Na':'Nah','Hb':'Hab','Zf':'Zeph','Hg':'Hag','Zc':'Zech','Sa':'Zech','Ml':'Mal',
}
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
def tf(name, edges=False, dataset='syriac'):
    """Read explicit/range/implicit node numbers; retain significant whitespace."""
    lines = (SRC / dataset / f'{name}.tf').read_text().splitlines()
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
    lexicon, occurrences, bdb_shards = {}, defaultdict(lambda: {'lemmas': defaultdict(list), 'roots': defaultdict(list)}), defaultdict(dict)
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
    for book, _ in BOOKS:
        for verse in ET.parse(SRC / 'hebrew' / f'{book}.xml').findall('.//o:verse', NS):
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
    annotated_syriac = {}
    for name, book in f['book'].items():
        if book not in SYRIAC_BOOKS:
            continue
        book_id = SYRIAC_BOOKS[book]
        bookslots = set(slots[name])
        chapter_for = {}
        for node, c in f['chapter'].items():
            if slots[node] and slots[node][0] in bookslots:
                for s in slots[node]:
                    chapter_for[s] = int(c)
        for node, v in f['verse'].items():
            verse_slots = slots[node]
            if not verse_slots or verse_slots[0] not in bookslots or verse_slots[0] not in chapter_for:
                continue
            ref = f'{book_id}.{chapter_for[verse_slots[0]]}.{v}'
            if ref in annotated_syriac:
                continue
            groups, group = [], None
            for s in verse_slots:
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
            annotated_syriac[ref] = groups
    p = {n: tf(n, edges=(n == 'oslots'), dataset='peshitta') for n in ['otype','oslots','book','chapter','verse','word','trailer']}
    p_slots = p['oslots']
    syriac = {}
    for node, kind in p['otype'].items():
        if kind != 'verse':
            continue
        book = PESHITTA_BOOKS.get(p['book'].get(node, ''))
        if not book:
            continue
        chapter, verse = int(p['chapter'][node]), int(p['verse'][node])
        ref = f'{book}.{chapter}.{verse}'
        words = []
        for slot in p_slots[node]:
            surface = p['word'].get(slot, '')
            if not surface:
                continue
            words.append({'id': f'p{slot}', 'text': surface, 'after': p['trailer'].get(slot, ' '), 'lemmas': [], 'parts': []})
        syriac[ref] = words

    def normalize_syriac(value):
        decomposed = unicodedata.normalize('NFD', value)
        return ''.join(c for c in decomposed if unicodedata.category(c) != 'Mn')
    for ref, base_words in syriac.items():
        analysis_words = annotated_syriac.get(ref, [])
        base_norm = [normalize_syriac(w['text']) for w in base_words]
        analysis_norm = [normalize_syriac(w['text']) for w in analysis_words]
        # Keep lexical/morphology pointers only for exact, ordered token matches.
        from difflib import SequenceMatcher
        for a, b, size in SequenceMatcher(a=base_norm, b=analysis_norm, autojunk=False).get_matching_blocks():
            for offset in range(size):
                base, analyzed = base_words[a+offset], analysis_words[b+offset]
                base['lemmas'] = analyzed['lemmas']
                base['parts'] = analyzed['parts']
    chapters = defaultdict(list)
    order = {book: index for index, (book, _) in enumerate(BOOKS)}
    # Keep the union of both source reference sets. Syriac-only labels stay
    # visible as Syriac-only rows instead of being dropped or falsely paired.
    all_refs = set(hebrew) | set(syriac)
    for ref in sorted(all_refs, key=lambda r: (order.get(r.split('.')[0], 999), *map(int, r.split('.')[1:]))):
        book, c, v = ref.split('.')
        row = {'id': ref, 'verse': int(v), 'he': hebrew.get(ref, []), 'syr': syriac.get(ref, []), 'alignment': 'reference-match' if ref in hebrew and ref in syriac else 'missing-side'}
        chapters[(book, int(c))].append(row)
        book_occurrences = occurrences[book]
        for lang in ['he','syr']:
            for i, word in enumerate(row[lang]):
                for part, lid in enumerate(word['lemmas']):
                    hit = {'ref': ref, 'word': i, 'part': part, 'text': word['text']}
                    book_occurrences['lemmas'][lid].append(hit)
                    root = lexicon[lid].get('rootId')
                    if root:
                        book_occurrences['roots'][f'{lang}:{root}'].append(hit)
    for (book, c), rows in chapters.items():
        book_name = next(name for code, name in BOOKS if code == book)
        book_slug = re.sub(r'[^a-z0-9]+', '-', book_name.lower()).strip('-')
        write(OUT / 'text' / book_slug / f'{c}.json', rows)
    write(OUT / 'lexical/index.json', lexicon)
    bdb_dir = OUT / 'lexical/bdb'
    # Only delete generated BDB JSON files; inputs and unrelated files are untouched.
    if bdb_dir.exists():
        for generated in bdb_dir.glob('*.json'):
            generated.unlink()
    for shard, entries in bdb_shards.items():
        write(bdb_dir / f'{shard}.json', entries)
    occurrence_dir = OUT / 'lexical/occurrences'
    (OUT / 'lexical/occurrences.json').unlink(missing_ok=True)
    if occurrence_dir.exists():
        for generated in occurrence_dir.glob('*.json'):
            generated.unlink()
    for book, index in occurrences.items():
        write(occurrence_dir / f'{book}.json', {'lemmas': index['lemmas'], 'roots': index['roots'], 'scope': f'{book}; Hebrew ketiv and Syriac Peshitta'})
    unmatched = [r['id'] for rows in chapters.values() for r in rows if r['alignment'] != 'reference-match']
    missing_syriac = sorted(set(hebrew) - set(syriac), key=lambda r: (order.get(r.split('.')[0], 999), *map(int, r.split('.')[1:])))
    missing_hebrew = sorted(set(syriac) - set(hebrew), key=lambda r: (order.get(r.split('.')[0], 999), *map(int, r.split('.')[1:])))
    report = {'hebrewVerses': len(hebrew), 'syriacVerses': len(syriac), 'unionRows': sum(map(len, chapters.values())), 'missingSyriacReferences': missing_syriac, 'syriacOnlyReferences': missing_hebrew, 'syriacCoverageBooks': sorted({ref.split('.')[0] for ref in syriac}, key=order.get), 'note': 'All source references are retained. Texts appear together only where their reference labels match; no semantic or word-to-word equivalence is claimed.'}
    write(OUT / 'alignment-report.json', report)
    catalog_books = []
    for book, name in BOOKS:
        book_chapters = {str(c): [r['verse'] for r in rows] for (b, c), rows in chapters.items() if b == book}
        if book_chapters:
            slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
            catalog_books.append({'id': book, 'name': name, 'slug': slug, 'chapters': book_chapters})
    write(OUT / 'catalog.json', {'schemaVersion': 1, 'books': catalog_books, 'scope': 'Jewish canon (39 books)', 'provenance': lock['repositories']})
    shutil.copy(ROOT / 'sources.lock.json', OUT / 'sources.lock.json')
    for src, dst in [('NotoSansSyriac[wght].ttf','NotoSansSyriac.ttf'),('NotoSerifHebrew[wdth,wght].ttf','NotoSerifHebrew.ttf'),('notosanssyriac-OFL.txt','Syriac-OFL.txt'),('notoserifhebrew-OFL.txt','Hebrew-OFL.txt')]:
        shutil.copy(SRC / src, ROOT / 'public/fonts' / dst)
    notices = ROOT / 'notices'
    notices.mkdir(exist_ok=True)
    for name in ['hebrew-README.md','readme.md','syriac-README.md','syriac-LICENSE','peshitta-about.md']:
        shutil.copy(SRC / name, notices / name)
    print(json.dumps(report, indent=2))
if __name__ == '__main__':
    main()
