// =================================================================
// CHAT WIDGET
// =================================================================
const chatWindow = document.getElementById('chatWindow');
const chatForm = document.getElementById('chatForm');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const chatPanel = document.getElementById('chatPanel');
const suggestionRow = document.getElementById('suggestionRow');

function openChat() {
  if (chatPanel) chatPanel.classList.remove('hidden');
  if (userInput) userInput.focus();
}
function closeChat() {
  if (chatPanel) chatPanel.classList.add('hidden');
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

const ROBOT_AVATAR_IMG = '<img src="/static/img/voice-assistant-robot.png" alt="AI">';

function addMessage(text, sender) {
  const msg = document.createElement('div');
  msg.className = `msg ${sender}`;
  const avatarContent = sender === 'user' ? '🧑' : ROBOT_AVATAR_IMG;
  const avatarClass = sender === 'user' ? 'avatar' : 'avatar ai-v2-robot-avatar';
  msg.innerHTML = `
    <div class="${avatarClass}">${avatarContent}</div>
    <div class="bubble">${escapeHtml(text)}</div>
  `;
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return msg;
}

function addTyping() {
  const msg = document.createElement('div');
  msg.className = 'msg bot';
  msg.innerHTML = `
    <div class="avatar ai-v2-robot-avatar">${ROBOT_AVATAR_IMG}</div>
    <div class="bubble typing"><span></span><span></span><span></span></div>
  `;
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return msg;
}

function renderSuggestions(suggestions) {
  if (!suggestionRow) return;
  suggestionRow.innerHTML = '';
  (suggestions || []).forEach((q) => {
    const btn = document.createElement('button');
    btn.className = 'suggestion-chip';
    btn.textContent = q;
    btn.onclick = () => sendMessage(q);
    suggestionRow.appendChild(btn);
  });
}

const welcomeScreen = document.getElementById('welcomeScreen');

async function sendMessage(text, onSpokenEnd) {
  if (welcomeScreen && !welcomeScreen.classList.contains('welcome-hidden')) {
    welcomeScreen.classList.add('welcome-hidden');
  }
  addMessage(text, 'user');
  userInput.value = '';
  sendBtn.disabled = true;
  renderSuggestions([]);
  const typingEl = addTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, lang: currentVoiceLang })
    });
    const data = await res.json();
    await new Promise(r => setTimeout(r, 150));
    typingEl.remove();
    addMessage(data.reply, 'bot');
    renderSuggestions(data.suggestions);
    // data.reply is already translated to the selected language server-side,
    // so speak it directly — no need to translate a second time.
    await speakText(data.reply, onSpokenEnd, true);
  } catch (err) {
    typingEl.remove();
    addMessage('Something went wrong. Please try again.', 'bot');
    if (onSpokenEnd) onSpokenEnd();
  }

  sendBtn.disabled = false;
  userInput.focus();
}

if (chatForm) {
  chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = userInput.value.trim();
    if (text) sendMessage(text);
  });
}

document.querySelectorAll('.chip').forEach((chip) => {
  chip.addEventListener('click', () => {
    openChat();
    sendMessage(chip.dataset.q);
  });
});

document.querySelectorAll('.ai-v2-quick-item').forEach((item) => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.ai-v2-quick-item').forEach((i) => i.classList.remove('active'));
    item.classList.add('active');
    sendMessage(item.dataset.q);
  });
});

const resetChatBtn = document.getElementById('resetChatBtn');
if (resetChatBtn) {
  resetChatBtn.addEventListener('click', () => {
    if (confirm('Start a new conversation? This will clear the current chat.')) {
      window.location.reload();
    }
  });
}


document.querySelectorAll('.ai-suggest-card').forEach((card) => {
  card.addEventListener('click', () => {
    sendMessage(card.dataset.q);
  });
});

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {});
  });
}

