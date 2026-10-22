import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public/data'
class DataIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((DATA/'catalog.json').read_text())
        cls.lexicon=json.loads((DATA/'lexical/index.json').read_text())
        cls.alignment=json.loads((DATA/'alignment-report.json').read_text())
        cls.rows=[];cls.occ={}
        for book in cls.catalog['books']:
            cls.occ[book['id']]=json.loads((DATA/f'lexical/occurrences/{book["id"]}.json').read_text())
            for chapter in book['chapters']:
                cls.rows.extend(json.loads((DATA/f'text/{book["slug"]}/{chapter}.json').read_text()))
    def test_reference_coverage(self):
        self.assertEqual(len(self.catalog['books']),39)
        self.assertEqual(len(self.rows),self.alignment['unionRows'])
        self.assertEqual(len({r['id'] for r in self.rows}),self.alignment['unionRows'])
        self.assertTrue(any(not r['syr'] and r['he'] for r in self.rows))
        self.assertTrue(any(not r['he'] and r['syr'] for r in self.rows))
        self.assertEqual(len(self.alignment['missingSyriacReferences']),207)
        self.assertEqual(len(self.alignment['syriacOnlyReferences']),78)
        for row in self.rows:
            self.assertTrue(row['he'] or row['syr'], row['id'])
    def test_lexical_and_occurrence_integrity(self):
        for book in self.catalog['books']:
            expected={};book_rows=[r for r in self.rows if r['id'].startswith(book['id']+'.')]
            by_ref={r['id']:r for r in book_rows};index=self.occ[book['id']]
            for row in book_rows:
                for language in ['he','syr']:
                    for word in row[language]:
                        for lemma in word['lemmas']:
                            self.assertIn(lemma,self.lexicon)
                            expected[lemma]=expected.get(lemma,0)+1
            self.assertEqual(expected,{k:len(v) for k,v in index['lemmas'].items()},book['id'])
            for lemma,hits in index['lemmas'].items():
                lang=lemma.split(':')[0]
                for hit in hits:
                    word=by_ref[hit['ref']][lang][hit['word']]
                    self.assertEqual(word['lemmas'][hit['part']],lemma)
        for lemma in self.lexicon.values():
            if lemma.get('bdb'):
                p=DATA/f'lexical/bdb/{lemma["bdb"][0]}.json'
                self.assertIn(lemma['bdb'],json.loads(p.read_text()))
    def test_syriac_text_and_optional_annotations(self):
        gen=next(r for r in self.rows if r['id']=='Gen.1.1')
        self.assertEqual(gen['syr'][0]['text'],'ܒܪܫܝܬ')
        self.assertTrue(all(word['text'] for row in self.rows for word in row['syr']))
        self.assertTrue(any(not word['lemmas'] for row in self.rows for word in row['syr']))
    def test_consecutive_hebrew_punctuation_is_retained(self):
        verse=next(r for r in self.rows if r['id']=='Gen.1.5')
        self.assertEqual(verse['he'][-1]['after'],'׃ פ ')
    def test_homonymous_roots_remain_distinct(self):
        create=self.lexicon['he:1254a']
        fat=self.lexicon['he:1277']
        self.assertEqual(create['root'],fat['root'])
        self.assertNotEqual(create['rootId'],fat['rootId'])
        hits=self.occ['Gen']['roots']['he:'+create['rootId']]
        self.assertFalse(any(h['ref'].startswith('Gen.41.') for h in hits))
    def test_offline_inventory_excludes_corpus_data(self):
        release=(ROOT/'public/release.js').read_text().splitlines()
        paths=json.loads(release[1].split(' = ',1)[1].rstrip(';'))
        for path in paths:self.assertTrue((ROOT/'public'/path).is_file(),path)
        self.assertIn('./fonts/NotoSansSyriac.ttf',paths)
        self.assertFalse(any(p.startswith('./data/text/') for p in paths))
        self.assertFalse(any(p.startswith('./data/lexical/') for p in paths))
if __name__=='__main__':unittest.main()
