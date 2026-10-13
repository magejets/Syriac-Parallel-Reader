// Provider contract: resolve(lemma, context) -> attributed entry; explicit online providers optional.
export class StaticBdbProvider {
  constructor(load) { this.load = load; }
  async resolve(lemma) {
    if (!lemma.bdb || !/^[a-z]+(?:\.[a-z]+)+$/.test(lemma.bdb)) return null;
    const shard = await this.load(`data/lexicon/bdb/${lemma.bdb[0]}.json`);
    return shard[lemma.bdb] || null;
  }
}
export class SefariaProvider {
  async search(word, ref, signal) {
    const url = new URL(`https://www.sefaria.org/api/words/${encodeURIComponent(word)}`);
    url.searchParams.set('lookup_ref', ref.replace('Gen.', 'Genesis ').replace(/\.(\d+)$/, ':$1'));
    const response = await fetch(url, {signal, credentials: 'omit', cache: 'no-store'});
    if (!response.ok) throw new Error(`Sefaria returned ${response.status}`);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error('No lexical matches returned');
    // Metadata only: a generic lexicon response does not consistently include a reuse license.
    // Do not render or persist remote definition HTML without a resource-specific license policy.
    return data.map(entry => ({headword: entry.headword, source: entry.parent_lexicon,
      attribution: entry.parent_lexicon_details?.attribution || '',
      url: `https://www.sefaria.org/search?q=${encodeURIComponent(entry.headword || word)}&tab=text`}));
  }
}