// =================================================================
// DARK / LIGHT THEME TOGGLE
// =================================================================
const themeToggle = document.getElementById('themeToggle');
function applyTheme(theme) {
  document.body.classList.toggle('dark-theme', theme === 'dark');
  if (themeToggle) themeToggle.textContent = theme === 'dark' ? '☀️' : '🌙';
}
const savedTheme = localStorage.getItem('site-theme') || 'light';
applyTheme(savedTheme);
if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const isDark = document.body.classList.contains('dark-theme');
    const newTheme = isDark ? 'light' : 'dark';
    applyTheme(newTheme);
    localStorage.setItem('site-theme', newTheme);
  });
}

// =================================================================
// ANIMATED COUNTERS
// =================================================================
function animateCounter(el) {
  const target = parseFloat(el.dataset.target);
  const suffix = el.dataset.suffix || '';
  if (isNaN(target)) return;
  let current = 0;
  const duration = 1200;
  const steps = 40;
  const increment = target / steps;
  const stepTime = duration / steps;
  const timer = setInterval(() => {
    current += increment;
    if (current >= target) {
      current = target;
      clearInterval(timer);
    }
    el.textContent = Math.round(current) + suffix;
  }, stepTime);
}

// =================================================================
// SCROLL REVEAL ANIMATIONS + COUNTER TRIGGER
// =================================================================
const revealEls = document.querySelectorAll('.reveal');
const counterEls = document.querySelectorAll('.stat-num[data-target]');

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('in-view');
      // Animate any not-yet-animated counters inside this revealed section
      // (works for .stat-card, .hero-stats-bar, .mini-stat-row, etc.)
      const counters = entry.target.querySelectorAll('.stat-num[data-target]');
      counters.forEach((counter) => {
        if (!counter.dataset.animated) {
          counter.dataset.animated = '1';
          animateCounter(counter);
        }
      });
      // The hero stats bar sits just below the hero header, outside any
      // .reveal wrapper — check it separately once the page has loaded.
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });

revealEls.forEach((el) => observer.observe(el));

// The hero stats bar isn't inside a `.reveal` section (it overlaps the
// hero photo), so animate its counters as soon as the page loads.
document.querySelectorAll('.hero-stats-bar .stat-num[data-target]').forEach((counter) => {
  if (!counter.dataset.animated) {
    counter.dataset.animated = '1';
    animateCounter(counter);
  }
});

// =================================================================
// GALLERY LIGHTBOX
// =================================================================
function openLightbox(src, caption) {
  const overlay = document.getElementById('lightboxOverlay');
  const img = document.getElementById('lightboxImg');
  const cap = document.getElementById('lightboxCaption');
  img.src = src;
  cap.textContent = caption || '';
  overlay.classList.remove('hidden');
}
function closeLightbox() {
  document.getElementById('lightboxOverlay').classList.add('hidden');
}

// =================================================================
// SITE SEARCH (simple client-side search across visible text sections)
// =================================================================
const siteSearch = document.getElementById('siteSearch');
const searchResults = document.getElementById('searchResults');

if (siteSearch) {
  siteSearch.addEventListener('input', () => {
    const q = siteSearch.value.trim().toLowerCase();
    if (q.length < 2) {
      searchResults.classList.add('hidden');
      searchResults.innerHTML = '';
      return;
    }

    const sections = document.querySelectorAll('main .section');
    const matches = [];
    sections.forEach((sec) => {
      const heading = sec.querySelector('h2');
      const text = sec.innerText.toLowerCase();
      if (text.includes(q) && heading) {
        matches.push({ id: sec.id, title: heading.textContent });
      }
    });

    if (matches.length === 0) {
      searchResults.innerHTML = '<div class="search-empty">No matches found</div>';
    } else {
      searchResults.innerHTML = matches
        .map((m) => `<a href="#${m.id}" class="search-result-item">${m.title}</a>`)
        .join('');
    }
    searchResults.classList.remove('hidden');
  });

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-bar-wrap')) {
      searchResults.classList.add('hidden');
    }
  });

  searchResults.addEventListener('click', () => {
    siteSearch.value = '';
    searchResults.classList.add('hidden');
  });
}

