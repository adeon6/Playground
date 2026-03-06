const app = document.querySelector("#app");
const supplements = window.WELLNESS_SUPPLEMENTS ?? [];

const conditionOptions = [
  { id: "pregnant", label: "Pregnant / trying to conceive" },
  { id: "kidney-disease", label: "Kidney disease" },
  { id: "bleeding-disorder", label: "Bleeding disorder" },
  { id: "thyroid-disorder", label: "Thyroid disorder" },
  { id: "hypercalcemia", label: "High blood calcium" },
  { id: "advanced-kidney-disease", label: "Advanced kidney disease" },
  { id: "active-cancer", label: "Active cancer / treatment" }
];

const goalOptions = [
  { id: "healthy-aging", label: "Healthy aging" },
  { id: "fat-loss", label: "Fat loss" },
  { id: "strength", label: "Strength/performance" },
  { id: "muscle-retention", label: "Muscle retention" },
  { id: "sleep", label: "Sleep quality" },
  { id: "stress", label: "Stress resilience" },
  { id: "brain-focus", label: "Brain focus/memory" },
  { id: "heart-health", label: "Heart health" },
  { id: "metabolic-health", label: "Metabolic health" }
];

function selectedValues(name) {
  return [...document.querySelectorAll(`input[name="${name}"]:checked`)].map((el) => el.value);
}

function classifySupplement(supplement, profile) {
  const reasons = [];
  const cautions = [];
  const blocks = [];
  let score = 0;

  const goalHits = supplement.goals.filter((goal) => profile.goals.includes(goal));
  if (goalHits.length) {
    reasons.push(`Matches goal(s): ${goalHits.join(", ")}`);
    score += goalHits.length * 3;
  }

  if (profile.age >= 45 && (supplement.goals.includes("healthy-aging") || supplement.goals.includes("muscle-retention"))) {
    reasons.push("Potentially relevant for age 45+ healthy aging strategy");
    score += 2;
  }

  const conditionHits = supplement.cautionConditions.filter((condition) => profile.conditions.includes(condition));
  if (conditionHits.length) {
    cautions.push(`Condition check needed: ${conditionHits.join(", ")}`);
    score -= conditionHits.length * 2;
  }

  const normalizedMedText = profile.medications.join(" ").toLowerCase();
  const medHits = supplement.cautionMeds.filter((med) => normalizedMedText.includes(med));
  if (medHits.length) {
    cautions.push(`Medication interaction risk: ${medHits.join(", ")}`);
    score -= medHits.length * 3;
  }

  const avoidHits = supplement.avoidIf.filter((rule) => profile.conditions.includes(rule));
  if (avoidHits.length) {
    blocks.push(`Avoid until clinician review: ${avoidHits.join(", ")}`);
    score -= 10;
  }

  if (!profile.goals.length) {
    reasons.push("No goals selected, showing educationally");
  }

  let status = "Relevant";
  if (blocks.length) status = "Ask clinician first";
  else if (cautions.length) status = "Use caution";
  else if (score <= 0) status = "Neutral";

  return { status, reasons, cautions, blocks, score };
}

function badgeClass(status) {
  if (status === "Relevant") return "badge badge-good";
  if (status === "Use caution") return "badge badge-warn";
  if (status === "Ask clinician first") return "badge badge-danger";
  return "badge";
}

function youtubeLink(videoId) {
  return `https://www.youtube.com/watch?v=${videoId}`;
}

