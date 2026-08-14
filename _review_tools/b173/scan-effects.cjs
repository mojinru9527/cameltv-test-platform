// Scan page files for useEffect blocks with async ops but without cleanup
const fs = require('fs');
const files = process.argv.slice(2);
const issues = [];
let totalEffects = 0, asyncEffects = 0, noCleanup = 0;
for (const f of files) {
  const text = fs.readFileSync(f, 'utf8');
  const re = /useEffect\s*\(/g;
  let m;
  while ((m = re.exec(text)) !== null) {
    totalEffects++;
    const startIdx = m.index;
    let depth = 1, endIdx = -1;
    for (let i = startIdx + m[0].length; i < text.length; i++) {
      const c = text[i];
      if (c === '(') depth++;
      else if (c === ')') { depth--; if (depth === 0) { endIdx = i; break; } }
    }
    if (endIdx === -1) continue;
    const block = text.slice(startIdx, endIdx + 1);
    const hasAsync = /\.then\(|await\s|\bfetch\w*\(|setTimeout\(|setInterval\(|new Promise/.test(block);
    if (!hasAsync) continue;
    asyncEffects++;
    const hasCleanup = /return\s*\(\)\s*=>/.test(block) || /cancelled\s*=\s*true/.test(block) ||
      /\.abort\(\)/.test(block) || /clearInterval\(/.test(block) || /clearTimeout\(/.test(block) ||
      /signal\.aborted/.test(block) || /controller\.abort/.test(block);
    if (!hasCleanup) {
      noCleanup++;
      const rel = f.replace(/\\/g, '/').split('/src/pages/')[1] || f;
      const startLine = text.slice(0, startIdx).split('\n').length;
      const endLine = text.slice(0, endIdx).split('\n').length;
      const snippet = block.slice(0, 220).replace(/\s+/g, ' ');
      issues.push(`${rel}:${startLine}-${endLine} :: ${snippet}`);
    }
  }
}
console.log(`TOTAL effects=${totalEffects} async=${asyncEffects} noCleanup=${noCleanup}`);
console.log('---');
console.log(issues.join('\n'));
