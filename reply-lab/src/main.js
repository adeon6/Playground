const app = document.querySelector("#app");

const instrumentKeywordsDefault = ["בס", "בסיסט", "גיטרת בס", "bass", "bassist", "bass guitar"];
const helpKeywordsDefault = [
  "עזרה",
  "מחפש",
  "מחפשת",
  "צריך",
  "צריכה",
  "דרוש",
  "דרושה",
  "נגן",
  "נגנית",
  "מורה",
  "שיעור",
  "ליווי",
  "הופעה",
  "חזרה",
  "הרכב",
  "הקלטה",
  "dep",
  "session",
  "gig",
  "lesson",
  "teacher",
  "help",
  "looking for",
  "need"
];

const exampleMessages = [
  "מחפש בסיסט להופעה בשבוע הבא ב-TW12 1YU",
  "צריך מישהו על בס להקלטה קצרה ב-SE15 3EB",
  "מה נשמע? אתה פנוי לקפה השבוע?",
  "מחפשת שיעור בס באזור N1 6FB"
];

const state = {
  homePostcode: "N1 6FB",
  maxAirDistanceKm: 12,
  instrumentKeywords: [...instrumentKeywordsDefault],
  helpKeywords: [...helpKeywordsDefault],
  message: exampleMessages[0],
  cache: new Map()
};

function normalizeText(text) {
  return (text || "").replace(/\s+/g, " ").trim();
}

function containsAnyKeyword(text, keywords) {
  const normalized = normalizeText(text).toLowerCase();
  return keywords.some((keyword) => normalized.includes(keyword.toLowerCase()));
}

function extractUkPostcode(text) {
  const match = text.match(/\b([A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})\b/i);
  return match ? match[1].toUpperCase().replace(/\s+/g, " ").trim() : null;
}

async function lookupPostcode(postcode) {
  const normalized = postcode.toUpperCase().replace(/\s+/g, "");
  if (state.cache.has(normalized)) {
    return state.cache.get(normalized);
  }

  const response = await fetch(`https://api.postcodes.io/postcodes/${encodeURIComponent(normalized)}`);
  const payload = await response.json();
  if (!response.ok || !payload?.result) {
    throw new Error(`Could not find postcode ${postcode}`);
  }

  const coords = {
    latitude: payload.result.latitude,
    longitude: payload.result.longitude
  };
  state.cache.set(normalized, coords);
  return coords;
}

function haversineDistanceKm(start, end) {
  const earthRadiusKm = 6371;
  const toRadians = (degrees) => (degrees * Math.PI) / 180;
  const latitudeDelta = toRadians(end.latitude - start.latitude);
  const longitudeDelta = toRadians(end.longitude - start.longitude);
  const startLatitude = toRadians(start.latitude);
  const endLatitude = toRadians(end.latitude);

  const a =
    Math.sin(latitudeDelta / 2) ** 2 +
    Math.cos(startLatitude) * Math.cos(endLatitude) * Math.sin(longitudeDelta / 2) ** 2;

  return earthRadiusKm * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

async function evaluateMessage(message) {
  const postcode = extractUkPostcode(message);
  const instrumentMatch = containsAnyKeyword(message, state.instrumentKeywords);
  const helpIntent = containsAnyKeyword(message, state.helpKeywords);

  if (!instrumentMatch || !helpIntent) {
    return {
      status: "ignore",
      instrumentMatch,
      helpIntent,
      postcode,
      reason: !instrumentMatch ? "לא זוהה קשר ברור לבס" : "זה נראה כמו צ'אט רגיל, לא בקשת עזרה"
    };
  }

  if (!postcode) {
    return {
      status: "ask-postcode",
      instrumentMatch,
      helpIntent,
      postcode,
      reason: "נראית בקשת עזרה רלוונטית, אבל חסר פוסטקוד"
    };
  }

  const [homeCoords, leadCoords] = await Promise.all([
    lookupPostcode(state.homePostcode),
    lookupPostcode(postcode)
  ]);

  const distanceKm = haversineDistanceKm(homeCoords, leadCoords);
  const inRange = distanceKm <= state.maxAirDistanceKm;

  return {
    status: inRange ? "reply" : "out-of-range",
    instrumentMatch,
    helpIntent,
    postcode,
    distanceKm,
    inRange,
    reason: inRange ? "נראה רלוונטי ואזורי" : "נראה רחוק מדי כרגע"
  };
}

function buildReply(result) {
  if (result.status === "ignore") {
    return "לא נשלחת תשובה. ההודעה נראית כמו שיחה רגילה או לא קשורה לבס.";
  }

  if (result.status === "ask-postcode") {
    return "היי, בשמחה. כדי להבין אם זה רלוונטי לי, אפשר לשלוח גם את הפוסטקוד של המקום?";
  }

  if (result.status === "out-of-range") {
    return "כרגע לא הייתי עונה אוטומטית, כי זה נראה קצת רחוק. אם זה משהו מיוחד, אפשר לבדוק ידנית.";
  }

  return "היי, ראיתי את ההודעה שלך. אני בסיסט ואני באזור, אז זה נשמע לי רלוונטי. אם מתאים, אפשר לשלוח עוד פרטים על מה צריך ומתי?";
}

function statusMeta(status) {
  if (status === "reply") {
    return { label: "לענות", tone: "good" };
  }
  if (status === "ask-postcode") {
    return { label: "לבקש פוסטקוד", tone: "warn" };
  }
  if (status === "out-of-range") {
    return { label: "לא לענות אוטומטית", tone: "muted" };
  }
  return { label: "להתעלם", tone: "muted" };
}

function renderShell() {
  app.innerHTML = `
    <main class="page">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">Reply Lab</p>
          <h1>סימולטור תשובות לגל</h1>
          <p class="lede">
            גל יכול לכתוב כאן הודעה כאילו היא הגיעה בוואטסאפ, ולקבל מיד החלטה:
            להתעלם, לבקש פוסטקוד, או להראות את התשובה שהיית שולח.
          </p>
        </div>
        <div class="hero-card">
          <p class="hero-kicker">מצב עבודה</p>
          <strong>בסיסט בלונדון</strong>
          <span>פוסטקוד בית: <b id="homePostcodeLabel">${state.homePostcode}</b></span>
        </div>
      </section>

      <section class="workspace">
        <div class="panel controls">
          <div class="field-row">
            <label class="field">
              <span>פוסטקוד בית</span>
              <input id="homePostcode" value="${state.homePostcode}" />
            </label>
            <label class="field">
              <span>טווח אווירי מקסימלי (ק"מ)</span>
              <input id="maxAirDistanceKm" type="number" min="1" max="100" value="${state.maxAirDistanceKm}" />
            </label>
          </div>

          <label class="field field-large">
            <span>הודעת תרגול</span>
            <textarea id="messageInput" rows="8" placeholder="למשל: מחפש בסיסט להופעה ב-TW12 1YU בשבוע הבא">${state.message}</textarea>
          </label>

          <div class="example-strip">
            ${exampleMessages
              .map(
                (message, index) => `
                <button class="example-chip" data-example="${index}" type="button">${message}</button>
              `
              )
              .join("")}
          </div>
        </div>

        <div class="panel analysis">
          <div id="statusMount" class="status-mount"></div>
          <div id="factsMount" class="facts-grid"></div>
          <div class="reply-box">
            <div class="reply-head">
              <span>תשובה מוצעת</span>
              <button id="copyReply" type="button" class="ghost-btn">העתק</button>
            </div>
            <p id="replyOutput" class="reply-output"></p>
          </div>
        </div>
      </section>
    </main>
  `;

  document.querySelector("#homePostcode").addEventListener("input", handleControlsChange);
  document.querySelector("#maxAirDistanceKm").addEventListener("input", handleControlsChange);
  document.querySelector("#messageInput").addEventListener("input", handleControlsChange);
  document.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => {
      state.message = exampleMessages[Number(button.dataset.example)];
      document.querySelector("#messageInput").value = state.message;
      updateAnalysis();
    });
  });
  document.querySelector("#copyReply").addEventListener("click", async () => {
    const reply = document.querySelector("#replyOutput").textContent || "";
    await navigator.clipboard.writeText(reply);
    document.querySelector("#copyReply").textContent = "הועתק";
    setTimeout(() => {
      document.querySelector("#copyReply").textContent = "העתק";
    }, 1200);
  });
}

