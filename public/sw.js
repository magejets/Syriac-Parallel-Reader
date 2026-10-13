/* release.js is generated from actual file content; never edit its inventory by hand. */
importScripts('./release.js');
const PREFIX = `between-lines:${self.registration.scope}:`;
const CACHE = PREFIX + self.RELEASE;
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    try {
      // Bounded concurrency for phones. A partial installation is never reported as ready.
      const queue = [...self.PRECACHE];
      await Promise.all(Array.from({length:4}, async () => {
        while (queue.length) {
          const path = queue.shift();
          const url = new URL(path, self.registration.scope);
          const response = await fetch(url, {cache:'reload'});
          if (!response.ok) throw new Error(`Offline asset failed: ${path}`);
          await cache.put(url, response);
        }
      }));
    } catch (e) {await caches.delete(CACHE);throw e;}
    // Wait for existing tabs to close when updating: no mixed old/new data.
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key.startsWith(PREFIX) && key !== CACHE) await caches.delete(key);
    await self.clients.claim();
    for (const client of await self.clients.matchAll()) client.postMessage({type:'OFFLINE_READY'});
  })());
});
self.addEventListener('message', event => {
  if (event.data?.type === 'STATUS') event.source?.postMessage({type:'OFFLINE_READY'});
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || !url.href.startsWith(self.registration.scope)) return;
  const path = url.href.slice(self.registration.scope.length).split('?')[0];
  if (path.startsWith('data/lexicon/') || path === 'data/occurrences.json') {
    event.respondWith(fetch(event.request, {cache:'no-store'}));
    return;
  }
  // No interception of Sefaria or other external providers.
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const key = new URL(event.request.url);key.hash='';key.search='';
    if (key.pathname.endsWith('/')) key.pathname += 'index.html';
    const cached = await cache.match(key.href);
    return cached || fetch(event.request);
  })());
});
