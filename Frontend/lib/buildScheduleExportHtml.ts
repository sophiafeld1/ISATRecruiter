/**
 * Build a single-page landscape HTML document from rendered schedule markup.
 * Groups each #### year heading + following <table> into a grid cell.
 */

function rearrangeScheduleNodes(importRoot: HTMLElement, doc: Document): string {
  const prelude = doc.createElement("div");
  prelude.className = "schedule-prelude";

  const grid = doc.createElement("div");
  grid.className = "schedule-grid";

  const footer = doc.createElement("div");
  footer.className = "schedule-footer";

  const children = Array.from(importRoot.children);
  let i = 0;

  while (i < children.length) {
    const el = children[i];
    const next = children[i + 1];
    if (
      el.tagName.toLowerCase() === "h4" &&
      next &&
      next.tagName.toLowerCase() === "table"
    ) {
      break;
    }
    prelude.appendChild(el.cloneNode(true));
    i++;
  }

  while (i < children.length) {
    const el = children[i];
    const next = children[i + 1];
    if (
      el.tagName.toLowerCase() === "h4" &&
      next &&
      next.tagName.toLowerCase() === "table"
    ) {
      const block = doc.createElement("div");
      block.className = "year-block";
      block.appendChild(el.cloneNode(true));
      block.appendChild(next.cloneNode(true));
      grid.appendChild(block);
      i += 2;
      continue;
    }
    footer.appendChild(el.cloneNode(true));
    i++;
  }

  const wrap = doc.createElement("div");
  wrap.className = "schedule-export-wrap";
  if (prelude.childNodes.length) wrap.appendChild(prelude);
  if (grid.childNodes.length) wrap.appendChild(grid);
  if (footer.childNodes.length) wrap.appendChild(footer);
  return wrap.outerHTML;
}

export function buildScheduleExportHtml(innerHtml: string): string {
  const parser = new DOMParser();
  const parsed = parser.parseFromString(
    `<div class="import-root">${innerHtml}</div>`,
    "text/html",
  );
  const importRoot = parsed.querySelector(".import-root");
  if (!importRoot) {
    return `<!doctype html><html><head><meta charset="utf-8"/><title>ISAT Schedule</title></head><body><div class="schedule-export-wrap">${innerHtml}</div></body></html>`;
  }

  const rearranged = rearrangeScheduleNodes(importRoot as HTMLElement, parsed);

  const styles = `
:root { color-scheme: light; }
* { box-sizing: border-box; }
@page {
  size: A4 landscape;
  margin: 4mm 6mm;
}
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
}
body {
  font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
  font-size: 8pt;
  line-height: 1.25;
  color: #1a1a1a;
  padding: 4mm 6mm;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.schedule-export-wrap {
  max-width: 100%;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.schedule-prelude p {
  margin: 0 0 3px 0;
  font-size: 8.5pt;
}
.schedule-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 5px 10px;
  align-items: start;
}
.year-block {
  break-inside: avoid;
  page-break-inside: avoid;
}
.year-block h4 {
  margin: 0 0 2px 0;
  font-size: 9pt;
  font-weight: 700;
  color: #2d0d4e;
  letter-spacing: 0.01em;
}
.year-block table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
  font-size: 6.5pt;
  margin: 0;
}
.year-block th,
.year-block td {
  border: 1px solid #b8a8c8;
  padding: 2px 4px;
  text-align: left;
  vertical-align: top;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
.year-block th {
  background: #ede4f4;
  font-weight: 600;
}
.year-block tr:nth-child(even) td {
  background: #faf8fc;
}
.schedule-footer {
  margin-top: 4px;
  padding-top: 4px;
  border-top: 1px solid #cfc3dc;
  font-size: 7.5pt;
}
.schedule-footer h3 {
  margin: 3px 0 2px 0;
  font-size: 8.5pt;
}
.schedule-footer p, .schedule-footer li {
  margin: 1px 0;
}
.schedule-footer ul {
  margin: 2px 0 2px 1.1em;
  padding: 0;
}
@media print {
  body { padding: 0; }
  .schedule-export-wrap { gap: 3px; }
  .schedule-grid { gap: 3px 6px; }
  .year-block table { font-size: 6pt; }
  .year-block th, .year-block td { padding: 1px 3px; }
}
`;

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>ISAT Schedule</title>
  <style>${styles}</style>
</head>
<body>
${rearranged}
</body>
</html>`;
}
