import { grimarillionData } from "../data/grimarillion-rr.js";

const app = document.querySelector("#app");
const ELEMENTAL_TYPES = new Set(["Fire", "Lightning", "Cold"]);
const DAMAGE_TYPES = grimarillionData.damageTypes;
const CLASS_NAMES = grimarillionData.masteries.map((mastery) => mastery.name).sort((left, right) => left.localeCompare(right));

let lastFocus = null;

if (!grimarillionData) {
  app.innerHTML = `
    <main class="layout">
      <section class="panel">
        <div class="empty-table">RR data is missing. Regenerate <code>data/grimarillion-rr.js</code> first.</div>
      </section>
    </main>
  `;
  throw new Error("Missing grimarillion RR dataset");
}

const state = {
  damageType: "",
  filterMetric: "stackedTotal",
  comparator: "gte",
  threshold: 60,
  baseResistance: 80,
  search: "",
  focusClass: "",
  hideConditional: false
};

function formatNumber(value) {
  const rounded = Math.round(value * 100) / 100;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(2).replace(/\.?0+$/, "");
}

function getApplicableTypes(damageType) {
  if (damageType === "Elemental") {
    return ["All", "Elemental"];
  }

  const types = ["All"];
  if (ELEMENTAL_TYPES.has(damageType)) {
    types.push("Elemental");
  }
  types.push(damageType);
  return types;
}

function resolveCategory(mastery, damageType, category) {
  const values = getApplicableTypes(damageType)
    .map((type) => mastery[category][type] ?? 0)
    .filter((value) => value > 0);

  if (values.length === 0) {
    return 0;
  }

  return Math.max(...values);
}

function calculatePairForDamageType(left, right, damageType, baseResistance) {
  const leftA = resolveCategory(left, damageType, "A");
  const rightA = resolveCategory(right, damageType, "A");
  const leftB = resolveCategory(left, damageType, "B");
  const rightB = resolveCategory(right, damageType, "B");
  const leftC = resolveCategory(left, damageType, "C");
  const rightC = resolveCategory(right, damageType, "C");
  const categoryA = Math.max(leftA, rightA);
  const categoryB = leftB + rightB;
  const categoryC = Math.max(leftC, rightC);
  const afterB = baseResistance - categoryB;
  const afterC = afterB >= 0
    ? afterB * (1 - categoryC / 100)
    : afterB * (1 + categoryC / 100);
  const finalResistance = afterC - categoryA;

  return {
    left,
    right,
    damageType,
    categoryA,
    categoryB,
    categoryC,
    stackedTotal: categoryA + categoryB + categoryC,
    finalResistance,
    effectiveReduction: baseResistance - finalResistance,
    notes: [...left.notes, ...right.notes],
    leftBreakdown: { A: leftA, B: leftB, C: leftC },
    rightBreakdown: { A: rightA, B: rightB, C: rightC }
  };
}

function getMetricValue(result) {
  if (state.filterMetric === "effectiveReduction") {
    return result.effectiveReduction;
  }

  if (state.filterMetric === "finalResistance") {
    return result.finalResistance;
  }

  return result.stackedTotal;
}

function compareByBestMetric(left, right) {
  if (state.filterMetric === "finalResistance") {
    if (left.finalResistance !== right.finalResistance) {
      return left.finalResistance - right.finalResistance;
    }
    return right.effectiveReduction - left.effectiveReduction;
  }

  const leftMetric = getMetricValue(left);
  const rightMetric = getMetricValue(right);

  if (rightMetric !== leftMetric) {
    return rightMetric - leftMetric;
  }

  return left.finalResistance - right.finalResistance;
}

function calculatePair(left, right) {
  const damageTypes = state.damageType ? [state.damageType] : DAMAGE_TYPES;
  const results = damageTypes.map((damageType) => calculatePairForDamageType(left, right, damageType, Number(state.baseResistance)));
  results.sort(compareByBestMetric);
  return results[0];
}