// =================================================================
// GALLERY AUTO-CAROUSEL
// =================================================================
(function () {
  const track = document.getElementById('carouselTrack');
  const dotsWrap = document.getElementById('carouselDots');
  if (!track || !dotsWrap) return;

  const slides = track.querySelectorAll('.carousel-slide');
  if (slides.length === 0) return;

  let current = 0;

  slides.forEach((_, i) => {
    const dot = document.createElement('div');
    dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
    dot.addEventListener('click', () => goTo(i));
    dotsWrap.appendChild(dot);
  });
  const dots = dotsWrap.querySelectorAll('.carousel-dot');

  function goTo(index) {
    current = (index + slides.length) % slides.length;
    track.style.transform = `translateX(-${current * 100}%)`;
    dots.forEach((d, i) => d.classList.toggle('active', i === current));
  }

  let autoplay = setInterval(() => goTo(current + 1), 4000);

  const carousel = document.getElementById('galleryCarousel');
  if (carousel) {
    carousel.addEventListener('mouseenter', () => clearInterval(autoplay));
    carousel.addEventListener('mouseleave', () => { autoplay = setInterval(() => goTo(current + 1), 4000); });
  }
})();

// =================================================================
// SPLASH SCREEN (auto-remove after animation so it never blocks clicks)
// =================================================================
(function () {
  const splash = document.getElementById('splashScreen');
  if (!splash) return;
  setTimeout(() => splash.remove(), 3400);
})();

// =================================================================
// VOICE MODE — single mic icon, jaise ChatGPT / Gemini / Alexa.
// Jab tak voice mode ON nahi hota, koi jawab bola nahi jaata (text hi
// dikhta hai). Mic dabate hi ek overlay orb dikhta hai jo Listening/
// Thinking/Speaking status batata hai. Wahi mic ya "Stop" dabao to band.
// =================================================================
let voiceModeActive = false;

// ---------- Voice output language: 'en' (default), 'hi', or 'mr' ----------
let currentVoiceLang = localStorage.getItem('voiceLang') || 'en';
const voiceLangSelect = document.getElementById('voiceLangSelect');
if (voiceLangSelect) {
  voiceLangSelect.value = currentVoiceLang;
  voiceLangSelect.addEventListener('change', () => {
    currentVoiceLang = voiceLangSelect.value;
    localStorage.setItem('voiceLang', currentVoiceLang);
    populateVoiceDropdown();
    stopAllSpeech();
  });
}

// ---------- ElevenLabs voice choice: which "actor" voice speaks the replies ----------
let currentElevenLabsVoice = localStorage.getItem('elevenLabsVoice') || 'manav';
const voiceChoiceSelect = document.getElementById('voiceChoiceSelect');
if (voiceChoiceSelect) {
  voiceChoiceSelect.value = currentElevenLabsVoice;
  voiceChoiceSelect.addEventListener('change', () => {
    currentElevenLabsVoice = voiceChoiceSelect.value;
    localStorage.setItem('elevenLabsVoice', currentElevenLabsVoice);
    stopAllSpeech();
  });
}

// ---------- Voice selection: list whatever voices this device actually has ----------
// Different phones/browsers ship with different installed voices (could be
// 1, could be 6) — we don't guess or hardcode, we just show what's really there.
let currentVoiceURI = localStorage.getItem('voiceURI') || '';
const voiceGenderSelect = document.getElementById('voiceGenderSelect');
let _cachedVoice = null;

function languageMatches(voiceLang, appLang) {
  if (!voiceLang) return false;
  const v = voiceLang.toLowerCase();
  if (appLang === 'hi') return v.startsWith('hi');
  if (appLang === 'mr') return v.startsWith('mr');
  return v.startsWith('en');
}