function handleControlsChange() {
  state.homePostcode = document.querySelector("#homePostcode").value.trim() || "N1 6FB";
  state.maxAirDistanceKm = Number(document.querySelector("#maxAirDistanceKm").value) || 12;
  state.message = document.querySelector("#messageInput").value;
  document.querySelector("#homePostcodeLabel").textContent = state.homePostcode;
  updateAnalysis();
}

async function updateAnalysis() {
  const statusMount = document.querySelector("#statusMount");
  const factsMount = document.querySelector("#factsMount");
  const replyOutput = document.querySelector("#replyOutput");

  statusMount.innerHTML = `<p class="loading">מחשב...</p>`;
  factsMount.innerHTML = "";
  replyOutput.textContent = "";

  try {
    const result = await evaluateMessage(state.message);
    const meta = statusMeta(result.status);

    statusMount.innerHTML = `
      <div class="status-card status-${meta.tone}">
        <span class="status-label">${meta.label}</span>
        <p>${result.reason}</p>
      </div>
    `;

    const facts = [
      { label: "זוהה כלי", value: result.instrumentMatch ? "כן" : "לא" },
      { label: "זוהתה בקשת עזרה", value: result.helpIntent ? "כן" : "לא" },
      { label: "פוסטקוד", value: result.postcode || "לא זוהה" },
      {
        label: "טווח",
        value:
          typeof result.distanceKm === "number"
            ? `${result.distanceKm.toFixed(1)} ק"מ, סף ${state.maxAirDistanceKm}`
            : "לא חושב"
      }
    ];

    factsMount.innerHTML = facts
      .map(
        (fact) => `
          <article class="fact-card">
            <span>${fact.label}</span>
            <strong>${fact.value}</strong>
          </article>
        `
      )
      .join("");

    replyOutput.textContent = buildReply(result);
  } catch (error) {
    statusMount.innerHTML = `
      <div class="status-card status-warn">
        <span class="status-label">שגיאת בדיקה</span>
        <p>${error.message}</p>
      </div>
    `;

    factsMount.innerHTML = `
      <article class="fact-card">
        <span>מה קרה</span>
        <strong>לא הצלחתי לבדוק את הפוסטקוד כרגע</strong>
      </article>
    `;

    replyOutput.textContent = "נסה שוב בעוד רגע, או בדוק שהפוסטקוד הוא בריטי וכתוב נכון.";
  }
}

renderShell();
updateAnalysis();
