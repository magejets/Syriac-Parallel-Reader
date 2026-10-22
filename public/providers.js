// Provider contract: resolve(lemma, context) -> attributed entry; explicit online providers optional.
export class StaticBdbProvider {
  constructor(load) { this.load = load; }
  async resolve(lemma) {
    if (!lemma.bdb || !/^[a-z]+(?:\.[a-z]+)+$/.test(lemma.bdb)) return null;
    const shard = await this.load(`data/lexical/bdb/${lemma.bdb[0]}.json`);
    return shard[lemma.bdb] || null;
  }
}
export class SefariaProvider {
  async search(word, ref, signal) {
    const names = {Gen:'Genesis',Exod:'Exodus',Lev:'Leviticus',Num:'Numbers',Deut:'Deuteronomy',Josh:'Joshua',Judg:'Judges',Ruth:'Ruth',
      '1Sam':'I Samuel','2Sam':'II Samuel','1Kgs':'I Kings','2Kgs':'II Kings','1Chr':'I Chronicles','2Chr':'II Chronicles',
      Ezra:'Ezra',Neh:'Nehemiah',Esth:'Esther',Job:'Job',Ps:'Psalms',Prov:'Proverbs',Eccl:'Ecclesiastes',Song:'Song of Songs',
      Isa:'Isaiah',Jer:'Jeremiah',Lam:'Lamentations',Ezek:'Ezekiel',Dan:'Daniel',Hos:'Hosea',Joel:'Joel',Amos:'Amos',
      Obad:'Obadiah',Jonah:'Jonah',Mic:'Micah',Nah:'Nahum',Hab:'Habakkuk',Zeph:'Zephaniah',Hag:'Haggai',Zech:'Zechariah',Mal:'Malachi'};
    const parsed = /^([A-Za-z0-9]+)\.(\d+)\.(\d+)$/.exec(ref);
    if (!parsed || !names[parsed[1]]) throw new Error('Invalid verse reference');
    const url = new URL(`https://www.sefaria.org/api/words/${encodeURIComponent(word)}`);
    url.searchParams.set('lookup_ref', `${names[parsed[1]]} ${parsed[2]}:${parsed[3]}`);
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
