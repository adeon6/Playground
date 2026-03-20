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

const examples = [
  {
    label: "הופעה קרובה",
    message: "מחפש בסיסט להופעה בשבוע הבא ב-TW12 1YU. יש חזרה אחת לפני"
  },
  {
    label: "מקום בלי פוסטקוד",
    message: "מחפש בסיסט להופעה באזור Old Street בשבוע הבא"
  },
  {
    label: "וייב של אזור",
    message: "Need a bass dep at Wembley on Friday night"
  },
  {
    label: "צ'אט רגיל",
    message: "מה נשמע? בא לך לקפה השבוע?"
  }
];

const state = {
  homePostcode: "N1 6FB",
  maxAirDistanceKm: 12,
  instrumentKeywords: [...instrumentKeywordsDefault],
  helpKeywords: [...helpKeywordsDefault],
  message: examples[0].message,
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

function extractAreaHint(text) {
  const normalized = normalizeText(text);
  const patterns = [
    /(?:around|near|at|in)\s+([A-Za-z][A-Za-z\s'-]{2,40})/i,
    /(?:באזור|ליד|ב)\s+([A-Za-z][A-Za-z\s'-]{2,40})/i,
    /(?:באזור|ליד)\s+([\u0590-\u05FF][\u0590-\u05FF\s"'-]{1,40})/i
  ];

  for (const pattern of patterns) {
    const match = normalized.match(pattern);
    if (!match?.[1]) {
      continue;
    }

    const candidate = match[1]
      .replace(/\b(on|for|with|this|next|בשבוע|ביום|עם|של)\b.*$/i, "")
      .replace(/[.,!?]+$/g, "")
      .trim();

    if (candidate.length >= 3) {
      return candidate;
    }
  }

  return null;
}

async function lookupPostcode(postcode) {
  const normalized = `postcode:${postcode.toUpperCase().replace(/\s+/g, "")}`;
  if (state.cache.has(normalized)) {
    return state.cache.get(normalized);
  }

  const response = await fetch(`https://api.postcodes.io/postcodes/${encodeURIComponent(postcode.toUpperCase().replace(/\s+/g, ""))}`);
  const payload = await response.json();
  if (!response.ok || !payload?.result) {
    throw new Error(`לא הצלחתי לזהות את הפוסטקוד ${postcode}`);
  }

  const coords = {
    latitude: payload.result.latitude,
    longitude: payload.result.longitude
  };
  state.cache.set(normalized, coords);
  return coords;
}

async function lookupAreaHint(areaHint) {
  const normalized = `place:${areaHint.toLowerCase()}`;
  if (state.cache.has(normalized)) {
    return state.cache.get(normalized);
  }

  const query = `${areaHint}, London, UK`;
  const response = await fetch(
    `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=1&countrycodes=gb&q=${encodeURIComponent(query)}`
  );
  const payload = await response.json();
  if (!response.ok || !Array.isArray(payload) || !payload.length) {
    throw new Error(`לא הצלחתי להבין את האזור "${areaHint}"`);
  }

  const first = payload[0];
  const coords = {
    latitude: Number(first.lat),
    longitude: Number(first.lon),
    label: first.display_name
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
  const areaHint = postcode ? null : extractAreaHint(message);
  const instrumentMatch = containsAnyKeyword(message, state.instrumentKeywords);
  const helpIntent = containsAnyKeyword(message, state.helpKeywords);

  if (!instrumentMatch || !helpIntent) {
    return {
      status: "ignore",
      instrumentMatch,
      helpIntent,
      postcode,
      areaHint,
      reason: !instrumentMatch ? "לא זוהה קשר ברור לבס" : "זו נראית שיחה רגילה, לא פנייה לעזרה"
    };
  }

  if (!postcode && !areaHint) {
    return {
      status: "ask-postcode",
      instrumentMatch,
      helpIntent,
      postcode,
      areaHint,
      reason: "זו נראית פנייה אמיתית, אבל חסר מיקום ברור"
    };
  }

  const homeCoords = await lookupPostcode(state.homePostcode);

  let targetCoords;
  let locationLabel = postcode;
  let locationType = "postcode";

  if (postcode) {
    targetCoords = await lookupPostcode(postcode);
  } else {
    targetCoords = await lookupAreaHint(areaHint);
    locationLabel = areaHint;
    locationType = "area";
  }

  const distanceKm = haversineDistanceKm(homeCoords, targetCoords);
  const inRange = distanceKm <= state.maxAirDistanceKm;

  return {
    status: inRange ? "reply" : "out-of-range",
    instrumentMatch,
    helpIntent,
    postcode,
    areaHint,
    distanceKm,
    inRange,
    locationLabel,
    locationType,
    reason: inRange ? "נראה באזור ולכן רלוונטי" : "נראה רחוק מדי כרגע"
  };
}

function buildReply(result) {
  if (result.status === "ignore") {
    return "אין תגובה אוטומטית. זו לא נראית כרגע כפנייה שדורשת מענה.";
  }

  if (result.status === "ask-postcode") {
    return "היי, בשמחה. כדי להבין אם זה רלוונטי לי, אפשר לשלוח גם פוסטקוד או אזור מדויק?";
  }

  if (result.status === "out-of-range") {
    return "כרגע לא הייתי שולח מענה אוטומטי. אם זה משהו חריג או חשוב במיוחד, שווה לבדוק ידנית.";
  }

  return "היי, ראיתי את ההודעה שלך. אני בסיסט ואני באזור, אז זה נשמע לי רלוונטי. אם מתאים, אפשר לשלוח עוד פרטים על מה צריך ומתי?";
}

function buildSecondaryNote(result) {
  if (result.status === "reply") {
    return result.locationType === "area"
      ? "גם בלי פוסטקוד, המערכת הצליחה להבין את האזור הכללי ולבדוק אם הוא נראה קרוב מספיק."
      : "ההודעה נראית כמו ליד אמיתי, עם כלי רלוונטי ומיקום שנמצא בטווח שהגדרת.";
  }

  if (result.status === "ask-postcode") {
    return "כאן כדאי לאשר עניין, אבל קודם לבקש מיקום ברור כדי לדעת אם בכלל להמשיך.";
  }

  if (result.status === "out-of-range") {
    return "המערכת מזהה פנייה רלוונטית, אבל מסמנת שלא כדאי לענות אוטומטית לפי הטווח הנוכחי.";
  }

  return "המערכת מסננת החוצה הודעות שלא נשמעות כמו בקשת עזרה אמיתית על בס.";
}

function statusMeta(status) {
  if (status === "reply") {
    return { label: "נשלחת תשובה", tone: "good" };
  }
  if (status === "ask-postcode") {
    return { label: "מבקשים מיקום", tone: "warn" };
  }
  if (status === "out-of-range") {
    return { label: "לא שולחים אוטומטית", tone: "muted" };
  }
  return { label: "מתעלמים", tone: "muted" };
}

function formatTime() {
  return new Date().toLocaleTimeString("he-IL", { hour: "2-digit", minute: "2-digit" });
}

function renderShell() {
  app.innerHTML = `
    <main class="page">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">Reply Lab</p>
          <h1>סימולטור תשובות שנראה כמו וואטסאפ אמיתי</h1>
          <p class="lede">
            גל יכול לכתוב כאן הודעה כאילו היא נכנסה אליך, ולראות מיד מה המערכת תעשה:
            להתעלם, לבקש מיקום, או להציע תשובה מלאה בשפה טבעית.
          </p>
        </div>

        <div class="hero-card">
          <p class="hero-kicker">מוכן לשיתוף</p>
          <strong>לינק אחד, בלי התקנה</strong>
          <span>בודק הודעות לפי כלי, כוונת עזרה, ופוסטקוד או אזור כללי כמו Old Street או Wembley</span>
        </div>
      </section>

      <section class="workspace">
        <section class="phone-shell">
          <div class="phone-frame">
            <div class="phone-topbar">
              <div class="avatar">ג</div>
              <div class="chat-meta">
                <strong>גל לונדון</strong>
                <span>מתרגל הודעות מולך</span>
              </div>
              <div class="phone-actions">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>

            <div class="chat-surface">
              <div class="system-pill">הודעת תרגול חדשה</div>
              <div class="bubble bubble-in">
                <p id="incomingBubble"></p>
                <span class="bubble-time" id="incomingTime"></span>
              </div>
              <div class="bubble bubble-out bubble-decision" id="replyBubbleWrap">
                <p id="replyBubble"></p>
                <span class="bubble-time" id="replyTime"></span>
              </div>
            </div>

            <div class="composer">
              <textarea id="messageInput" rows="4" placeholder="למשל: מחפש בסיסט באזור Old Street בשבוע הבא"></textarea>
              <button id="copyReply" type="button" class="send-btn">העתק תשובה</button>
            </div>
          </div>
        </section>

        <section class="inspector">
          <div class="panel panel-main">
            <div class="panel-head">
              <div>
                <p class="micro-label">Decision Engine</p>
                <h2>מה יקרה להודעה הזאת?</h2>
              </div>
              <div id="statusMount"></div>
            </div>

            <div id="summaryMount" class="summary-box"></div>
            <div id="factsMount" class="facts-grid"></div>
          </div>

          <div class="panel panel-controls">
            <div class="panel-head compact">
              <div>
                <p class="micro-label">Settings</p>
                <h3>כוונון מהיר</h3>
              </div>
            </div>

            <div class="field-row">
              <label class="field">
                <span>פוסטקוד בית</span>
                <input id="homePostcode" value="${state.homePostcode}" />
              </label>

              <label class="field">
                <span>טווח מקסימלי (ק"מ)</span>
                <input id="maxAirDistanceKm" type="number" min="1" max="100" value="${state.maxAirDistanceKm}" />
              </label>
            </div>

            <div class="example-strip">
              ${examples
                .map(
                  (example, index) => `
                    <button class="example-chip" data-example="${index}" type="button">${example.label}</button>
                  `
                )
                .join("")}
            </div>
          </div>
        </section>
      </section>
    </main>
  `;

  document.querySelector("#messageInput").value = state.message;
  document.querySelector("#homePostcode").addEventListener("input", handleControlsChange);
  document.querySelector("#maxAirDistanceKm").addEventListener("input", handleControlsChange);
  document.querySelector("#messageInput").addEventListener("input", handleControlsChange);

  document.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => {
      state.message = examples[Number(button.dataset.example)].message;
      document.querySelector("#messageInput").value = state.message;
      updateAnalysis();
    });
  });

  document.querySelector("#copyReply").addEventListener("click", async () => {
    const reply = document.querySelector("#replyBubble").textContent || "";
    if (!reply) {
      return;
    }

    await navigator.clipboard.writeText(reply);
    const button = document.querySelector("#copyReply");
    const original = button.textContent;
    button.textContent = "הועתק";
    setTimeout(() => {
      button.textContent = original;
    }, 1200);
  });
}

function handleControlsChange() {
  state.homePostcode = document.querySelector("#homePostcode").value.trim() || "N1 6FB";
  state.maxAirDistanceKm = Number(document.querySelector("#maxAirDistanceKm").value) || 12;
  state.message = document.querySelector("#messageInput").value;
  updateAnalysis();
}

function renderFacts(result) {
  const facts = [
    {
      label: "זוהה כלי",
      value: result.instrumentMatch ? "כן, נשמע קשור לבס" : "לא"
    },
    {
      label: "זוהתה בקשת עזרה",
      value: result.helpIntent ? "כן" : "לא"
    },
    {
      label: "מיקום שזוהה",
      value: result.postcode || result.areaHint || "לא זוהה"
    },
    {
      label: "איך זה הובן",
      value:
        result.locationType === "postcode"
          ? "לפי פוסטקוד"
          : result.locationType === "area"
            ? "לפי אזור/לנדמרק"
            : "עדיין לא"
    }
  ];

  return facts
    .map(
      (fact) => `
        <article class="fact-card">
          <span>${fact.label}</span>
          <strong>${fact.value}</strong>
        </article>
      `
    )
    .join("");
}

async function updateAnalysis() {
  const incomingBubble = document.querySelector("#incomingBubble");
  const incomingTime = document.querySelector("#incomingTime");
  const replyBubble = document.querySelector("#replyBubble");
  const replyTime = document.querySelector("#replyTime");
  const replyBubbleWrap = document.querySelector("#replyBubbleWrap");
  const statusMount = document.querySelector("#statusMount");
  const summaryMount = document.querySelector("#summaryMount");
  const factsMount = document.querySelector("#factsMount");

  const currentMessage = normalizeText(state.message);
  incomingBubble.textContent = currentMessage || "כתוב כאן הודעת תרגול כדי לראות מה יקרה.";
  incomingTime.textContent = formatTime();

  statusMount.innerHTML = `<span class="status-chip status-loading">מחשב...</span>`;
  summaryMount.innerHTML = `<p class="summary-copy">בודק אם זו פנייה אמיתית, ואם יש פוסטקוד או אזור שאפשר להבין ממנו מיקום.</p>`;
  factsMount.innerHTML = "";
  replyBubble.textContent = "";
  replyTime.textContent = "";
  replyBubbleWrap.className = "bubble bubble-out bubble-decision is-hidden";

  if (!currentMessage) {
    statusMount.innerHTML = `<span class="status-chip status-muted">ממתין להודעה</span>`;
    summaryMount.innerHTML = `<p class="summary-copy">ברגע שתכתב כאן הודעה, נראה את ההחלטה ואת התשובה המוצעת.</p>`;
    return;
  }

  try {
    const result = await evaluateMessage(currentMessage);
    const meta = statusMeta(result.status);
    const reply = buildReply(result);

    statusMount.innerHTML = `<span class="status-chip status-${meta.tone}">${meta.label}</span>`;
    summaryMount.innerHTML = `
      <div class="summary-stack">
        <p class="summary-copy">${result.reason}</p>
        <p class="summary-note">${buildSecondaryNote(result)}</p>
      </div>
    `;
    factsMount.innerHTML = renderFacts(result);

    replyBubble.textContent = reply;
    replyTime.textContent = formatTime();
    replyBubbleWrap.className = `bubble bubble-out bubble-decision ${result.status === "ignore" ? "decision-muted" : ""}`;
  } catch (error) {
    statusMount.innerHTML = `<span class="status-chip status-warn">שגיאת בדיקה</span>`;
    summaryMount.innerHTML = `
      <div class="summary-stack">
        <p class="summary-copy">${error.message}</p>
        <p class="summary-note">בדוק שהמיקום כתוב ברור, למשל פוסטקוד בריטי או אזור כמו Old Street.</p>
      </div>
    `;
    factsMount.innerHTML = `
      <article class="fact-card">
        <span>מצב</span>
        <strong>לא הצלחתי להשלים את בדיקת המיקום</strong>
      </article>
    `;
    replyBubble.textContent = "נסה שוב בעוד רגע, או כתוב פוסטקוד בריטי או אזור ברור בלונדון.";
    replyTime.textContent = formatTime();
    replyBubbleWrap.className = "bubble bubble-out bubble-decision decision-muted";
  }
}

renderShell();
updateAnalysis();
