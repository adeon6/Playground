const STORAGE_KEY = "d2r-reimagined-rune-counts";
const PINNED_STORAGE_KEY = "d2r-reimagined-pinned-runewords";
const app = document.querySelector("#app");

const runeOrder = [
  "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort", "Thul",
  "Amn", "Sol", "Shael", "Dol", "Hel", "Io", "Lum", "Ko", "Fal", "Lem",
  "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo", "Sur", "Ber",
  "Jah", "Cham", "Zod"
];

const state = {
  search: "",
  hideVanilla: false,
  showOnlyCraftable: true,
  showPinnedOnly: false,
  sortBy: "level",
  sortDirection: "asc"
};

let runewords = [];
let runeCounts = loadStorage(STORAGE_KEY);
let pinnedRunewords = loadStorage(PINNED_STORAGE_KEY);
let lastFocus = null;

function loadStorage(key) {
  try {
    return JSON.parse(localStorage.getItem(key) ?? "{}");
  } catch {
    return {};
  }
}

function saveStorage(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function normalizeRuneName(name) {
  return name.replace(/\s+Rune$/i, "").trim();
}

function formatTypes(types) {
  return types.map((type) => type.Name).join(", ");
}

function countNeededRunes(runes) {
  return runes.reduce((accumulator, rune) => {
    const name = normalizeRuneName(rune.Name);
    accumulator[name] = (accumulator[name] ?? 0) + 1;
    return accumulator;
  }, {});
}

function craftableCount(requiredRunes) {
  let maxCrafts = Infinity;
  for (const [rune, required] of Object.entries(requiredRunes)) {
    maxCrafts = Math.min(maxCrafts, Math.floor(Number(runeCounts[rune] ?? 0) / required));
  }
  return Number.isFinite(maxCrafts) ? maxCrafts : 0;
}

function missingRunes(requiredRunes) {
  return Object.entries(requiredRunes)
    .map(([rune, required]) => {
      const available = Number(runeCounts[rune] ?? 0);
      return available >= required ? null : { rune, available, required };
    })
    .filter(Boolean);
}

function compareValues(left, right) {
  if (typeof left === "number" && typeof right === "number") {
    return left - right;
  }
  return String(left).localeCompare(String(right));
}

function getSortValue(runeword, key) {
  if (key === "name") return runeword.Name;
  if (key === "types") return formatTypes(runeword.Types);
  if (key === "crafts") return runeword.crafts;
  if (key.startsWith("rune")) return runeword.runeSequence[Number(key.replace("rune", ""))] ?? "";
  return runeword.RequiredLevel;
}

function enrichRuneword(runeword) {
  const requiredRunes = countNeededRunes(runeword.Runes);
  return {
    ...runeword,
    requiredRunes,
    crafts: craftableCount(requiredRunes),
    missing: missingRunes(requiredRunes),
    runeSequence: runeword.Runes.map((rune) => normalizeRuneName(rune.Name)),
    isPinned: Boolean(pinnedRunewords[runeword.Code])
  };
}

function getFilteredRunewords() {
  const search = state.search.trim().toLowerCase();

  return runewords
    .map(enrichRuneword)
    .filter((runeword) => !state.hideVanilla || runeword.Vanilla !== "Y")
    .filter((runeword) => !state.showOnlyCraftable || runeword.crafts > 0)
    .filter((runeword) => !state.showPinnedOnly || runeword.isPinned)
    .filter((runeword) => {
      if (!search) return true;
      const haystack = [
        runeword.Name,
        formatTypes(runeword.Types),
        runeword.runeSequence.join(" "),
        ...runeword.Properties.map((property) => property.PropertyString)
      ].join(" ").toLowerCase();
      return haystack.includes(search);
    })
    .sort((left, right) => {
      if (left.isPinned !== right.isPinned) return left.isPinned ? -1 : 1;
      const comparison = compareValues(getSortValue(left, state.sortBy), getSortValue(right, state.sortBy));
      if (comparison !== 0) return state.sortDirection === "asc" ? comparison : -comparison;
      return left.Name.localeCompare(right.Name);
    });
}

function highlightProperty(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/(\+|-)?\d+([.-]\d+)?%?/g, '<span class="stat-value">$&</span>')
    .replace(/\(([^)]+)\)/g, '<span class="stat-note">($1)</span>');
}

function renderSortHeader(label, key) {
  const active = state.sortBy === key;
  const arrow = active ? (state.sortDirection === "asc" ? "&#9650;" : "&#9660;") : "";
  return `<button class="header-button" type="button" data-sort="${key}">${label} ${arrow}</button>`;
}