function populateVoiceDropdown() {
  if (!voiceGenderSelect || !('speechSynthesis' in window)) return;
  const allVoices = window.speechSynthesis.getVoices();
  if (!allVoices.length) return;

  // Prefer voices matching the currently selected language; if this device
  // has none installed for that language, fall back to showing all voices
  // so the option list is never empty.
  let relevant = allVoices.filter((v) => languageMatches(v.lang, currentVoiceLang));
  if (!relevant.length) relevant = allVoices;

  voiceGenderSelect.innerHTML = '';
  relevant.forEach((v) => {
    const opt = document.createElement('option');
    opt.value = v.voiceURI;
    opt.textContent = v.name.replace(/^Microsoft |^Google /, '') + (v.lang ? ` (${v.lang})` : '');
    voiceGenderSelect.appendChild(opt);
  });

  // Restore the saved choice if it's still in this list, else default to the first one.
  const savedStillValid = relevant.some((v) => v.voiceURI === currentVoiceURI);
  voiceGenderSelect.value = savedStillValid ? currentVoiceURI : relevant[0].voiceURI;
  currentVoiceURI = voiceGenderSelect.value;
  _cachedVoice = relevant.find((v) => v.voiceURI === currentVoiceURI) || relevant[0];
}

if (voiceGenderSelect) {
  voiceGenderSelect.addEventListener('change', () => {
    currentVoiceURI = voiceGenderSelect.value;
    localStorage.setItem('voiceURI', currentVoiceURI);
    const allVoices = window.speechSynthesis.getVoices();
    _cachedVoice = allVoices.find((v) => v.voiceURI === currentVoiceURI) || null;
    stopAllSpeech();
  });
}