function buildPairs() {
  const pairs = [];
  const { masteries } = grimarillionData;

  for (let index = 0; index < masteries.length; index += 1) {
    for (let next = index + 1; next < masteries.length; next += 1) {
      pairs.push(calculatePair(masteries[index], masteries[next]));
    }
  }

  return pairs;
}

function compareMetric(value) {
  return state.comparator === "gte"
    ? value >= Number(state.threshold)
    : value <= Number(state.threshold);
}

function getFilteredPairs() {
  const search = state.search.trim().toLowerCase();
  const focusClass = state.focusClass.trim().toLowerCase();

  return buildPairs()
    .filter((pair) => compareMetric(getMetricValue(pair)))
    .filter((pair) => !state.hideConditional || pair.notes.length === 0)
    .filter((pair) => {
      if (!focusClass) {
        return true;
      }

      return pair.left.name.toLowerCase() === focusClass || pair.right.name.toLowerCase() === focusClass;
    })
    .filter((pair) => {
      if (!search) {
        return true;
      }

      return `${pair.left.name} ${pair.right.name} ${pair.damageType}`.toLowerCase().includes(search);
    })
    .sort((left, right) => {
      const pairMetricDelta = compareByBestMetric(left, right);
      if (pairMetricDelta !== 0) {
        return pairMetricDelta;
      }

      return `${left.left.name} ${left.right.name}`.localeCompare(`${right.left.name} ${right.right.name}`);
    });
}

function renderMetricLabel() {
  if (state.filterMetric === "effectiveReduction") {
    return "Effective RR";
  }

  if (state.filterMetric === "finalResistance") {
    return "Final resistance";
  }

  return "Stacked total";
}

function getFocusSummary(pairs) {
  if (!state.focusClass.trim()) {
    return null;
  }

  const focusClass = state.focusClass.trim().toLowerCase();
  const bestPair = pairs.find((pair) => pair.left.name.toLowerCase() === focusClass || pair.right.name.toLowerCase() === focusClass);

  if (!bestPair) {
    return null;
  }

  const partner = bestPair.left.name.toLowerCase() === focusClass ? bestPair.right.name : bestPair.left.name;

  return {
    partner,
    damageType: bestPair.damageType,
    metric: formatNumber(getMetricValue(bestPair)),
    finalResistance: formatNumber(bestPair.finalResistance)
  };
}

function renderSummary(pairs) {
  const strongest = pairs[0];
  const strongestLabel = strongest ? `${strongest.left.name} + ${strongest.right.name}` : "No pair matches";
  const strongestValue = strongest ? formatNumber(getMetricValue(strongest)) : "N/A";
  const focusSummary = getFocusSummary(pairs);

  return `
    <section class="summary-grid ${focusSummary ? "has-focus-summary" : ""}">
      <article class="summary-card">
        <span class="eyebrow">Matching pairs</span>
        <strong>${pairs.length}</strong>
      </article>
      <article class="summary-card">
        <span class="eyebrow">Masteries loaded</span>
        <strong>${grimarillionData.masteries.length}</strong>
      </article>
      <article class="summary-card">
        <span class="eyebrow">Best ${renderMetricLabel().toLowerCase()}</span>
        <strong>${strongestValue}</strong>
        <span class="summary-detail">${strongestLabel}${strongest ? ` • ${strongest.damageType}` : ""}</span>
      </article>
      ${focusSummary ? `
        <article class="summary-card focus-card">
          <span class="eyebrow">Best partner for ${state.focusClass}</span>
          <strong>${focusSummary.partner}</strong>
          <span class="summary-detail">${focusSummary.damageType} • metric ${focusSummary.metric} • final resist ${focusSummary.finalResistance}</span>
        </article>
      ` : ""}
    </section>
  `;
}