function renderRuneGrid() {
  return runeOrder.map((rune) => `
    <label class="rune-card ${Number(runeCounts[rune] ?? 0) > 0 ? "has-stock" : ""}" for="rune-${rune}">
      <span class="rune-icon">${rune.slice(0, 1)}</span>
      <div class="rune-meta">
        <span class="rune-name">${rune}</span>
        <input id="rune-${rune}" class="rune-input" type="number" min="0" step="1" value="${Number(runeCounts[rune] ?? 0)}" data-rune="${rune}" />
      </div>
    </label>
  `).join("");
}

function renderRows(items) {
  if (items.length === 0) {
    return `<tr><td class="empty-table" colspan="12">No runewords match your current filters.</td></tr>`;
  }

  return items.map((runeword) => {
    const runes = Array.from({ length: 6 }, (_, index) => {
      const rune = runeword.runeSequence[index] ?? "";
      const owned = rune && Number(runeCounts[rune] ?? 0) > 0;
      return `<td class="rune-col ${owned ? "is-owned" : ""}">${rune}</td>`;
    }).join("");

    const status = runeword.missing.length === 0
      ? '<span class="status-inline is-ready">Ready now</span>'
      : runeword.missing.map((entry) => `<span class="missing-chip">${entry.rune} <strong>${entry.available}/${entry.required}</strong></span>`).join("");

    const props = runeword.Properties.map((property) => `<div class="affix-line">${highlightProperty(property.PropertyString)}</div>`).join("");

    return `
      <tr class="runeword-row ${runeword.crafts > 0 ? "is-complete" : ""}">
        <td class="pin-col"><button class="pin-button ${runeword.isPinned ? "is-pinned" : ""}" type="button" data-pin="${runeword.Code}">${runeword.isPinned ? "&#9733;" : "&#9734;"}</button></td>
        <td class="name-col">
          <div class="name-stack">
            <span class="runeword-name">${runeword.Name}</span>
            <span class="runeword-badges">
              <span class="badge ${runeword.Vanilla === "Y" ? "badge-vanilla" : "badge-mod"}">${runeword.Vanilla === "Y" ? "Vanilla" : "Reimagined"}</span>
            </span>
          </div>
        </td>
        ${runes}
        <td class="type-col">
          <div>${formatTypes(runeword.Types)}</div>
          <div class="type-status">${status}</div>
        </td>
        <td class="level-col">${runeword.RequiredLevel > 0 ? runeword.RequiredLevel : 1}</td>
        <td class="crafts-col ${runeword.crafts > 0 ? "is-ready" : "is-missing"}">${runeword.crafts > 0 ? `${runeword.crafts}x` : runeword.missing.length}</td>
        <td class="props-col"><div class="affix-list">${props}</div></td>
      </tr>
    `;
  }).join("");
}

function render() {
  const filtered = getFilteredRunewords();
  const craftableNow = filtered.filter((runeword) => runeword.crafts > 0).length;
  const pinnedVisible = filtered.filter((runeword) => runeword.isPinned).length;

  app.innerHTML = `
    <main class="layout">
      <section class="panel hero">
        <div>
          <span class="eyebrow">Diablo II Resurrected</span>
          <h1>D2R Reimagined Runeword Helper</h1>
          <p class="hero-copy">Track the runes you own, then scan the full D2R Reimagined runeword list with a wider, readable properties column.</p>
        </div>
        <div class="summary-grid">
          <div class="summary-card"><span class="summary-label">Runewords loaded</span><strong>${runewords.length}</strong></div>
          <div class="summary-card good"><span class="summary-label">Craftable now</span><strong>${craftableNow}</strong></div>
          <div class="summary-card"><span class="summary-label">Pinned visible</span><strong>${pinnedVisible}</strong></div>
        </div>
      </section>

      <section class="panel runes-panel">
        <div class="panel-header">
          <h2>Your runes</h2>
          <button id="reset-runes" class="ghost-button" type="button">Reset counts</button>
        </div>
        <div class="rune-grid">${renderRuneGrid()}</div>
      </section>

      <section class="panel filters-panel">
        <div class="filter-toolbar">
          <div class="field">
            <label for="search">Search</label>
            <input id="search" class="search-input" type="search" value="${state.search}" placeholder="Search name, rune, type, or stat" />
          </div>
          <label class="toggle"><input id="show-craftable" type="checkbox" ${state.showOnlyCraftable ? "checked" : ""} /> <span>Only craftable</span></label>
          <label class="toggle"><input id="hide-vanilla" type="checkbox" ${state.hideVanilla ? "checked" : ""} /> <span>Hide vanilla</span></label>
          <label class="toggle"><input id="show-pinned" type="checkbox" ${state.showPinnedOnly ? "checked" : ""} /> <span>Pinned only</span></label>
        </div>
      </section>

      <section class="panel table-panel">
        <div class="table-shell">
          <table class="runeword-table">
            <thead>
              <tr>
                <th class="pin-col"></th>
                <th class="name-col">${renderSortHeader("Runeword", "name")}</th>
                <th>${renderSortHeader("R1", "rune0")}</th>
                <th>${renderSortHeader("R2", "rune1")}</th>
                <th>${renderSortHeader("R3", "rune2")}</th>
                <th>${renderSortHeader("R4", "rune3")}</th>
                <th>${renderSortHeader("R5", "rune4")}</th>
                <th>${renderSortHeader("R6", "rune5")}</th>
                <th class="type-col">${renderSortHeader("Item Type", "types")}</th>
                <th class="level-col">${renderSortHeader("Lvl", "level")}</th>
                <th class="crafts-col">${renderSortHeader("Can Make", "crafts")}</th>
                <th class="props-col">Properties</th>
              </tr>
            </thead>
            <tbody>${renderRows(filtered)}</tbody>
          </table>
        </div>
      </section>
    </main>
  `;

  bindEvents();
  restoreFocus();
}