// ---------- Pick the best-sounding voice for a given language (fallback path) ----------
function pickBestVoice(lang) {
  if (!('speechSynthesis' in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;
  return (
    voices.find((v) => languageMatches(v.lang, lang) && v.name.startsWith('Google')) ||
    voices.find((v) => languageMatches(v.lang, lang)) ||
    voices.find((v) => v.lang && v.lang.startsWith('en')) ||
    voices[0]
  );
}
if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = populateVoiceDropdown;
  populateVoiceDropdown();
}

// ---------- Fix common mispronunciations before speaking out loud ----------
// The browser's TTS engine reads institution-specific acronyms as if they
// were regular words (e.g. "SEDCOE" comes out as gibberish). We spell these
// out letter-by-letter (or expand them) ONLY for the spoken audio — the
// text shown in the chat bubble is never touched.
const ACRONYM_PRONUNCIATIONS = {
  SEDCOE: 'S E D C O E', MSBTE: 'M S B T E', HOD: 'H O D', CEO: 'C E O',
  TPO: 'T P O', NGO: 'N G O', ITI: 'I T I', CCTV: 'C C T V',
  EWS: 'E W S', EBC: 'E B C', TFWS: 'T F W S', VJNT: 'V J N T',
  SBC: 'S B C', OBC: 'O B C', HSC: 'H S C', SSC: 'S S C',
  KPIT: 'K P I T', TCS: 'T C S', GOI: 'Government of India',
  DND: 'D N D', KGVP: 'K G V P', LPA: 'lakhs per annum',
  AICTE: 'A I C T E', NAAC: 'N A A C', IQAC: 'I Q A C',
};

function fixPronunciation(text) {
  let out = text;
  // Spell out known acronyms (word-boundary match, case-sensitive so we
  // don't touch normal lowercase words).
  Object.keys(ACRONYM_PRONUNCIATIONS).forEach((acr) => {
    const re = new RegExp(`\\b${acr}\\b`, 'g');
    out = out.replace(re, ACRONYM_PRONUNCIATIONS[acr]);
  });
  // Symbols that get misread or skipped entirely.
  out = out
    .replace(/₹/g, ' rupees ')
    .replace(/%/g, ' percent')
    .replace(/&/g, ' and ')
    .replace(/[•●▪]/g, ', ')   // bullet points → a short pause instead of silence
    .replace(/\bB\.E\.?\b/g, 'B E')
    .replace(/\bDr\.\s/g, 'Doctor ')
    .replace(/\s+/g, ' ')
    .trim();
  return out;
}

function stopAllSpeech() {
  if (_elevenLabsAudio) { try { _elevenLabsAudio.pause(); } catch (err) {} _elevenLabsAudio = null; }
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
}

async function speakText(text, onDone, alreadyTranslated) {
  if (!voiceModeActive) {
    if (onDone) onDone();
    return;
  }
  let plain = text.replace(/[*_#`]/g, '').replace(/\s+/g, ' ').trim();

  // If a non-English voice is selected, translate the reply first so the
  // spoken output actually matches the chosen language. If translation
  // fails for any reason (no internet, no API key set up), it just speaks
  // the original English text instead — never silently breaks.
  // Skipped when the text has already been translated server-side
  // (e.g. the chat reply text itself was already returned in Hindi/Marathi).
  if (currentVoiceLang !== 'en' && !alreadyTranslated) {
    if (voiceOverlayStatus) voiceOverlayStatus.textContent = 'Translating…';
    try {
      const res = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: plain, lang: currentVoiceLang })
      });
      const data = await res.json();
      if (data.translated) plain = data.translated;
    } catch (err) {
      // network/translate failure — fall back to speaking original text
    }
  }

  // Fix known mispronunciations (acronyms, ₹, %, & etc.) before speaking.
  plain = fixPronunciation(plain);

  // Try the natural ElevenLabs voice first — unless the admin has manually
  // switched the site to the backup browser voice (e.g. ElevenLabs quota
  // ran out for the month). If it's not configured on the server, or the
  // request fails for any reason, we fall straight through to the browser's
  // own built-in voice below — voice mode never breaks.
  const useElevenLabs = (window.VOICE_MODE || 'elevenlabs') !== 'browser';
  if (useElevenLabs) {
    const playedWithElevenLabs = await speakWithElevenLabs(plain, onDone);
    if (playedWithElevenLabs) return;
  }

  if (!('speechSynthesis' in window)) {
    if (onDone) onDone();
    return;
  }

  const utterance = new SpeechSynthesisUtterance(plain);
  // Slightly slower + a gentler pitch reads noticeably more natural than
  // the browser default, especially for longer sentences.
  utterance.rate = 0.92;
  utterance.pitch = 1.0;
  if (currentVoiceLang === 'hi') utterance.lang = 'hi-IN';
  else if (currentVoiceLang === 'mr') utterance.lang = 'mr-IN';
  const voice = _cachedVoice || pickBestVoice(currentVoiceLang);
  if (voice) utterance.voice = voice;
  utterance.onstart = () => setVoiceStatus('speaking');
  utterance.onend = () => { if (onDone) onDone(); };
  utterance.onerror = () => { if (onDone) onDone(); };
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

let _elevenLabsAudio = null;

// Requests natural-sounding speech audio from the server (ElevenLabs) and
// plays it. Returns true if playback started successfully, false if it
// should fall back to the browser's built-in voice instead.
async function speakWithElevenLabs(text, onDone) {
  try {
    const res = await fetch('/api/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice: currentElevenLabsVoice, lang: currentVoiceLang })
    });
    if (!res.ok || res.status === 204) return false;
    const blob = await res.blob();
    if (!blob || blob.size === 0) return false;

    if (_elevenLabsAudio) { _elevenLabsAudio.pause(); _elevenLabsAudio = null; }
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    _elevenLabsAudio = audio;
    audio.onplay = () => setVoiceStatus('speaking');
    audio.onended = () => { URL.revokeObjectURL(url); if (onDone) onDone(); };
    audio.onerror = () => { URL.revokeObjectURL(url); if (onDone) onDone(); };
    await audio.play();
    return true;
  } catch (err) {
    return false;
  }
}

const voiceOverlay = document.getElementById('voiceOverlay');
const voiceOverlayStatus = document.getElementById('voiceOverlayStatus');