function renderRows(pairs) {
  if (pairs.length === 0) {
    return `
      <tr>
        <td class="empty-table" colspan="10">No 2-class combinations match this filter.</td>
      </tr>
    `;
  }

  return pairs.map((pair) => `
    <tr>
      <td class="pair-col">
        <div class="pair-names">
          <strong>${pair.left.name}</strong>
          <span>+</span>
          <strong>${pair.right.name}</strong>
        </div>
      </td>
      <td class="damage-col"><span class="damage-badge">${pair.damageType}</span></td>
      <td>${formatNumber(pair.categoryA)}</td>
      <td>${formatNumber(pair.categoryB)}</td>
      <td>${formatNumber(pair.categoryC)}%</td>
      <td class="metric-strong">${formatNumber(pair.stackedTotal)}</td>
      <td>${formatNumber(pair.finalResistance)}</td>
      <td class="metric-strong">${formatNumber(pair.effectiveReduction)}</td>
      <td class="class-breakdown">
        ${pair.left.name}: A ${formatNumber(pair.leftBreakdown.A)}, B ${formatNumber(pair.leftBreakdown.B)}, C ${formatNumber(pair.leftBreakdown.C)}%<br>
        ${pair.right.name}: A ${formatNumber(pair.rightBreakdown.A)}, B ${formatNumber(pair.rightBreakdown.B)}, C ${formatNumber(pair.rightBreakdown.C)}%
      </td>
      <td>
        ${pair.notes.length > 0
          ? pair.notes.map((note) => `<span class="note-pill">${note}</span>`).join("")
          : '<span class="muted">None</span>'}
      </td>
    </tr>
  `).join("");
}

