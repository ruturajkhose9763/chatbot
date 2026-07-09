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

function addMessage(text, sender) {
  const msg = document.createElement('div');
  msg.className = `msg ${sender}`;
  const avatarContent = sender === 'user' ? '🧑' : '<img src="/static/img/college-logo.jpg" alt="Bot">';
  msg.innerHTML = `
    <div class="avatar">${avatarContent}</div>
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
    <div class="avatar"><img src="/static/img/college-logo.jpg" alt="Bot"></div>
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
      body: JSON.stringify({ message: text })
    });
    const data = await res.json();
    await new Promise(r => setTimeout(r, 150));
    typingEl.remove();
    addMessage(data.reply, 'bot');
    renderSuggestions(data.suggestions);
    await speakText(data.reply, onSpokenEnd);
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
      if (entry.target.classList.contains('stat-card')) {
        const counter = entry.target.querySelector('.stat-num[data-target]');
        if (counter && !counter.dataset.animated) {
          counter.dataset.animated = '1';
          animateCounter(counter);
        }
      }
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.15 });

revealEls.forEach((el) => observer.observe(el));

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
    _cachedVoice = pickBestVoice(currentVoiceLang);
    window.speechSynthesis.cancel();
  });
}

// ---------- Pick the best-sounding free voice already installed in the browser ----------
let _cachedVoice = null;
function pickBestVoice(lang) {
  if (!('speechSynthesis' in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  if (!voices.length) return null;

  if (lang === 'hi') {
    return (
      voices.find((v) => v.name.includes('Google हिन्दी') || v.name.includes('Google हिंदी')) ||
      voices.find((v) => v.lang === 'hi-IN') ||
      voices.find((v) => v.lang && v.lang.startsWith('hi')) ||
      pickBestVoice('en')
    );
  }
  if (lang === 'mr') {
    return (
      voices.find((v) => v.lang === 'mr-IN') ||
      voices.find((v) => v.lang && v.lang.startsWith('mr')) ||
      pickBestVoice('en')
    );
  }

  // Known high-quality "natural" English voices, best first.
  const preferredNames = [
    'Google UK English Female', 'Google US English',
    'Microsoft Heera Online (Natural) - English (India)',
    'Microsoft Heera - English (India)', 'Microsoft Ravi - English (India)',
    'Samantha', 'Microsoft Zira - English (United States)',
  ];
  for (const name of preferredNames) {
    const v = voices.find((v) => v.name === name);
    if (v) return v;
  }
  // Fallback: any Indian-English / Hindi voice, then any Google voice, then any English voice.
  return (
    voices.find((v) => v.lang === 'en-IN') ||
    voices.find((v) => v.lang === 'hi-IN') ||
    voices.find((v) => v.name.startsWith('Google') && v.lang.startsWith('en')) ||
    voices.find((v) => v.lang && v.lang.startsWith('en')) ||
    voices[0]
  );
}
if ('speechSynthesis' in window) {
  window.speechSynthesis.onvoiceschanged = () => { _cachedVoice = pickBestVoice(currentVoiceLang); };
  _cachedVoice = pickBestVoice(currentVoiceLang);
}

async function speakText(text, onDone) {
  if (!voiceModeActive || !('speechSynthesis' in window)) {
    if (onDone) onDone();
    return;
  }
  let plain = text.replace(/[*_#`]/g, '').replace(/\s+/g, ' ').trim();

  // If a non-English voice is selected, translate the reply first so the
  // spoken output actually matches the chosen language. If translation
  // fails for any reason (no internet, no API key set up), it just speaks
  // the original English text instead — never silently breaks.
  if (currentVoiceLang !== 'en') {
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

  const utterance = new SpeechSynthesisUtterance(plain);
  utterance.rate = 0.98;
  utterance.pitch = 1.02;
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
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  function startListening() {
    setVoiceStatus('listening');
    try { recognition.start(); } catch (err) { /* already running, ignore */ }
  }

  function startVoiceMode() {
    voiceModeActive = true;
    if (voiceOverlay) voiceOverlay.classList.remove('hidden');
    micBtn.classList.add('mic-conversation');
    startListening();
  }

  function stopVoiceMode() {
    voiceModeActive = false;
    if (voiceOverlay) voiceOverlay.classList.add('hidden');
    micBtn.classList.remove('mic-conversation', 'mic-listening');
    window.speechSynthesis.cancel();
    try { recognition.stop(); } catch (err) {}
    try { recognition.abort(); } catch (err) {}
  }

  recognition.addEventListener('result', (e) => {
    const transcript = e.results[0][0].transcript;
    if (userInput) userInput.value = transcript;
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
        window.speechSynthesis.cancel();
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