function render() {
  app.innerHTML = `
    <main class="layout">
      <header class="hero panel">
        <p class="eyebrow">Wellness Messiah Companion</p>
        <h1>Interactive Supplement Inspector</h1>
        <p>
          Explore supplements discussed in videos and filter them against a user profile.
          This is educational decision-support, not medical diagnosis.
        </p>
      </header>

      <section class="panel controls">
        <div class="field-grid">
          <label class="field">
            <span>Age</span>
            <input id="age" type="number" min="18" max="99" value="35" />
          </label>

          <label class="field">
            <span>Sex</span>
            <select id="sex">
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label class="field">
            <span>Weight (kg)</span>
            <input id="weight" type="number" min="35" max="250" value="75" />
          </label>
        </div>

        <div class="chip-group">
          <p class="group-title">Goals</p>
          ${goalOptions
            .map(
              (goal, idx) => `
              <label class="chip">
                <input type="checkbox" name="goal" value="${goal.id}" ${idx < 2 ? "checked" : ""} />
                <span>${goal.label}</span>
              </label>
            `
            )
            .join("")}
        </div>

        <div class="chip-group">
          <p class="group-title">Conditions</p>
          ${conditionOptions
            .map(
              (condition) => `
              <label class="chip chip-muted">
                <input type="checkbox" name="condition" value="${condition.id}" />
                <span>${condition.label}</span>
              </label>
            `
            )
            .join("")}
        </div>

        <div class="field-grid bottom-grid">
          <label class="field">
            <span>Medications (comma-separated keywords)</span>
            <input id="medications" placeholder="warfarin, nsaid, ssri" />
          </label>

          <label class="field">
            <span>Search supplement</span>
            <input id="query" placeholder="creatine, taurine, fish oil..." />
          </label>

          <label class="field">
            <span>Status filter</span>
            <select id="statusFilter">
              <option value="all">All</option>
              <option value="Relevant">Relevant</option>
              <option value="Use caution">Use caution</option>
              <option value="Ask clinician first">Ask clinician first</option>
              <option value="Neutral">Neutral</option>
            </select>
          </label>
        </div>
      </section>

      <section id="results" class="results"></section>
    </main>
  `;

  const controls = [...document.querySelectorAll("input, select")];
  controls.forEach((control) => control.addEventListener("input", updateResults));
  updateResults();
}

function buildProfile() {
  const medicationsRaw = document.querySelector("#medications").value.trim();
  return {
    age: Number(document.querySelector("#age").value) || 0,
    sex: document.querySelector("#sex").value,
    weight: Number(document.querySelector("#weight").value) || 0,
    goals: selectedValues("goal"),
    conditions: selectedValues("condition"),
    medications: medicationsRaw ? medicationsRaw.split(",").map((item) => item.trim().toLowerCase()) : []
  };
}

function updateResults() {
  const profile = buildProfile();
  const query = document.querySelector("#query").value.trim().toLowerCase();
  const statusFilter = document.querySelector("#statusFilter").value;
  const root = document.querySelector("#results");

  const evaluated = supplements
    .map((supplement) => ({ supplement, evaluation: classifySupplement(supplement, profile) }))
    .filter(({ supplement, evaluation }) => {
      const matchesQuery =
        !query ||
        supplement.name.toLowerCase().includes(query) ||
        supplement.category.toLowerCase().includes(query) ||
        supplement.goals.some((goal) => goal.includes(query));
      const matchesStatus = statusFilter === "all" || evaluation.status === statusFilter;
      return matchesQuery && matchesStatus;
    })
    .sort((a, b) => b.evaluation.score - a.evaluation.score);

  const totals = evaluated.reduce(
    (acc, item) => {
      acc[item.evaluation.status] = (acc[item.evaluation.status] ?? 0) + 1;
      return acc;
    },
    { Relevant: 0, "Use caution": 0, "Ask clinician first": 0, Neutral: 0 }
  );

  root.innerHTML = `
    <div class="summary panel">
      <strong>${evaluated.length}</strong> supplements shown
      <span>Relevant: ${totals.Relevant}</span>
      <span>Use caution: ${totals["Use caution"]}</span>
      <span>Ask clinician first: ${totals["Ask clinician first"]}</span>
    </div>
    <div class="card-grid">
      ${
        evaluated.length
          ? evaluated
              .map(({ supplement, evaluation }) => {
                const notes = [...evaluation.reasons, ...evaluation.cautions, ...evaluation.blocks]
                  .map((line) => `<li>${line}</li>`)
                  .join("");
                const evidence = supplement.evidence
                  .map(
                    (clip) => `
                  <li>
                    <a href="${youtubeLink(clip.videoId)}" target="_blank" rel="noreferrer">
                      ${clip.title}
                    </a>
                    <span>${clip.published}</span>
                  </li>
                `
                  )
                  .join("");
                return `
                  <article class="card panel">
                    <div class="card-top">
                      <p class="icon">${supplement.icon}</p>
                      <div>
                        <h2>${supplement.name}</h2>
                        <p class="muted">${supplement.category}</p>
                      </div>
                      <p class="${badgeClass(evaluation.status)}">${evaluation.status}</p>
                    </div>
                    <p class="dose">${supplement.dosageNote}</p>
                    <ul class="list">${notes || "<li>No strong profile-specific flags found.</li>"}</ul>
                    <p class="label">Source videos</p>
                    <ul class="sources">${evidence}</ul>
                  </article>
                `;
              })
              .join("")
          : `<article class="panel empty">No matches for current filters.</article>`
      }
    </div>
  `;
}

render();