function render() {
  const pairs = getFilteredPairs();

  app.innerHTML = `
    <main class="layout">
      <section class="hero panel">
        <div class="hero-copy-wrap">
          <p class="eyebrow">Grim Dawn - Grimarillion</p>
          <img class="hero-logo" src="https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/219990/header.jpg?t=1726250949" alt="Grim Dawn art" />
          <h1>RR Pair Finder</h1>
          <p class="hero-copy">
            Filters every 2-mastery combination using the workbook rules:
            <strong>A = highest</strong>, <strong>B = additive</strong>, <strong>C = highest</strong>.
            Leave damage type empty to automatically pick the strongest damage type per pair.
          </p>
        </div>
        <div class="rule-box">
          <div><span>A</span> ${grimarillionData.rules.A}</div>
          <div><span>B</span> ${grimarillionData.rules.B}</div>
          <div><span>C</span> ${grimarillionData.rules.C}</div>
          <p>Exact final resistance is computed as base resist -> subtract B -> apply C -> subtract A.</p>
        </div>
      </section>

      ${renderSummary(pairs)}

      <section class="controls-grid">
        <section class="panel filter-panel">
          <div class="field">
            <label for="focus-class">Class focus</label>
            <input id="focus-class" list="class-options" type="search" value="${state.focusClass}" placeholder="Type or pick a mastery" />
            <datalist id="class-options">
              ${CLASS_NAMES.map((name) => `<option value="${name}"></option>`).join("")}
            </datalist>
          </div>
          <div class="field">
            <label for="damage-type">Damage type</label>
            <select id="damage-type">
              <option value="" ${state.damageType === "" ? "selected" : ""}>Any / strongest per pair</option>
              ${DAMAGE_TYPES.map((damageType) => `<option value="${damageType}" ${state.damageType === damageType ? "selected" : ""}>${damageType}</option>`).join("")}
            </select>
          </div>
          <div class="field">
            <label for="filter-metric">Filter by</label>
            <select id="filter-metric">
              <option value="stackedTotal" ${state.filterMetric === "stackedTotal" ? "selected" : ""}>Stacked total (A + B + C)</option>
              <option value="effectiveReduction" ${state.filterMetric === "effectiveReduction" ? "selected" : ""}>Effective RR from base resist</option>
              <option value="finalResistance" ${state.filterMetric === "finalResistance" ? "selected" : ""}>Final resistance after RR</option>
            </select>
          </div>
          <div class="field">
            <label for="comparator">Comparator</label>
            <select id="comparator">
              <option value="gte" ${state.comparator === "gte" ? "selected" : ""}>Greater than or equal</option>
              <option value="lte" ${state.comparator === "lte" ? "selected" : ""}>Less than or equal</option>
            </select>
          </div>
          <div class="field">
            <label for="threshold">Threshold</label>
            <input id="threshold" type="number" step="1" value="${state.threshold}" />
          </div>
          <div class="field">
            <label for="base-resistance">Base enemy resistance</label>
            <input id="base-resistance" type="number" step="1" value="${state.baseResistance}" />
          </div>
          <div class="field field-search">
            <label for="search">Text filter</label>
            <input id="search" type="search" value="${state.search}" placeholder="Filter class names or chosen damage type" />
          </div>
          <label class="checkbox">
            <input id="hide-conditional" type="checkbox" ${state.hideConditional ? "checked" : ""} />
            <span>Hide pairs with note-based or conditional RR</span>
          </label>
        </section>

        <section class="panel info-panel">
          <h2>How this is applied</h2>
          <p><strong>Applicable columns:</strong> each damage type checks <code>All</code>, then <code>Elemental</code> when relevant, then the specific type.</p>
          <p><strong>Pair merge:</strong> A keeps the highest value across both classes, B adds both classes, C keeps the highest value across both classes.</p>
          <p><strong>Class focus:</strong> choose a class and the table becomes that class paired with every possible second class, ranked by the currently selected metric.</p>
          <p><strong>Any damage type:</strong> when damage type is empty, each pair is evaluated across all supported damage types and the strongest one is shown.</p>
          <p><strong>Source:</strong> ${grimarillionData.sourceWorkbook} / ${grimarillionData.sheet}.</p>
        </section>
      </section>

      <section class="panel table-panel">
        <div class="table-shell">
          <table>
            <thead>
              <tr>
                <th>Pair</th>
                <th>Damage</th>
                <th>A</th>
                <th>B</th>
                <th>C</th>
                <th>Stacked total</th>
                <th>Final resist</th>
                <th>Effective RR</th>
                <th>Per-class breakdown</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>${renderRows(pairs)}</tbody>
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
  if (!lastFocus) {
    return;
  }

  const element = document.getElementById(lastFocus.id);

  if (!element) {
    return;
  }

  element.focus();

  if (lastFocus.selectionStart !== null && lastFocus.selectionEnd !== null) {
    element.setSelectionRange(lastFocus.selectionStart, lastFocus.selectionEnd);
  }
}

function bindEvents() {
  app.querySelector("#focus-class").addEventListener("input", (event) => {
    captureFocus();
    state.focusClass = event.currentTarget.value;
    render();
  });

  app.querySelector("#damage-type").addEventListener("change", (event) => {
    captureFocus();
    state.damageType = event.currentTarget.value;
    render();
  });

  app.querySelector("#filter-metric").addEventListener("change", (event) => {
    captureFocus();
    state.filterMetric = event.currentTarget.value;
    if (state.filterMetric === "finalResistance" && state.comparator === "gte") {
      state.comparator = "lte";
    }
    render();
  });

  app.querySelector("#comparator").addEventListener("change", (event) => {
    captureFocus();
    state.comparator = event.currentTarget.value;
    render();
  });

  app.querySelector("#threshold").addEventListener("input", (event) => {
    captureFocus();
    state.threshold = Number(event.currentTarget.value || 0);
    render();
  });

  app.querySelector("#base-resistance").addEventListener("input", (event) => {
    captureFocus();
    state.baseResistance = Number(event.currentTarget.value || 0);
    render();
  });

  app.querySelector("#search").addEventListener("input", (event) => {
    captureFocus();
    state.search = event.currentTarget.value;
    render();
  });

  app.querySelector("#hide-conditional").addEventListener("change", (event) => {
    captureFocus();
    state.hideConditional = event.currentTarget.checked;
    render();
  });
}

render();
