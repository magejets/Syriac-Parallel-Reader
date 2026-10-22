import test from 'node:test';
import assert from 'node:assert/strict';
import {parseLocation,stripAccents,occurrenceVerses,defaultComponent} from '../public/core.js';
import {StaticBdbProvider,SefariaProvider} from '../public/providers.js';
import {consonantTransliteration} from '../public/transliteration.js';
test('consonant transliteration preserves unknown letters and omits vowel marks',()=>{
  assert.equal(consonantTransliteration('ܒܪܫܝܬ','syr'),'bršyt');
  assert.equal(consonantTransliteration('ܐܪܥܐ','syr'),'ʾrʿʾ');
  assert.equal(consonantTransliteration('בָּרָ֣א','he'),'brʾ');
  assert.equal(consonantTransliteration('ܔ','syr'),'ܔ');
});
const catalog={books:[{id:'Gen',chapters:{1:[1,2,3],2:[1,2]}}]};
test('deep links are bounded by the actual corpus',()=>{
  assert.deepEqual(parseLocation('#Gen.2.2',catalog),{book:'Gen',chapter:2,verse:2});
  assert.deepEqual(parseLocation('#Gen.999.999',catalog),{book:'Gen',chapter:1,verse:1});
  assert.deepEqual(parseLocation('#Gen.2.99',catalog),{book:'Gen',chapter:2,verse:1});
  assert.equal(parseLocation('#invalid',catalog).book,'Gen');
});
test('accent toggle preserves vowels, consonants and punctuation',()=>{
  assert.equal(stripAccents('בְּרֵאשִׁ֖ית׃'),'בְּרֵאשִׁית׃');
});
test('occurrence lists deduplicate verses while keeping token counts available',()=>{
  const hits=[{ref:'Gen.1.1',word:1},{ref:'Gen.1.1',word:2},{ref:'Gen.1.2',word:1}];
  assert.equal(occurrenceVerses(hits).length,2);assert.equal(hits.length,3);
});
test('word study defaults to the lexical component after attached prefixes',()=>{
  assert.equal(defaultComponent({lemmas:['he:c','he:d','he:776']},'he'),2);
  assert.equal(defaultComponent({parts:[{morphology:{sp:'conj'}},{morphology:{sp:'verb'}}]},'syr'),1);
});
test('BDB loads a single static shard and rejects malformed paths',async()=>{
  const paths=[];const provider=new StaticBdbProvider(async p=>{paths.push(p);return {'b.cw.aa':{body:'create'}};});
  assert.equal((await provider.resolve({bdb:'b.cw.aa'})).body,'create');
  assert.deepEqual(paths,['data/lexical/bdb/b.json']);
  assert.equal(await provider.resolve({bdb:'../secret'}),null);
});
test('Sefaria provider passes verse context and exposes metadata without remote HTML',async()=>{
  const previous=globalThis.fetch;let url;
  globalThis.fetch=async u=>{url=u;return {ok:true,json:async()=>[{headword:'ברא',parent_lexicon:'BDB Dictionary',content:{senses:[{definition:'<script>bad</script>'}]}}]};};
  try {
    const data=await new SefariaProvider().search('ברא','Gen.1.1');
    assert.equal(url.searchParams.get('lookup_ref'),'Genesis 1:1');
    assert.equal(data[0].source,'BDB Dictionary');assert.equal(data[0].content,undefined);
  } finally {globalThis.fetch=previous;}
});
