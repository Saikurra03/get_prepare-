/* Tiny SVG chart helpers for the report dashboard (Phase 5).
   Dependency-free, additive. Callers pass REAL numbers from the report —
   these helpers never fabricate or interpolate data. Colors use the app's
   existing CSS tokens. */
const Charts = {
  _esc: (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])),

  /* Horizontal bars: items = [{label, value, color?, hint?}]. One shared scale. */
  bars(items, opts = {}) {
    if (!items || !items.length) return "";
    const rowH = 24, gap = 8, labelW = opts.labelW || 96, W = 340;
    const H = items.length * (rowH + gap) + 4;
    const max = Math.max(1, ...items.map((i) => i.value || 0));
    const barMax = W - labelW - 44;
    const rows = items.map((it, i) => {
      const y = i * (rowH + gap) + 2;
      const w = Math.round((Math.max(0, it.value || 0) / max) * barMax);
      const color = it.color || "var(--acc)";
      return `<text x="${labelW - 6}" y="${y + 15}" text-anchor="end" font-size="11" fill="var(--mut)">${Charts._esc(it.label)}</text>
<rect x="${labelW}" y="${y + 4}" width="${barMax}" height="12" rx="6" fill="var(--line-soft)"/>
<rect x="${labelW}" y="${y + 4}" width="${Math.max(w, 2)}" height="12" rx="6" fill="${color}"/>
<text x="${labelW + barMax + 6}" y="${y + 15}" font-size="11" fill="var(--ink)">${Charts._esc(it.value)}</text>`;
    }).join("");
    return `<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img">${rows}</svg>`;
  },

  /* Trend line: points = [{label, value}] on a 0..max scale (default 10). */
  line(points, opts = {}) {
    if (!points || points.length < 2) return "";
    const max = opts.max || 10;
    const W = 340, H = 150, padL = 26, padR = 10, padT = 12, padB = 26;
    const iw = W - padL - padR, ih = H - padT - padB;
    const x = (i) => padL + (points.length === 1 ? iw / 2 : (i / (points.length - 1)) * iw);
    const y = (v) => padT + ih - (Math.min(Math.max(v, 0), max) / max) * ih;
    const gridLines = [0, max / 2, max].map((g) =>
      `<line x1="${padL}" y1="${y(g)}" x2="${W - padR}" y2="${y(g)}" stroke="var(--line-soft)" stroke-width="1"/>
       <text x="4" y="${y(g) + 4}" font-size="10" fill="var(--dim)">${g}</text>`).join("");
    const path = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
    const area = `${path} L${x(points.length - 1).toFixed(1)},${padT + ih} L${padL},${padT + ih} Z`;
    const dots = points.map((p, i) =>
      `<circle cx="${x(i).toFixed(1)}" cy="${y(p.value).toFixed(1)}" r="3.5" fill="var(--acc)"/>
       <text x="${x(i).toFixed(1)}" y="${H - 8}" text-anchor="middle" font-size="10" fill="var(--dim)">${Charts._esc(p.label)}</text>`).join("");
    return `<svg class="chart-svg" viewBox="0 0 ${W} ${H}" role="img">
${gridLines}
<path d="${area}" fill="rgba(91,140,255,.14)"/>
<path d="${path}" fill="none" stroke="var(--acc)" stroke-width="2" stroke-linejoin="round"/>
${dots}</svg>`;
  },

  /* Donut of segments (same unit): [{label, value, color}] + center total. */
  donut(segments, opts = {}) {
    const total = (segments || []).reduce((a, s) => a + (s.value || 0), 0);
    if (!total) return "";
    const R = 54, C = 2 * Math.PI * R;
    let off = 0;
    const rings = segments.filter((s) => s.value > 0).map((s) => {
      const frac = s.value / total;
      const dash = `${(frac * C).toFixed(2)} ${C.toFixed(2)}`;
      const seg = `<circle cx="80" cy="80" r="${R}" fill="none" stroke="${s.color || "var(--acc)"}"
        stroke-width="16" stroke-dasharray="${dash}" stroke-dashoffset="${(-off * C).toFixed(2)}"
        transform="rotate(-90 80 80)"/>`;
      off += frac;
      return seg;
    }).join("");
    const legend = segments.map((s) =>
      `<span><span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${s.color || "var(--acc)"};margin-right:5px"></span>${Charts._esc(s.label)} <b>${s.value}</b></span>`).join("");
    return `<svg class="chart-svg" viewBox="0 0 160 160" style="max-width:170px;margin:0 auto" role="img">
${rings}
<text x="80" y="76" text-anchor="middle" font-size="26" font-weight="700" fill="var(--ink)">${total}</text>
<text x="80" y="96" text-anchor="middle" font-size="10" fill="var(--dim)">${Charts._esc(opts.centerLabel || "total")}</text>
</svg><div class="chart-legend" style="justify-content:center">${legend}</div>`;
  },
};
