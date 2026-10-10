const $ = (s) => document.querySelector(s);

function esc(t) {
  const d = document.createElement("div");
  d.textContent = t == null ? "" : t;
  return d.innerHTML;
}

async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    throw new Error(
      Array.isArray(d)
        ? d.map((x) => x.msg).join("; ")
        : d || "Something went wrong",
    );
  }
  return data;
}

function msg(text, type) {
  const m = $("#msg");
  m.textContent = text || "";
  m.className = "msg " + (type || "err");
  m.hidden = !text;
}

// Wrap an async handler so errors show in the message box instead of failing silently.
const guard =
  (fn) =>
  async (...args) => {
    msg("");
    try {
      await fn(...args);
    } catch (e) {
      msg(e.message);
    }
  };

function fillSelect(sel, items, placeholder, label = (i) => i.name) {
  sel.replaceChildren(
    new Option(items.length ? placeholder : "No options available", ""),
    ...items.map((i) => new Option(label(i), i.id)),
  );
  sel.disabled = items.length === 0;
}
const resetSelect = (sel, placeholder) => {
  fillSelect(sel, [], placeholder);
  sel.options[0].text = placeholder;
};

function resultsTable(rows, nameKey, valueKey) {
  rows = [...rows].sort((a, b) => b[valueKey] - a[valueKey]);
  const total = rows.reduce((s, r) => s + Number(r[valueKey]), 0);
  const max = Math.max(...rows.map((r) => Number(r[valueKey])), 1);
  const body = rows
    .map(
      (r) =>
        `<tr><td>${esc(r[nameKey])}</td><td class="num">${Number(r[valueKey]).toLocaleString()}</td>` +
        `<td class="barcell"><div class="bar" style="width:${((Number(r[valueKey]) / max) * 100).toFixed(1)}%"></div></td></tr>`,
    )
    .join("");
  return (
    `<table><thead><tr><th>Party</th><th class="num">Votes</th><th></th></tr></thead><tbody>${body}</tbody>` +
    `<tfoot><tr><th>Total</th><th class="num">${total.toLocaleString()}</th><th></th></tr></tfoot></table>`
  );
}

const links = [
  ["/", "Polling unit"],
  ["/lga", "LGA total"],
  ["/new", "Add result"],
];
document.body.insertAdjacentHTML(
  "afterbegin",
  "<nav><b>Delta 2011 Results</b>" +
    links
      .map(
        ([h, t]) =>
          `<a href="${h}"${location.pathname === h ? ' class="on"' : ""}>${t}</a>`,
      )
      .join("") +
    "</nav>",
);