function setVoiceStatus(state) {
  if (!voiceOverlay) return;
  voiceOverlay.classList.remove('state-listening', 'state-thinking', 'state-speaking');
  if (state === 'listening') {
    voiceOverlay.classList.add('state-listening');
    if (voiceOverlayStatus) voiceOverlayStatus.textContent = 'Listening…';
  } else if (state === 'thinking') {
    voiceOverlay.classList.add('state-thinking');
    if (voiceOverlayStatus) voiceOverlayStatus.textContent = 'Thinking…';
  } else if (state === 'speaking') {
    voiceOverlay.classList.add('state-speaking');
    if (voiceOverlayStatus) voiceOverlayStatus.textContent = 'Speaking… (tap orb to interrupt)';
  }
}

(function () {
  const micBtn = document.getElementById('micBtn');
  const voiceOverlayClose = document.getElementById('voiceOverlayClose');
  if (!micBtn) return;

  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognitionCtor) {
    micBtn.style.display = 'none'; // browser doesn't support voice input
    return;
  }

  const recognition = new SpeechRecognitionCtor();
  recognition.lang = 'en-IN';
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  // Keep the mic's listening language in sync with whichever voice
  // language is selected, so Hindi/Marathi speech is recognized properly
  // instead of always being interpreted as English.
  function syncRecognitionLang() {
    if (currentVoiceLang === 'hi') recognition.lang = 'hi-IN';
    else if (currentVoiceLang === 'mr') recognition.lang = 'mr-IN';
    else recognition.lang = 'en-IN';
  }
  if (voiceLangSelect) voiceLangSelect.addEventListener('change', syncRecognitionLang);
  syncRecognitionLang();

  let noSpeechRetries = 0;

  function startListening() {
    setVoiceStatus('listening');
    syncRecognitionLang();
    try { recognition.start(); } catch (err) { /* already running, ignore */ }
  }

  function startVoiceMode() {
    voiceModeActive = true;
    noSpeechRetries = 0;
    if (voiceOverlay) voiceOverlay.classList.remove('hidden');
    micBtn.classList.add('mic-conversation');
    startListening();
  }

  function stopVoiceMode() {
    voiceModeActive = false;
    if (voiceOverlay) voiceOverlay.classList.add('hidden');
    micBtn.classList.remove('mic-conversation', 'mic-listening');
    stopAllSpeech();
    try { recognition.stop(); } catch (err) {}
    try { recognition.abort(); } catch (err) {}
  }

  recognition.addEventListener('result', (e) => {
    let transcript = '';
    let isFinal = false;
    for (let i = e.resultIndex; i < e.results.length; i++) {
      transcript += e.results[i][0].transcript;
      if (e.results[i].isFinal) isFinal = true;
    }
    if (userInput) userInput.value = transcript;
    // Show the live partial transcript in the "Listening..." overlay too.
    if (voiceOverlayStatus && !isFinal && transcript.trim()) {
      voiceOverlayStatus.textContent = `"${transcript.trim()}"`;
    }
    if (!isFinal) return; // wait for the final result before sending

    noSpeechRetries = 0;
    if (!transcript || !transcript.trim()) {
      if (voiceModeActive) startListening();
      return;
    }
    setVoiceStatus('thinking');
    sendMessage(transcript.trim(), () => {
      // Jawab bolna khatam hote hi, agar voice mode abhi bhi ON hai,
      // to khud-ba-khud wapas sunna shuru — jaise real voice assistant.
      if (voiceModeActive) startListening();
    });
  });

  recognition.addEventListener('error', (e) => {
    const fatal = e.error === 'not-allowed' || e.error === 'audio-capture' || e.error === 'service-not-allowed';
    if (fatal) {
      stopVoiceMode();
      return;
    }
    // "no-speech" jaisi choti si chup ke baad khud rukna nahi chahiye —
    // agar voice mode abhi bhi ON hai to thodi der baad dobara sunna shuru karo.
    // Kuch baar consecutively kuch na sune, to ek friendly hint dikhao
    // (chup-chaap retry karte rehna confusing lagta hai).
    if (e.error === 'no-speech') {
      noSpeechRetries += 1;
      if (noSpeechRetries >= 2 && voiceOverlayStatus) {
        voiceOverlayStatus.textContent = "Kuch sunayi nahi diya — thoda zor se boliye 🎤";
      }
    }
    if (voiceModeActive) {
      setTimeout(() => { if (voiceModeActive) startListening(); }, 400);
    }
  });

  micBtn.addEventListener('click', () => {
    if (voiceModeActive) {
      stopVoiceMode();
    } else {
      startVoiceMode();
    }
  });

  if (voiceOverlayClose) {
    voiceOverlayClose.addEventListener('click', stopVoiceMode);
  }

  // Tap the orb WHILE the assistant is speaking = "barge-in": stop it
  // talking immediately and start listening again, just like Alexa/Gemini.
  const voiceOverlayOrb = document.getElementById('voiceOverlayOrb');
  if (voiceOverlayOrb) {
    voiceOverlayOrb.addEventListener('click', (e) => {
      e.stopPropagation();
      if (voiceOverlay && voiceOverlay.classList.contains('state-speaking')) {
        stopAllSpeech();
        startListening();
      }
    });
  }

  if (voiceOverlay) {
    voiceOverlay.addEventListener('click', (e) => {
      if (e.target === voiceOverlay) stopVoiceMode();
    });
  }
})();

