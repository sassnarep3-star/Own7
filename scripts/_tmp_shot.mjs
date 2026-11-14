import { chromium } from 'playwright-core';
import sparticuz from '@sparticuz/chromium';
import { readFileSync } from 'node:fs'; import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { tmpdir } from 'node:os';
const libs = join(tmpdir(), 'own7-chromium-libs');
mkdirSync(libs, { recursive: true });
const archive = resolve(dirname(fileURLToPath(import.meta.resolve('@sparticuz/chromium'))), '../bin/al2023.tar.br');
execFileSync('tar', ['-xf', '-', '-C', libs], { input: zlib.brotliDecompressSync(readFileSync(archive)) });
const libraryPath = [join(libs, 'lib'), process.env.LD_LIBRARY_PATH].filter(Boolean).join(':');
const browser = await chromium.launch({
  executablePath: await sparticuz.executablePath(), headless: true,
  args: sparticuz.args.filter(a => a !== '--disable-web-security' && a !== '--allow-running-insecure-content'),
  env: { ...process.env, LD_LIBRARY_PATH: libraryPath },
});
const page = await browser.newPage({ viewport: { width: 1280, height: 1050 } });
for (const slug of ['index', 'luck', 'depletion', 'suggestions']) {
  await page.goto(`http://127.0.0.1:8099/nfl-skill-cfdd/site/${slug}.html`, { waitUntil: 'networkidle' });
  await page.screenshot({ path: `/tmp/shot-${slug}.png`, fullPage: false });
}
await browser.close();
console.log('done');
