import {parseLocation, stripAccents, occurrenceVerses, defaultComponent} from './core.js';
import {StaticBdbProvider, SefariaProvider} from './providers.js';
import {consonantTransliteration} from './transliteration.js';
const $ = id => document.getElementById(id);
const memo = new Map();
async function load(path) {
  if (!memo.has(path)) memo.set(path, (async () => {
    const compressible = path.startsWith('data/text/') || path.startsWith('data/lexical/');
    if (compressible && 'DecompressionStream' in globalThis) {
      try {
        const compressed = await fetch(new URL(`${path}.gz`, import.meta.url));
        if (compressed.ok && compressed.body) {
          const body = compressed.body.pipeThrough(new DecompressionStream('gzip'));
          return await new Response(body).json();
        }
      } catch {}
    }
    const response = await fetch(new URL(path, import.meta.url));
    if (!response.ok) throw new Error(`Could not load ${path}`);
    return response.json();
  })().catch(e => {memo.delete(path); throw e;}));
  return memo.get(path);
}
function node(tag, text, className) {
  const el = document.createElement(tag);
  if (text != null) el.textContent = text;
  if (className) el.className = className;
  return el;
}
function save(key, value) {try {localStorage.setItem(key, value);return true;} catch {return false;}}
function read(key) {try {return localStorage.getItem(key);} catch {return null;}}
function storedArray(key) {
  try {const value = JSON.parse(read(key) || '[]');return Array.isArray(value) ? value.filter(v => typeof v === 'string') : [];} catch {return [];}
}
let catalog, location, rows = [], navigationId = 0, studyId = 0, selectedButton, installPrompt, activeBookOption = -1;
const readVerses = new Set(storedArray('between-lines-read-verses'));
const readingDays = new Set(storedArray('between-lines-reading-days').filter(v => /^\d{4}-\d{2}-\d{2}$/.test(v)));
const bdb = new StaticBdbProvider(load), sefaria = new SefariaProvider();
const reader = $('reader'), study = $('study');
const localDay = (date = new Date()) => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
function streakLength() {
  const today = new Date();
  let cursor = readingDays.has(localDay(today)) ? today : new Date(today.getFullYear(), today.getMonth(), today.getDate()-1);
  if (!readingDays.has(localDay(cursor))) return 0;
  let count = 0;
  while (readingDays.has(localDay(cursor))) {count++;cursor = new Date(cursor.getFullYear(), cursor.getMonth(), cursor.getDate()-1);}
  return count;
}
function updateReadingSummary() {
  const readCount = rows.filter(row => readVerses.has(row.id)).length;
  $('chapter-progress').textContent = `${readCount} of ${rows.length} verses read`;
  const streak = streakLength();
  $('streak').textContent = `${streak}-day streak`;
  $('streak').setAttribute('aria-label', `${streak} day reading streak`);
}
function markVerse(ref, checked) {
  if (checked) {readVerses.add(ref);readingDays.add(localDay());}
  else readVerses.delete(ref);
  const persisted = save('between-lines-read-verses', JSON.stringify([...readVerses])) && save('between-lines-reading-days', JSON.stringify([...readingDays]));
  const row = document.querySelector(`.verse-row[data-ref="${ref}"]`);
  row?.classList.toggle('read', checked);
  updateReadingSummary();
  $('reading-save-status').textContent = persisted ? 'Progress saved on this device.' : 'Progress could not be saved in this browser.';
}
function options(select, values, value) {
  select.replaceChildren(...values.map(([id, title]) => {const o = node('option', title);o.value = id;return o;}));
  select.value = value;select.disabled = false;
}
function bookOptions(books, currentId) {
  const input = $('book'), list = $('book-options');
  input.value = books.find(book => book.id === currentId)?.name || '';
  input.disabled = false;
  list.hidden = true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');
  if (input.dataset.pickerReady) return;
  input.dataset.pickerReady = 'true';
  const render = (query = '', highlightFirst = false) => {
    const normalized = query.trim().toLocaleLowerCase();
    const matches = catalog.books.filter(book => `${book.name} ${book.id}`.toLocaleLowerCase().includes(normalized));
    activeBookOption = highlightFirst && matches.length ? 0 : -1;
    list.replaceChildren(...(matches.length ? matches.map((book,index) => {
      const option = node('div',book.name,'book-option');
      option.id = `book-option-${index}`;option.setAttribute('role','option');option.setAttribute('aria-selected',index===activeBookOption?'true':'false');
      option.onmousedown = event => event.preventDefault();
      option.onclick = () => chooseBook(book);
      return option;
    }) : [node('div','No matching books','book-empty')]));
    list.hidden = false;input.setAttribute('aria-expanded','true');
    input.removeAttribute('aria-activedescendant');
    if (activeBookOption >= 0) input.setAttribute('aria-activedescendant',`book-option-${activeBookOption}`);
  };
  const close = (restore = true) => {
    list.hidden = true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');
    if (restore && location) input.value = catalog.books.find(book => book.id === location.book)?.name || '';
  };
  function chooseBook(book) {
    input.value = book.name;list.hidden = true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');
    if (location && location.book !== book.id) navigate({book:book.id,chapter:1,verse:1});
  }
  function moveActive(direction) {
    const options = [...list.querySelectorAll('[role="option"]')];
    if (!options.length) return;
    activeBookOption = Math.max(0,Math.min(options.length-1,activeBookOption < 0 ? (direction > 0 ? 0 : options.length-1) : activeBookOption+direction));
    options.forEach((option,index)=>option.setAttribute('aria-selected',index===activeBookOption?'true':'false'));
    input.setAttribute('aria-activedescendant',options[activeBookOption].id);options[activeBookOption].scrollIntoView({block:'nearest'});
  }
  input.addEventListener('focus',()=>{input.select();render();});
  input.addEventListener('click',()=>{input.select();render();});
  input.addEventListener('input',()=>render(input.value,true));
  input.addEventListener('keydown',event=>{
    if (event.key==='ArrowDown'||event.key==='ArrowUp') {event.preventDefault();if(list.hidden)render();moveActive(event.key==='ArrowDown'?1:-1);}
    else if (event.key==='Enter'&&!list.hidden) {
      event.preventDefault();
      const option=list.querySelectorAll('[role="option"]')[activeBookOption];
      if (option) chooseBook(catalog.books.find(book=>book.name===option.textContent));
    } else if (event.key==='Escape'&&!list.hidden) {event.preventDefault();close();}
  });
  input.addEventListener('blur',()=>setTimeout(()=>close(),120));
}
function remember() {
  const hash = `#${location.book}.${location.chapter}.${location.verse}`;
  history.replaceState(null, '', hash);save('between-lines-location', hash);
}
function selectVerse(verse, scroll = true) {
  document.documentElement.style.setProperty('--nav-height', `${document.querySelector('.toolbar').getBoundingClientRect().height}px`);
  location.verse = verse; $('verse').value = verse;remember();
  document.querySelectorAll('.verse-row').forEach(row => row.classList.toggle('current', Number(row.dataset.verse) === verse));
  if (scroll) document.getElementById(`verse-${verse}`)?.scrollIntoView({block: 'start'});
}
function hideStudy() {
  study.classList.remove('open');$('close-study').hidden = true;
  selectedButton?.focus({preventScroll:true});
}
async function navigate(target, scroll = true) {
  const sequence = ++navigationId;
  ++studyId;hideStudy(); selectedButton = null;
  $('reader-status').hidden = false;$('reader-status').textContent = 'Loading passage…';
  $('previous').disabled = $('next').disabled = $('next-bottom').disabled = true;
  try {
    const bookInfo = catalog.books.find(book => book.id === target.book);
    const data = await load(`data/text/${bookInfo.slug}/${target.chapter}.json`);
    if (sequence !== navigationId) return;
    location = target; rows = data;
    const book = catalog.books.find(b => b.id === location.book);
    bookOptions(catalog.books, book.id);
    options($('chapter'), Object.keys(book.chapters).map(c => [c,c]), location.chapter);
    options($('verse'), book.chapters[location.chapter].map(v => [v,v]), location.verse);
    $('passage-title').replaceChildren(document.createTextNode(`${book.name} `), node('span', location.chapter));
    document.title = `${book.name} ${location.chapter} · Between the Lines`;
    renderPassage();$('reader-status').hidden = true;
    updateReadingSummary();
    const bookIndex = catalog.books.findIndex(item => item.id === location.book);
    const chapterNumbers = Object.keys(book.chapters).map(Number).sort((a,b) => a-b);
    const chapterIndex = chapterNumbers.indexOf(location.chapter);
    $('previous').disabled = bookIndex === 0 && chapterIndex === 0;
    $('next').disabled = $('next-bottom').disabled = bookIndex === catalog.books.length - 1 && chapterIndex === chapterNumbers.length - 1;
    selectVerse(location.verse, scroll && location.verse > 1);
    if (scroll && location.verse === 1) $('passage-title').scrollIntoView({block:'start'});
  } catch (error) {
    if (sequence !== navigationId) return;
    $('reader-status').replaceChildren(node('span', `${error.message}. `));
    const retry = node('button', 'Retry');retry.onclick = () => navigate(target, scroll);$('reader-status').append(retry);
  }
}
function renderPassage() {
  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const article = node('article', null, `verse-row${readVerses.has(row.id) ? ' read' : ''}`); article.id = `verse-${row.verse}`;article.dataset.verse = row.verse;article.dataset.ref = row.id;
    const book = catalog.books.find(b => b.id === location.book);
    article.setAttribute('aria-label', `${book.name} ${location.chapter}:${row.verse}`);
    const meta = node('div', null, 'verse-meta');
    meta.append(node('span', `${location.chapter}:${row.verse}`, 'verse-number'));
    const readLabel = node('label', null, 'read-check');
    const readInput = node('input');readInput.type = 'checkbox';readInput.checked = readVerses.has(row.id);readInput.setAttribute('aria-label', `Read ${book.name} ${location.chapter}:${row.verse}`);
    readInput.onchange = () => markVerse(row.id, readInput.checked);
    readLabel.append(readInput, node('span', 'Read'));
    meta.append(readLabel);article.append(meta);
    for (const language of ['he','syr']) {
      const side = node('div', null, 'verse-side');side.dataset.label = language === 'he' ? 'HEBREW' : 'SYRIAC';
      const script = node('div', null, `script ${language}`);script.dir = 'rtl';script.lang = language === 'he' ? 'he' : 'syr';
      if (!row[language].length) script.append(node('span', 'This verse is not found in this source.', 'missing'));
      row[language].forEach((word, index) => {
        const button = node('button', language === 'he' && !$('accents').checked ? stripAccents(word.text) : word.text, 'word');
        button.dataset.word = `${row.id}/${language}/${index}`;button.setAttribute('aria-label', `${word.text}, word study, ${book.name} ${location.chapter}:${row.verse}`);
        button.onclick = () => {selectVerse(row.verse, false);openStudy(row, language, index, button);};
        script.append(button, node('span', word.after, 'punct'));
      });
      side.append(script);article.append(side);
    }
    fragment.append(article);
  }
  $('verses').replaceChildren(fragment);
}
function section(title) {const s = node('section', null, 'study-section');s.append(node('h3', title));return s;}
async function openStudy(row, language, index, button, component) {
  const sequence = ++studyId;
  document.querySelector('.word.selected')?.classList.remove('selected');
  selectedButton = button;button.classList.add('selected');
  study.classList.add('open');$('close-study').hidden = false;
  study.scrollTop = 0;
  const bookName = catalog.books.find(item => item.id === location.book)?.name || location.book;
  $('study-title').textContent = `${language === 'he' ? 'Hebrew' : 'Syriac'} · ${bookName} ${location.chapter}:${row.verse}`;
  const content = $('study-content'), word = row[language][index];
  const showWord = () => {
    content.replaceChildren(node('div', word.text, `study-word ${language}`));
    const transliteration = node('p', `Consonant transliteration: ${consonantTransliteration(word.text, language)}`, 'meta transliteration');
    transliteration.dir = 'ltr';content.append(transliteration);
    content.append(node('p', 'Unvocalized spelling aid; vowels and pronunciation are not reconstructed.', 'meta'));
  };
  showWord();content.append(node('p', 'Loading word study…', 'meta'));
  try {
    const [lexicon, occurrenceIndex] = await Promise.all([load('data/lexical/index.json'), load(`data/lexical/occurrences/${location.book}.json`)]);
    if (sequence !== studyId) return;
    component ??= defaultComponent(word, language);
    const lid = word.lemmas?.[component], lemma = lid ? lexicon[lid] : null;
    showWord();
    const choices = node('div', null, 'lemma-choices');
    word.lemmas.forEach((id, i) => {const choice = node('button', word.parts?.[i]?.text || lexicon[id]?.headword || id);choice.setAttribute('aria-pressed', String(i === component));choice.onclick = () => openStudy(row, language, index, button, i);choices.append(choice);});
    if (word.lemmas.length > 1) {content.append(node('p', 'Choose a word component:', 'meta'), choices);}
    content.append(node('p', lemma?.gloss || 'No gloss supplied', 'gloss'));
    if (lemma || lid) content.append(node('p', `Lemma: ${lemma?.headword || lid}${language === 'syr' ? ' (ETCBC transcription)' : ''}`, 'meta'));
    else if (language === 'syr') content.append(node('p', 'No word-level lexical analysis is supplied for this word.', 'meta'));
    if (lemma?.transliteration) content.append(node('p', `Lexicon transliteration: ${lemma.transliteration}`, 'meta'));
    if (word.qere) content.append(node('p', `Written form (ketiv). Recorded reading (qere): ${word.qere}`, 'meta'));
    const grammar = section('Morphology');
    if (language === 'he') {grammar.append(node('p', `${word.morphology} · Open Scriptures code`));const link = node('a','Code guide ↗');link.href='https://hb.openscriptures.org/parsing/HebrewMorphologyCodes.html';link.target='_blank';link.rel='noopener noreferrer';grammar.append(link);}
    else if (word.parts?.[component]) {
      const labels = {sp:'Part of speech',vs:'Stem',vt:'Tense',gn:'Gender',nu:'Number',ps:'Person',st:'State'};
      const values = {subs:'noun',verb:'verb',prep:'preposition',conj:'conjunction',adjv:'adjective',advb:'adverb',nmpr:'proper name',sg:'singular',pl:'plural',m:'masculine',f:'feminine',pe:'Peal',pa:'Pael',ap:'Aphel',pf:'perfect',ipf:'imperfect',emph:'emphatic',cst:'construct',abs:'absolute'};
      for (const [key, value] of Object.entries(word.parts[component].morphology)) grammar.append(node('p', `${labels[key]}: ${values[value] || value}`));
    } else grammar.append(node('p', 'No word-level morphology is supplied for this word.'));
    content.append(grammar);
    if (language === 'he' && lemma?.bdb) {
      const details = node('details', null, 'study-section');details.append(node('summary', 'Read bundled BDB entry'));
      details.addEventListener('toggle', async () => {
        if (!details.open || details.dataset.loaded) return;
        details.querySelector('.bdb-body')?.remove();
        details.dataset.loaded = 'yes';const body = node('p','Loading…','bdb-body');details.append(body);
        try {const entry = await bdb.resolve(lemma);body.textContent = entry?.body || 'Entry not included.';details.append(node('p', `Abridged transcription · BDB ${lemma.bdb} · ${entry?.source || lemma.source} · CC BY 4.0`, 'lex-source'));}
        catch {body.textContent = 'Could not load this entry. Close and reopen to retry.';delete details.dataset.loaded;}
      });
      content.append(details);
    }
    const hits = occurrenceIndex.lemmas[lid] || [];
    content.append(occurrenceSection('Same lemma', hits, language));
    if (lemma?.rootId) {content.append(node('p', `Lexical root: ${lemma.root} (Open Scriptures etymology)`, 'meta'));content.append(occurrenceSection('Same lexical root', occurrenceIndex.roots[`${language}:${lemma.rootId}`] || [], language));}
    else content.append(node('p', 'No verified root grouping supplied for this lemma.', 'meta'));
    if (language === 'he') {
      const online = section('More on Sefaria');const search = node('button', 'Find lexical matches online ↗');const result = node('div');
      search.onclick = async () => {
        search.disabled = true;result.replaceChildren(node('p','Contacting Sefaria…','meta'));
        const controller = new AbortController();const timeout = setTimeout(() => controller.abort(), 12000);
        try {
          const query = (lemma?.headword || word.text).replace(/[\u0591-\u05c7]/g, '');
          const matches = await sefaria.search(query, row.id, controller.signal);
          if (sequence !== studyId) return;
          result.replaceChildren(node('p', `${matches.length} lexical matches. Open on Sefaria to read.`, 'meta'));
          for (const match of matches) {const p=node('p');const a=node('a',`${match.headword} · ${match.source} ↗`);a.href=match.url;a.target='_blank';a.rel='noopener noreferrer';p.append(a);result.append(p);}
          result.append(node('p','Online results are not saved offline. Resource licenses vary.','lex-source'));
        } catch {result.replaceChildren(node('p','Sefaria lookup unavailable. Your bundled word study remains available.','meta'));}
        finally {clearTimeout(timeout);search.disabled=false;}
      };
      online.append(search,result);content.append(online);
    }
    content.append(node('p', `${lemma?.source || 'Source unavailable'} · ${lemma?.license || ''}`, 'lex-source'));
  } catch (e) {
    if (sequence === studyId) {showWord();content.append(node('p','Lexical resources need an internet connection. Your saved text and consonant transliteration remain available.','meta'));const retry=node('button','Retry word study');retry.onclick=()=>openStudy(row,language,index,button,component);content.append(retry);}
  }
}
function occurrenceSection(title, hits, language) {
  const bookName = catalog.books.find(b => b.id === location.book)?.name || location.book;
  const s = section(`${title} · ${hits.length} tokens in ${bookName}`), verses = occurrenceVerses(hits);
  s.append(node('p', `${verses.length} verses · select a reference to read its pair.`, 'meta'));
  const list = node('div', null, 'occurrences');
  let shown = 0;
  const more = node('button', 'Show more verses');
  function appendMore() {
    for (const hit of verses.slice(shown,shown+30)) {
      const [book, chapter, verse] = hit.ref.split('.');const bookName=catalog.books.find(b=>b.id===book)?.name || book;const button=node('button',`${bookName} ${chapter}:${verse} `);
      const sample=node('bdi',hit.text);sample.dir='rtl';button.append(sample);
      button.onclick = async () => {
        if (book !== location.book || Number(chapter) !== location.chapter) await navigate({book,chapter:Number(chapter),verse:Number(verse)});
        else {hideStudy();selectVerse(Number(verse));}
        const target=document.querySelector(`[data-word="${hit.ref}/${language}/${hit.word}"]`);
        target?.classList.add('selected');target?.focus({preventScroll:true});
      };
      list.append(button);
    }
    shown+=30;more.hidden=shown>=verses.length;
  }
  more.onclick=appendMore;appendMore();s.append(list,more);return s;
}
function adjacentChapter(direction) {
  const bookIndex = catalog.books.findIndex(book => book.id === location.book);
  const current = catalog.books[bookIndex];
  const chapters = Object.keys(current.chapters).map(Number).sort((a,b) => a-b);
  const index = chapters.indexOf(location.chapter) + direction;
  if (chapters[index] !== undefined) return {book: current.id, chapter: chapters[index], verse: 1};
  const other = catalog.books[bookIndex + direction];
  if (!other) return location;
  const otherChapters = Object.keys(other.chapters).map(Number).sort((a,b) => a-b);
  return {book: other.id, chapter: direction > 0 ? otherChapters[0] : otherChapters.at(-1), verse: 1};
}
$('chapter').onchange=()=>navigate({...location,chapter:Number($('chapter').value),verse:1});
$('reload-update').onclick=()=>{
  const waiting = navigator.serviceWorker.getRegistration().then(registration => registration?.waiting);
  waiting.then(worker=>{
    if (!worker) {window.location.reload();return;}
    navigator.serviceWorker.addEventListener('controllerchange',()=>window.location.reload(),{once:true});
    worker.postMessage({type:'ACTIVATE_UPDATE'});
  });
};
$('verse').onchange=()=>selectVerse(Number($('verse').value));
$('previous').onclick=()=>navigate(adjacentChapter(-1));
for (const id of ['next','next-bottom']) $(id).onclick=()=>navigate(adjacentChapter(1));
$('stack').checked=read('between-lines-stack')==='true';reader.classList.toggle('stacked',$('stack').checked);
$('stack').onchange=()=>{reader.classList.toggle('stacked',$('stack').checked);save('between-lines-stack',$('stack').checked);};
$('accents').checked=read('between-lines-accents')!=='false';
$('accents').onchange=()=>{save('between-lines-accents',$('accents').checked);renderPassage();selectVerse(location.verse,false);hideStudy();};
const savedSize=Number(read('between-lines-size'));if(savedSize>=22&&savedSize<=40)$('size').value=savedSize;
function resize(){document.documentElement.style.setProperty('--word-size',`${$('size').value}px`);save('between-lines-size',$('size').value);}
$('size').oninput=resize;resize();
const navigation = document.querySelector('.toolbar');
new ResizeObserver(() => document.documentElement.style.setProperty('--nav-height', `${navigation.getBoundingClientRect().height}px`)).observe(navigation);
$('close-study').onclick=hideStudy;
document.querySelector('.skip').onclick=e=>{e.preventDefault();reader.focus();reader.scrollIntoView({block:'start'});};
const settingsDialog=$('settings'), infoDialog=$('info');
$('settings-button').onclick=()=>settingsDialog.showModal();$('about').onclick=()=>infoDialog.showModal();
$('close-settings').onclick=()=>settingsDialog.close();$('close-info').onclick=()=>infoDialog.close();
document.addEventListener('keydown',e=>{if(e.key==='Escape')hideStudy();});
window.addEventListener('hashchange',()=>{if(catalog)navigate(parseLocation(window.location.hash,catalog));});
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('install').hidden=false;});
$('install').onclick=async()=>{if(installPrompt){await installPrompt.prompt();installPrompt=null;$('install').hidden=true;}};
window.addEventListener('appinstalled',()=>{$('install').hidden=true;});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)updateReadingSummary();});
async function offline() {
  if (!('serviceWorker' in navigator)) {$('offline-status').textContent='Offline installation unavailable';return;}
  try {
    navigator.serviceWorker.addEventListener('message',e=>{if(e.data?.type==='OFFLINE_READY')$('offline-status').textContent='Reader shell ready · text requires internet';});
    const registration=await navigator.serviceWorker.register('./sw.js',{updateViaCache:'none'});
    const showUpdate = () => {
      if(navigator.serviceWorker.controller){$('offline-status').textContent='Update ready · reload to use it';$('update-notice').hidden=false;}
    };
    const observeWorker = worker => worker?.addEventListener('statechange',()=>{
      if(worker.state==='installed'&&navigator.serviceWorker.controller)showUpdate();
      if(worker.state==='redundant')$('offline-status').textContent='Offline setup failed · reload to retry';
    });
    observeWorker(registration.installing);
    registration.addEventListener('updatefound',()=>observeWorker(registration.installing));
    if(registration.waiting)showUpdate();
    const ready=await navigator.serviceWorker.ready;
    ready.active?.postMessage({type:'STATUS'});
  } catch {$('offline-status').textContent='Online reading · offline setup unavailable';}
}
try {
  catalog=await load('data/catalog.json');bookOptions(catalog.books,catalog.books[0].id);
  const initial=parseLocation(window.location.hash || read('between-lines-location') || '',catalog);
  await navigate(initial,initial.verse > 1);
  offline();
} catch (e) {$('reader-status').textContent=`${e.message}. Reload to retry.`;}