// =================================================================
// SIDEBAR (admin dashboard OR public site — whichever is present)
// =================================================================
(function () {
  const isAdmin = !!document.getElementById('adminSidebar');
  const sidebar = document.getElementById('adminSidebar') || document.getElementById('siteSidebar');
  const toggleBtn = document.getElementById('sidebarToggle');
  const overlay = document.getElementById('sidebarOverlay');
  if (!sidebar) return; // this page has no sidebar

  function openSidebar() {
    sidebar.classList.add('open');
    if (overlay) overlay.classList.add('show');
  }
  function closeSidebar() {
    sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('show');
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });
  }
  if (overlay) {
    overlay.addEventListener('click', closeSidebar);
  }

  const links = sidebar.querySelectorAll('.sidebar-link');
  const sections = Array.from(links)
    .map((link) => {
      const href = link.getAttribute('href') || '';
      return href.startsWith('#') ? document.querySelector(href) : null;
    })
    .filter(Boolean);

  if (isAdmin) {
    // Admin dashboard: show ONE section at a time (click a sidebar link to reveal
    // it, hide the rest) instead of one long scrolling page.
    function showSection(targetId) {
      sections.forEach((sec) => {
        if (sec.id === targetId) {
          sec.classList.add('admin-block-active');
          sec.classList.remove('admin-block-hidden');
        } else {
          sec.classList.remove('admin-block-active');
          sec.classList.add('admin-block-hidden');
        }
      });
      links.forEach((link) => {
        link.classList.toggle('active', link.getAttribute('href') === `#${targetId}`);
      });
    }

    links.forEach((link) => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = link.getAttribute('href').slice(1);
        showSection(targetId);
        closeSidebar();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        history.replaceState(null, '', `#${targetId}`);
      });
    });

    const initialId = (window.location.hash || '').slice(1);
    const initialSection = sections.find((s) => s.id === initialId) || sections[0];
    if (initialSection) showSection(initialSection.id);

  } else {
    // Public homepage: normal scroll-to-section behaviour, just close the
    // mobile sidebar after picking a section.
    links.forEach((link) => {
      link.addEventListener('click', closeSidebar);
    });

    if ('IntersectionObserver' in window && sections.length) {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const id = entry.target.getAttribute('id');
              links.forEach((link) => {
                link.classList.toggle('active', link.getAttribute('href') === `#${id}`);
              });
            }
          });
        },
        { rootMargin: '-20% 0px -70% 0px' }
      );
      sections.forEach((section) => observer.observe(section));
    }
  }
})();

