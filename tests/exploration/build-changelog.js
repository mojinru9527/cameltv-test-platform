// 解析更新日志 v2：基于顺序模式（版本号、日期、内容、页面名交替）
const fs = require('fs');

const raw = fs.readFileSync('F:/CamelTv/tests/exploration/lanhu-assets/更新日志.txt', 'utf8');
const lines = raw.split('\n').map(l => l.trim()).filter(Boolean);

const verRe = /^\d+\.\d+\.\d+$/;
const dateRe = /^\d{4}-\d{2}-\d{2}$/;

// 观察到的模式：版本号 → 更新时间 → 操作人员(-) → 审核人员(-) → 审核时间 → 更新内容行 → 关联页面
// 更新内容行以 1、2、3 或"新增/调整"开头，或为"创建"
// 关联页面是短中文词（页面名，如"聊天"、"首页"）

const records = [];
let cur = null;

for (const line of lines) {
  if (verRe.test(line)) {
    cur = { version: line, updateTime: '', auditTime: '', content: [], pages: [] };
    records.push(cur);
    continue;
  }
  if (!cur) continue;
  if (dateRe.test(line)) {
    if (!cur.updateTime) cur.updateTime = line;
    else if (!cur.auditTime) cur.auditTime = line;
    continue;
  }
  if (line === '-') continue;
  if (line === '创建' || /^[1-9０-９][、.．]/.test(line) || /^[1-9][)）]/.test(line)) {
    cur.content.push(line);
    continue;
  }
  // 其它短行视为关联页面（排除日期、版本号等）
  if (line.length <= 24) {
    cur.pages.push(line);
  }
}

const out = records.map(r => ({
  version: r.version,
  updateTime: r.updateTime,
  auditTime: r.auditTime,
  content: r.content,
  pages: [...new Set(r.pages)],
}));

fs.writeFileSync('F:/CamelTv/tests/exploration/lanhu-assets/changelog-structured.json', JSON.stringify(out, null, 2), 'utf8');
console.log('RECORDS:', out.length);
// 只打印有内容的
for (const r of out) {
  if (r.content.length) {
    console.log(`\n=== ${r.version} (${r.updateTime}) ===`);
    r.content.forEach(c => console.log('  ' + c));
    if (r.pages.length) console.log('  页面: ' + r.pages.join(', '));
  }
}
