// Optional regression suite. Start the local server before running.
import {chromium} from '@playwright/test';
import assert from 'node:assert/strict';
const url=process.env.READER_URL || 'http://127.0.0.1:4173/';
const browser=await chromium.launch();
try {
  const context=await browser.newContext({viewport:{width:390,height:844},serviceWorkers:'allow'});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);
  await page.waitForFunction(()=>document.querySelectorAll('.verse-row').length===31);
  await page.waitForFunction(()=>document.querySelector('#offline-status').textContent==='Genesis available offline',{},{timeout:60000});
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.locator('[data-word="Gen.1.1/he/1"]').click();
  await page.locator('#study-content .gloss').waitFor();
  assert.match(await page.locator('#study-content').innerText(),/Same lemma/);
  await page.getByText('Read bundled BDB entry',{exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.bdb-body')?.textContent!=='Loading…');
  assert.match(await page.locator('.bdb-body').innerText(),/create|shape/);
  await page.locator('#close-study').click();
  await page.locator('#stack').check();
  assert.equal(await page.locator('#reader').getAttribute('class'),'stacked');
  await context.setOffline(true);
  await page.locator('#chapter').selectOption('50');
  await page.waitForFunction(()=>document.querySelector('#passage-title').textContent==='Genesis 50');
  assert.equal(await page.locator('.verse-row').count(),26);
  await page.locator('#verse').selectOption('26');
  assert.ok(page.url().endsWith('#Gen.50.26'));
  await page.reload();
  await page.locator('[data-word="Gen.50.26/syr/0"]').click();
  await page.locator('#study-content .transliteration').waitFor();
  await page.getByText('Lexical resources need an internet connection.',{exact:false}).waitFor();
  assert.match(await page.locator('#study-content').innerText(),/Consonant transliteration/);
  assert.deepEqual(errors,[]);
  await browser.close();console.log('Mobile navigation, lexical study and offline smoke checks passed.');
} finally {if(browser.isConnected())await browser.close();}
