/* Slang Lab: learn common English slang/idioms with pronunciation. */
const page = buildShell("Slang Lab", "BERREADY / Slang Lab");

const SLANG = [
  { word: "Ghost someone", meaning: "To suddenly stop replying to someone, cutting off all communication.", example: "We were texting every day, then she ghosted me.", category: "Social" },
  { word: "No cap", meaning: "No lie, for real, I'm being completely honest.", example: "That was the best meal I've ever had, no cap.", category: "Casual" },
  { word: "Hit me up", meaning: "Contact me, reach out to me (usually via text or DM).", example: "Hit me up if you want to grab coffee later.", category: "Social" },
  { word: "Salty", meaning: "Being upset or bitter about something, usually over a small thing.", example: "He's still salty about losing that game last week.", category: "Emotion" },
  { word: "Lit", meaning: "Something exciting, amazing, or high-energy.", example: "The party last night was absolutely lit.", category: "Descriptive" },
  { word: "Vibe check", meaning: "Assessing the mood or energy of a person or situation.", example: "Walk into the room and do a quick vibe check before speaking.", category: "Social" },
  { word: "Biggest flex", meaning: "Your most impressive achievement or something you're really proud of.", example: "Learning three languages is my biggest flex.", category: "Casual" },
  { word: "Lowkey / Highkey", meaning: "Lowkey = somewhat, secretly. Highkey = very much, openly.", example: "I'm lowkey nervous about the interview. / I highkey love this song.", category: "Casual" },
  { word: "Bet", meaning: "Okay, sure, sounds good — agreement or confirmation.", example: "Want to meet at 6? — Bet.", category: "Social" },
  { word: "Slay", meaning: "To do something extremely well, to succeed impressively.", example: "You absolutely slayed that presentation.", category: "Descriptive" },
  { word: "Periodt", meaning: "End of discussion, that's final, no argument.", example: "She's the best candidate for the role, periodt.", category: "Casual" },
  { word: "Snatched", meaning: "Looking really good, on point, perfectly put together.", example: "Your outfit today is absolutely snatched.", category: "Descriptive" },
  { word: "Yeet", meaning: "To throw something with force, or an exclamation of excitement.", example: "He yeeted his phone across the room when he heard the news.", category: "Action" },
  { word: "Suss / Sus", meaning: "Suspicious, sketchy, not trustworthy.", example: "That email looks sus — don't click any links.", category: "Descriptive" },
  { word: "GOAT", meaning: "Greatest Of All Time — someone who's the best at what they do.", example: "Messi is the GOAT of football.", category: "Descriptive" },
  { word: "Shook", meaning: "Extremely shocked or surprised, can't believe it.", example: "I was shook when I saw my exam results.", category: "Emotion" },
  { word: "Bussin", meaning: "Really good, especially used for food that tastes amazing.", example: "This pasta is bussin, what's the recipe?", category: "Descriptive" },
  { word: "Cap / No cap", meaning: "Cap = a lie. No cap = the truth. Used to call out or confirm honesty.", example: "That story sounds like cap. — Nah, no cap, it really happened.", category: "Casual" },
  { word: "Stan", meaning: "An overly obsessed fan, or to be a very enthusiastic supporter of someone.", example: "I stan anyone who works that hard on their craft.", category: "Social" },
  { word: "Pick me", meaning: "Someone who seeks attention/validation by doing things for approval, often putting others down.", example: "Stop being a pick me — just be yourself.", category: "Social" },
  { word: "It's giving...", meaning: "It's giving off a certain vibe or energy (left open-ended for interpretation).", example: "That outfit is giving main character energy.", category: "Descriptive" },
  { word: "Understood the assignment", meaning: "Did exactly what was needed, nailed it perfectly.", example: "She showed up in that dress and understood the assignment.", category: "Descriptive" },
  { word: "Rent free", meaning: "Something or someone that keeps occupying your thoughts, you can't stop thinking about it.", example: "That awkward moment lives in my head rent free.", category: "Emotion" },
  { word: "Touch grass", meaning: "Go outside, get some fresh air, disconnect from the internet.", example: "You've been gaming for 10 hours — go touch grass.", category: "Social" },
  { word: "Main character energy", meaning: "Acting like you're the protagonist of a movie — confident, magnetic, unapologetic.", example: "She walked in with main character energy and owned the room.", category: "Descriptive" },
  { word: "That hits different", meaning: "Something feels uniquely special or impactful in a way it didn't before.", example: "Hearing your favorite song live hits different.", category: "Emotion" },
  { word: "Dead / I'm dead", meaning: "Something is so funny you can't handle it, you're dying of laughter.", example: "Did you see that meme? I'm dead.", category: "Emotion" },
  { word: "Clout", meaning: "Influence, power, or popularity, especially on social media.", example: "He's just doing it for clout.", category: "Social" },
  { word: "W / L", meaning: "W = Win (something good). L = Loss (something bad or embarrassing).", example: "Got the job — that's a huge W. / Trippped in public — total L.", category: "Casual" },
  { word: "Mid", meaning: "Mediocre, average, nothing special — used as a criticism.", example: "The movie was mid, nothing worth watching again.", category: "Descriptive" },
];