function captureFocus() {
  const active = document.activeElement;
  if (!active || !active.id) {
    lastFocus = null;
    return;
  }
  lastFocus = {
    id: active.id,
    selectionStart: typeof active.selectionStart === "number" ? active.selectionStart : null,
    selectionEnd: typeof active.selectionEnd === "number" ? active.selectionEnd : null
  };
}

function restoreFocus() {
  if (!lastFocus) return;
  const element = document.getElementById(lastFocus.id);
  if (!element) return;
  element.focus();
  if (lastFocus.selectionStart !== null && lastFocus.selectionEnd !== null) {
    element.setSelectionRange(lastFocus.selectionStart, lastFocus.selectionEnd);
  }
}

function toggleSort(sortBy) {
  if (state.sortBy === sortBy) {
    state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
    return;
  }
  state.sortBy = sortBy;
  state.sortDirection = sortBy === "crafts" ? "desc" : "asc";
}

function bindEvents() {
  app.querySelectorAll("[data-rune]").forEach((input) => {
    input.addEventListener("input", (event) => {
      captureFocus();
      runeCounts[event.currentTarget.dataset.rune] = Math.max(0, Number(event.currentTarget.value || 0));
      saveStorage(STORAGE_KEY, runeCounts);
      render();
    });
  });

  app.querySelector("#search").addEventListener("input", (event) => {
    captureFocus();
    state.search = event.currentTarget.value;
    render();
  });

  app.querySelector("#show-craftable").addEventListener("change", (event) => {
    captureFocus();
    state.showOnlyCraftable = event.currentTarget.checked;
    render();
  });

  app.querySelector("#hide-vanilla").addEventListener("change", (event) => {
    captureFocus();
    state.hideVanilla = event.currentTarget.checked;
    render();
  });

  app.querySelector("#show-pinned").addEventListener("change", (event) => {
    captureFocus();
    state.showPinnedOnly = event.currentTarget.checked;
    render();
  });

  app.querySelector("#reset-runes").addEventListener("click", () => {
    runeCounts = {};
    saveStorage(STORAGE_KEY, runeCounts);
    render();
  });

  app.querySelectorAll("[data-sort]").forEach((button) => {
    button.addEventListener("click", (event) => {
      toggleSort(event.currentTarget.dataset.sort);
      render();
    });
  });

  app.querySelectorAll("[data-pin]").forEach((button) => {
    button.addEventListener("click", (event) => {
      const code = event.currentTarget.dataset.pin;
      pinnedRunewords[code] = !pinnedRunewords[code];
      if (!pinnedRunewords[code]) delete pinnedRunewords[code];
      saveStorage(PINNED_STORAGE_KEY, pinnedRunewords);
      render();
    });
  });
}

if (!Array.isArray(window.RUNewordsData)) {
  app.innerHTML = '<main class="layout"><section class="panel hero"><h1>Could not load runeword data</h1></section></main>';
} else {
  runewords = window.RUNewordsData;
  render();
}
