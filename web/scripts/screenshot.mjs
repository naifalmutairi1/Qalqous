// screenshot.mjs: viewport screenshots of the running dev server, at an exact width.
// No packages: it starts Chrome and talks to it through the DevTools Protocol (Node's built-in WebSocket).
// Why not `chrome --screenshot`? Headless Chrome will not make a window narrower than ~500px,
// so a "375px" shot comes out cropped. Here we set the viewport size directly, like DevTools' phone mode.
//
// Usage (from web/, with `npm run dev` running):
//   node scripts/screenshot.mjs <url> <width> <out.png> [click text ...]
// Each "click text" clicks the first button whose visible text contains it, in order,
// so interactive states (e.g. "are you sure?") come from real clicks, not fake URL flags.
// "scroll:<text>" scrolls to a heading or button instead of clicking it.
// Example:
//   node scripts/screenshot.mjs "http://localhost:5173/#/report/inc-0014" 375 ../design/shots/report-375.png "إبقاءه موقوف"
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9333;
const [url, widthArg, out, ...clicks] = process.argv.slice(2);
if (!url || !widthArg || !out) {
  console.error('usage: node scripts/screenshot.mjs <url> <width> <out.png> [click text ...]');
  process.exit(1);
}
const width = Number(widthArg);
const height = width < 600 ? 812 : 900;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// A throwaway Chrome profile, so this never touches the user's own browser profile.
const profile = mkdtempSync(join(tmpdir(), 'qalqous-shot-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`, 'about:blank',
]);

try {
  // Wait until Chrome answers, then find the open tab.
  let target;
  for (let i = 0; i < 40 && !target; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      target = list.find((t) => t.type === 'page');
    } catch { await wait(250); }
  }
  if (!target) throw new Error('Chrome did not start');

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r, { once: true }));
  let nextId = 0;
  const pending = new Map();
  ws.addEventListener('message', (e) => {
    const msg = JSON.parse(e.data);
    if (pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, (msg) => (msg.error ? reject(new Error(msg.error.message)) : resolve(msg.result)));
    ws.send(JSON.stringify({ id, method, params }));
  });

  await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: width < 600 });
  await send('Page.enable');
  await send('Page.navigate', { url });
  await wait(2500); // page load + web fonts
  await send('Runtime.evaluate', { expression: 'document.fonts.ready', awaitPromise: true });

  for (const text of clicks) {
    // "scroll:<text>": scroll the first heading/button with that text to the top of the viewport.
    if (text.startsWith('scroll:')) {
      const target = text.slice('scroll:'.length);
      await send('Runtime.evaluate', {
        expression: `(() => {
          // Headings first, so "قرارك" finds the section title, not a sentence that contains the word.
          const all = [...document.querySelectorAll('h1, h2, h3'), ...document.querySelectorAll('button, a, p')];
          const el = all.find((b) => b.textContent.includes(${JSON.stringify(target)}));
          if (el) { el.scrollIntoView({ block: 'start' }); window.scrollBy(0, -24); }
        })()`,
      });
      await wait(300);
      continue;
    }
    const { result } = await send('Runtime.evaluate', {
      expression: `(() => {
        const el = [...document.querySelectorAll('button, a')].find((b) => b.textContent.includes(${JSON.stringify(text)}));
        if (!el) return false;
        el.click();
        return true;
      })()`,
      returnByValue: true,
    });
    if (!result.value) throw new Error(`no button with text: ${text}`);
    await wait(400);
  }
  // Viewport shot from the top of the page, unless a click scrolled on purpose.
  const { data } = await send('Page.captureScreenshot', { format: 'png' });
  writeFileSync(out, Buffer.from(data, 'base64'));
  console.log(`saved ${out} (${width}x${height})`);
  ws.close();
} finally {
  chrome.kill();
  await wait(500);
  try { rmSync(profile, { recursive: true, force: true }); } catch { /* Chrome may still hold a file */ }
}
