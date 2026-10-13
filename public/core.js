export function parseLocation(hash, catalog) {
  const match = /^#([A-Za-z0-9]+)\.(\d+)\.(\d+)$/.exec(hash);
  const book = catalog.books.find(b => b.id === match?.[1]) || catalog.books[0];
  const chapter = match && book.chapters[Number(match[2])] ? Number(match[2]) : 1;
  const verses = book.chapters[chapter];
  const verse = match && verses.includes(Number(match[3])) ? Number(match[3]) : verses[0];
  return {book: book.id, chapter, verse};
}
export const stripAccents = text => text.replace(/[\u0591-\u05af]/g, '');
export function occurrenceVerses(hits) {
  return [...new Map(hits.map(h => [h.ref, h])).values()];
}
export function defaultComponent(word, language) {
  if (language === 'he') {
    const index = word.lemmas.findLastIndex(l => /\d/.test(l));
    return Math.max(0, index);
  }
  const index = word.parts?.findIndex(p => !['prep', 'conj', 'art'].includes(p.morphology.sp));
  return index >= 0 ? index : 0;
}
