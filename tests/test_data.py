import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'public/data'
class DataIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((DATA/'catalog.json').read_text())
        cls.lexicon=json.loads((DATA/'lexicon/index.json').read_text())
        cls.occ=json.loads((DATA/'occurrences.json').read_text())
        cls.rows=[r for c in range(1,51) for r in json.loads((DATA/f'chapters/Gen.{c}.json').read_text())]
    def test_reference_coverage(self):
        self.assertEqual(len(self.rows),1533)
        self.assertEqual(len({r['id'] for r in self.rows}),1533)
        self.assertEqual(self.rows[-1]['id'],'Gen.50.26')
        for row in self.rows:
            self.assertTrue(row['he']);self.assertTrue(row['syr'])
    def test_lexical_and_occurrence_integrity(self):
        expected={}
        by_ref={r['id']:r for r in self.rows}
        for row in self.rows:
            for language in ['he','syr']:
                for word in row[language]:
                    for lemma in word['lemmas']:
                        self.assertIn(lemma,self.lexicon)
                        expected[lemma]=expected.get(lemma,0)+1
        self.assertEqual(expected,{k:len(v) for k,v in self.occ['lemmas'].items()})
        for lemma,hits in self.occ['lemmas'].items():
            lang=lemma.split(':')[0]
            for hit in hits:
                word=by_ref[hit['ref']][lang][hit['word']]
                self.assertEqual(word['lemmas'][hit['part']],lemma)
        for lemma in self.lexicon.values():
            if lemma.get('bdb'):
                p=DATA/f'lexicon/bdb/{lemma["bdb"][0]}.json'
                self.assertIn(lemma['bdb'],json.loads(p.read_text()))
    def test_syriac_joining_and_genesis_opening(self):
        words=self.rows[0]['syr']
        self.assertEqual(words[0]['text'],'ܒܪܫܝܬ')
        self.assertEqual(len(words[0]['parts']),2)
        self.assertEqual(words[1]['text'],'ܒܪܐ')
        for row in self.rows:
            for word in row['syr']:
                self.assertEqual(word['text'],''.join(p['text'] for p in word['parts']))
                self.assertEqual(word['lemmas'],[p['lemma'] for p in word['parts']])
    def test_consecutive_hebrew_punctuation_is_retained(self):
        verse=next(r for r in self.rows if r['id']=='Gen.1.5')
        self.assertEqual(verse['he'][-1]['after'],'׃ פ ')
    def test_homonymous_roots_remain_distinct(self):
        create=self.lexicon['he:1254a']
        fat=self.lexicon['he:1277']
        self.assertEqual(create['root'],fat['root'])
        self.assertNotEqual(create['rootId'],fat['rootId'])
        hits=self.occ['roots']['he:'+create['rootId']]
        self.assertFalse(any(h['ref'].startswith('Gen.41.') for h in hits))
    def test_offline_inventory_is_complete(self):
        release=(ROOT/'public/release.js').read_text().splitlines()
        paths=json.loads(release[1].split(' = ',1)[1].rstrip(';'))
        for path in paths:self.assertTrue((ROOT/'public'/path).is_file(),path)
        for c in range(1,51):self.assertIn(f'./data/chapters/Gen.{c}.json',paths)
        self.assertIn('./fonts/NotoSansSyriac.ttf',paths)
        self.assertNotIn('./data/occurrences.json',paths)
        self.assertFalse(any(p.startswith('./data/lexicon/') for p in paths))
if __name__=='__main__':unittest.main()