const CATEGORIES = [...new Set(SLANG.map(s => s.category))];

let activeCategory = "All";
let audioPlaying = null;
let currentAudio = null;

function render() {
  const filtered = activeCategory === "All" ? SLANG : SLANG.filter(s => s.category === activeCategory);
  page.innerHTML = `
    <p class="sub">Common English slang and idioms — click the speaker to hear pronunciation.</p>
    <div class="row mb" style="flex-wrap:wrap;gap:6px">
      <button class="cat-btn ${activeCategory === "All" ? "primary" : ""}" data-cat="All">All (${SLANG.length})</button>
      ${CATEGORIES.map(c => `<button class="cat-btn ${activeCategory === c ? "primary" : ""}" data-cat="${c}">${c} (${SLANG.filter(s => s.category === c).length})</button>`).join("")}
    </div>
    <div id="slangList">${filtered.map((s, i) => slangCard(s, SLANG.indexOf(s))).join("")}</div>`;
  document.querySelectorAll(".cat-btn").forEach(b => {
    b.onclick = () => { activeCategory = b.dataset.cat; render(); };
  });
  document.querySelectorAll(".speak-btn").forEach(b => {
    b.onclick = () => playSlang(b.dataset.idx, b);
  });
}

function slangCard(s, idx) {
  return `<div class="card mb" style="border-left:3px solid var(--accent)">
    <div class="row" style="align-items:center">
      <div style="flex:1">
        <div class="row" style="align-items:center;gap:8px">
          <b style="font-size:15px">${esc(s.word)}</b>
          <span class="score" style="font-size:11px">${esc(s.category)}</span>
        </div>
        <div class="small" style="margin-top:4px">${esc(s.meaning)}</div>
        <div class="small dim" style="margin-top:4px;font-style:italic">"${esc(s.example)}"</div>
      </div>
      <button class="speak-btn ghost" data-idx="${idx}" title="Hear pronunciation" style="font-size:18px;padding:6px 10px">🔊</button>
    </div>
  </div>`;
}

async function playSlang(idx, btn) {
  const s = SLANG[idx];
  if (!s) return;

  // Prevent duplicate calls — if already playing this word, stop it.
  if (audioPlaying === idx) {
    if (currentAudio) { currentAudio.pause(); currentAudio = null; }
    audioPlaying = null;
    btn.textContent = "🔊";
    btn.classList.remove("rec");
    return;
  }

  // Stop any currently playing audio
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  audioPlaying = null;
  document.querySelectorAll(".speak-btn").forEach(b => { b.textContent = "🔊"; b.classList.remove("rec"); });

  // Show loading state
  btn.textContent = "⏳";
  btn.disabled = true;

  const textToSpeak = `${s.word}. ${s.meaning} For example: ${s.example}`;

  try {
    const resp = await fetch((window.APP_CONFIG?.API_BASE || "") + "/api/tts/speak", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: textToSpeak }),
    });

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.error || `HTTP ${resp.status}`);
    }

    const contentType = resp.headers.get("content-type") || "";
    if (!contentType.includes("audio")) {
      const errData = await resp.json().catch(() => ({}));
      throw new Error(errData.error || "Server did not return audio");
    }

    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    currentAudio = audio;
    audioPlaying = idx;

    btn.textContent = "🔊";
    btn.classList.add("rec");

    audio.onended = () => {
      audioPlaying = null;
      currentAudio = null;
      btn.textContent = "🔊";
      btn.classList.remove("rec");
      URL.revokeObjectURL(url);
    };

    audio.onerror = () => {
      audioPlaying = null;
      currentAudio = null;
      btn.textContent = "🔊";
      btn.classList.remove("rec");
      URL.revokeObjectURL(url);
    };

    await audio.play();
  } catch (err) {
    console.error("TTS error:", err);
    audioPlaying = null;
    currentAudio = null;
    btn.textContent = "⚠️";
    setTimeout(() => { btn.textContent = "🔊"; }, 2000);
  } finally {
    btn.disabled = false;
  }
}

render();
