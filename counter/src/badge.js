// The profile-views badge, drawn like the README's link buttons: cream (or dark) tile,
// ink border, hard offset shadow, a terracotta eye tile, and the count in Space Mono.
import { ADVANCE, GLYPHS, SPACE_MONO_700 } from "./font.js";

const THEMES = {
  light: { card: "#FFFDF8", rule: "#1C1917", shadow: "#1C1917", ink: "#1C1917", count: "#B23F1C", hair: "#E4DACB" },
  dark: { card: "#24201D", rule: "#FAF6EE", shadow: "#E05A36", ink: "#FAF6EE", count: "#F2896A", hair: "#3E3732" },
};
const ACCENT = "#E05A36";
const LABEL = "PROFILE VIEWS";
const LABEL_SIZE = 12, LABEL_LS = 0.1;   // em of letter-spacing, as on the cards
const COUNT_SIZE = 16, COUNT_LS = 0.02;

const textWidth = (s, size, ls) => s.length * (ADVANCE + ls) * size;

export function formatCount(n) {
  const s = Math.max(0, Math.floor(n)).toLocaleString("en-US");
  // only characters the embedded font has; anything else would fall back to another font
  return [...s].every((c) => GLYPHS.includes(c)) ? s : String(Math.floor(n));
}

export function renderBadge(n, themeName = "light") {
  const t = THEMES[themeName] || THEMES.light;
  const count = formatCount(n);
  const labelX = 46;
  const labelW = textWidth(LABEL, LABEL_SIZE, LABEL_LS);
  const divX = labelX + labelW + 10;
  const countX = divX + 14;
  const w = Math.ceil(countX + textWidth(count, COUNT_SIZE, COUNT_LS) + 18 + 6);
  const h = 48;
  const title = `${count} profile views`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img" aria-label="${title}">
<title>${title}</title>
<style>@font-face{font-family:M7;font-weight:700;src:url(data:font/woff2;base64,${SPACE_MONO_700}) format('woff2')}
text{font-family:M7,'Space Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-weight:700}
.n{animation:rise .7s cubic-bezier(.22,1,.36,1) .15s both}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>
<rect x="6" y="6" width="${w - 6}" height="40" rx="12" fill="${t.shadow}"/>
<rect x="2" y="2" width="${w - 6}" height="40" rx="12" fill="${t.card}" stroke="${t.rule}" stroke-width="2"/>
<rect x="9" y="9" width="26" height="26" rx="7" fill="${ACCENT}" stroke="${t.rule}" stroke-width="1.5"/>
<path d="M13.5 22 Q22 13.5 30.5 22 Q22 30.5 13.5 22Z" fill="none" stroke="#FFFFFF" stroke-width="1.7" stroke-linejoin="round"/>
<circle cx="22" cy="22" r="2.6" fill="#FFFFFF"/>
<text x="${labelX}" y="26.5" font-size="${LABEL_SIZE}" letter-spacing="${(LABEL_LS * LABEL_SIZE).toFixed(2)}" fill="${t.ink}">${LABEL}</text>
<line x1="${divX.toFixed(1)}" y1="12" x2="${divX.toFixed(1)}" y2="32" stroke="${t.hair}" stroke-width="2"/>
<text class="n" x="${countX.toFixed(1)}" y="27.5" font-size="${COUNT_SIZE}" letter-spacing="${(COUNT_LS * COUNT_SIZE).toFixed(2)}" fill="${t.count}">${count}</text>
</svg>`;
}
