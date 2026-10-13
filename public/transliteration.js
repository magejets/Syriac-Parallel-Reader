// A consonant spelling aid, not reconstructed pronunciation or supplied vowels.
// Base letters follow the Unicode Syriac/Hebrew repertoires; unknown characters remain visible.
const syr = {'ܐ':'ʾ','ܒ':'b','ܓ':'g','ܕ':'d','ܗ':'h','ܘ':'w','ܙ':'z','ܚ':'ḥ','ܛ':'ṭ','ܝ':'y','ܟ':'k','ܠ':'l','ܡ':'m','ܢ':'n','ܣ':'s','ܤ':'s','ܥ':'ʿ','ܦ':'p','ܨ':'ṣ','ܩ':'q','ܪ':'r','ܫ':'š','ܬ':'t'};
const he = {'א':'ʾ','ב':'b','ג':'g','ד':'d','ה':'h','ו':'w','ז':'z','ח':'ḥ','ט':'ṭ','י':'y','כ':'k','ך':'k','ל':'l','מ':'m','ם':'m','נ':'n','ן':'n','ס':'s','ע':'ʿ','פ':'p','ף':'p','צ':'ṣ','ץ':'ṣ','ק':'q','ר':'r','ש':'š','ת':'t'};
export function consonantTransliteration(text, language) {
  const alphabet = language === 'syr' ? syr : he;
  return Array.from(text.normalize('NFD')).filter(c => !/\p{Mark}/u.test(c)).map(c => alphabet[c] ?? c).join('');
}