// =================================================================
// TIMETABLE TABLE EDITOR (teacher/admin "My Class" section)
// =================================================================
(function () {
  const tbody = document.getElementById('ttEditRows');
  const addBtn = document.getElementById('ttAddRow');
  if (!tbody || !addBtn) return;

  function addRow() {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input type="text" name="tt_time" placeholder="e.g. 10:00-11:00"></td>
      <td><input type="text" name="tt_subject" placeholder="Subject"></td>
      <td><input type="text" name="tt_teacher" placeholder="Teacher"></td>
      <td><button type="button" class="btn-small btn-danger tt-remove-row">✕</button></td>
    `;
    tbody.appendChild(tr);
  }

  addBtn.addEventListener('click', addRow);

  tbody.addEventListener('click', (e) => {
    if (e.target.classList.contains('tt-remove-row')) {
      const rows = tbody.querySelectorAll('tr');
      if (rows.length > 1) {
        e.target.closest('tr').remove();
      } else {
        // keep at least one row, just clear it
        e.target.closest('tr').querySelectorAll('input').forEach((inp) => (inp.value = ''));
      }
    }
  });
})();

// =================================================================
// SUBJECTS PAGE — branch tab switcher (show one department at a time)
// =================================================================
(function () {
  const tabs = document.querySelectorAll('.branch-tab');
  if (!tabs.length) return;

  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const branch = tab.dataset.branch;
      document.querySelectorAll('.branch-tab').forEach((t) => t.classList.toggle('active', t === tab));
      document.querySelectorAll('.branch-panel').forEach((panel) => {
        panel.style.display = panel.dataset.branchPanel === branch ? '' : 'none';
      });
    });
  });
})();

// =================================================================
// GALLERY FILTER TABS (All / Campus / Events / Labs / Sports)
// =================================================================
(function () {
  const filterBtns = document.querySelectorAll('.gallery-filter-btn');
  const galleryItems = document.querySelectorAll('.gallery-item');
  if (!filterBtns.length) return;

  filterBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      filterBtns.forEach((b) => b.classList.toggle('active', b === btn));
      const filter = btn.dataset.filter;
      galleryItems.forEach((item) => {
        const show = filter === 'all' || item.dataset.category === filter;
        item.style.display = show ? '' : 'none';
      });
    });
  });
})();

// =================================================================
// TESTIMONIALS CAROUSEL (arrows + dots, 1 card at a time on mobile,
// 3 at a time on desktop)
// =================================================================
(function () {
  const track = document.querySelector('.testimonial-carousel-track');
  const wrap = document.querySelector('.testimonial-carousel-wrap');
  const dotsWrap = document.querySelector('.testimonial-dots');
  if (!track || !wrap) return;

  const cards = Array.from(track.children);
  if (!cards.length) return;

  const perView = () => (window.innerWidth <= 900 ? 1 : 3);
  let index = 0;

  function totalPages() {
    return Math.max(1, Math.ceil(cards.length / perView()));
  }

  function renderDots() {
    if (!dotsWrap) return;
    dotsWrap.innerHTML = '';
    for (let i = 0; i < totalPages(); i++) {
      const dot = document.createElement('span');
      if (i === index) dot.classList.add('active');
      dot.addEventListener('click', () => goTo(i));
      dotsWrap.appendChild(dot);
    }
  }

  function goTo(page) {
    index = ((page % totalPages()) + totalPages()) % totalPages();
    const cardWidth = cards[0].getBoundingClientRect().width + 20; // + gap
    track.style.transform = `translateX(-${index * perView() * cardWidth}px)`;
    renderDots();
  }

  const leftArrow = wrap.querySelector('.testimonial-arrow-left');
  const rightArrow = wrap.querySelector('.testimonial-arrow-right');
  if (leftArrow) leftArrow.addEventListener('click', () => goTo(index - 1));
  if (rightArrow) rightArrow.addEventListener('click', () => goTo(index + 1));

  track.style.transition = 'transform 0.4s ease';
  renderDots();
  window.addEventListener('resize', () => goTo(0));

  // Gentle auto-advance every 6 seconds
  setInterval(() => goTo(index + 1), 6000);
})();
