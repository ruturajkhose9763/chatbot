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

const ROBOT_AVATAR_SVG = `<svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">
  <line x1="60" y1="8" x2="60" y2="20" stroke="#B9C6D6" stroke-width="4" stroke-linecap="round"/>
  <circle cx="60" cy="6" r="5" fill="#4DC9FF"/>
  <rect x="16" y="20" width="88" height="56" rx="26" fill="#F4F7FB" stroke="#D7E1EC" stroke-width="2"/>
  <rect x="8" y="40" width="10" height="18" rx="5" fill="#E3EAF2"/>
  <rect x="102" y="40" width="10" height="18" rx="5" fill="#E3EAF2"/>
  <rect x="32" y="34" width="56" height="32" rx="16" fill="#0F1B2D"/>
  <circle cx="49" cy="50" r="6.5" fill="#4DC9FF"/>
  <circle cx="71" cy="50" r="6.5" fill="#4DC9FF"/>
  <path d="M48 68 Q60 75 72 68" stroke="#AEBBCC" stroke-width="3" fill="none" stroke-linecap="round"/>
  <rect x="24" y="80" width="72" height="36" rx="18" fill="#F4F7FB" stroke="#D7E1EC" stroke-width="2"/>
  <circle cx="60" cy="98" r="7" fill="#4DC9FF"/>
</svg>`;

function currentTimeLabel() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function addMessage(text, sender) {
  const msg = document.createElement('div');
  msg.className = `msg ${sender}`;
  const avatarContent = sender === 'user' ? '🧑' : ROBOT_AVATAR_SVG;
  const avatarClass = sender === 'user' ? 'avatar' : 'avatar robot-avatar';
  const checkmark = sender === 'user' ? ' ✓✓' : '';
  msg.innerHTML = `
    <div class="${avatarClass}">${avatarContent}</div>
    <div class="bubble-col">
      <div class="bubble">${escapeHtml(text)}</div>
      <span class="msg-time">${currentTimeLabel()}${checkmark}</span>
    </div>
  `;
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return msg;
}

function addTyping() {
  const msg = document.createElement('div');
  msg.className = 'msg bot';
  msg.innerHTML = `
    <div class="avatar robot-avatar">${ROBOT_AVATAR_SVG}</div>
    <div class="bubble-col"><div class="bubble typing"><span></span><span></span><span></span></div></div>
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

async function sendMessage(text) {
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
    speakText(data.reply);
  } catch (err) {
    typingEl.remove();
    addMessage('Something went wrong. Please try again.', 'bot');
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
// VOICE MODE — fullscreen overlay assistant.
// Tapping the mic opens an overlay with the robot mascot, shows
// Listening / Thinking / Speaking status, and speaks replies aloud.
// Replies are only spoken while this overlay mode is active.
// =================================================================
let voiceModeActive = false;
let voiceOutputEnabled = false;

const voiceOverlay = document.getElementById('voiceOverlay');
const voiceOverlayStatus = document.getElementById('voiceOverlayStatus');
const voiceOverlaySubtext = document.getElementById('voiceOverlaySubtext');
const voiceOverlayClose = document.getElementById('voiceOverlayClose');
const voiceOverlayMic = document.getElementById('voiceOverlayMic');
const voiceOverlayMute = document.getElementById('voiceOverlayMute');
const voiceOverlayOrb = document.getElementById('voiceOverlayOrb');

function setVoiceStatus(state) {
  if (!voiceOverlay) return;
  voiceOverlay.classList.remove('state-listening', 'state-thinking', 'state-speaking', 'state-idle');
  voiceOverlay.classList.add(`state-${state}`);
  const copy = {
    listening: ['Listening…', 'Speak now, I am listening'],
    thinking: ['Thinking…', 'Let me find that for you'],
    speaking: ['Speaking…', 'Tap the robot to interrupt'],
    idle: ['Ready', 'Tap the mic to speak again'],
  }[state] || ['', ''];
  if (voiceOverlayStatus) voiceOverlayStatus.textContent = copy[0];
  if (voiceOverlaySubtext) voiceOverlaySubtext.textContent = copy[1];
}

function speakText(text) {
  if (!voiceModeActive && !voiceOutputEnabled) return;
  if (!('speechSynthesis' in window)) return;
  const plain = text.replace(/[*_#`]/g, '').replace(/\s+/g, ' ').trim();
  if (!plain) return;
  const utterance = new SpeechSynthesisUtterance(plain);
  utterance.rate = 0.98;
  utterance.pitch = 1.02;
  utterance.onstart = () => setVoiceStatus('speaking');
  utterance.onend = () => {
    if (voiceModeActive) {
      setVoiceStatus('idle');
      startListening();
    }
  };
  utterance.onerror = () => { if (voiceModeActive) setVoiceStatus('idle'); };
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

(function () {
  const micBtn = document.getElementById('micBtn');
  const voiceToggle = document.getElementById('voiceOutputToggle');

  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;
  const speechSupported = !!SpeechRecognitionCtor;
  let recognition = null;
  if (speechSupported) {
    recognition = new SpeechRecognitionCtor();
    recognition.lang = 'en-IN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.addEventListener('result', (e) => {
      const transcript = e.results[0][0].transcript;
      if (userInput) userInput.value = transcript;
      setVoiceStatus('thinking');
      sendMessage(transcript.trim());
    });
    recognition.addEventListener('start', () => setVoiceStatus('listening'));
    recognition.addEventListener('end', () => {
      if (micBtn) micBtn.classList.remove('mic-listening');
    });
    recognition.addEventListener('error', (e) => {
      if (micBtn) micBtn.classList.remove('mic-listening');
      // A brief silence shouldn't end the whole conversation — try again.
      if (voiceModeActive && e.error === 'no-speech') {
        setTimeout(startListening, 300);
      } else if (voiceModeActive) {
        setVoiceStatus('idle');
      }
    });
  }

  function startListening() {
    if (!recognition || !voiceModeActive) return;
    window.speechSynthesis.cancel();
    if (micBtn) micBtn.classList.add('mic-listening');
    try { recognition.start(); } catch (e) { /* already running — ignore */ }
  }
  window.startListening = startListening; // used by speakText's onend callback

  function openVoiceOverlay() {
    if (!voiceOverlay) return;
    if (!speechSupported) {
      alert("Your browser doesn't support voice input. Try Chrome or Edge.");
      return;
    }
    voiceModeActive = true;
    voiceOverlay.classList.remove('hidden');
    startListening();
  }

  function closeVoiceOverlay() {
    voiceModeActive = false;
    window.speechSynthesis.cancel();
    if (recognition) { try { recognition.stop(); } catch (e) {} }
    if (voiceOverlay) voiceOverlay.classList.add('hidden');
  }

  if (micBtn) {
    micBtn.addEventListener('click', () => {
      if (voiceModeActive) { closeVoiceOverlay(); } else { openVoiceOverlay(); }
    });
  }
  if (voiceOverlayClose) voiceOverlayClose.addEventListener('click', closeVoiceOverlay);
  if (voiceOverlayMic) {
    voiceOverlayMic.addEventListener('click', () => {
      if (voiceOverlay.classList.contains('state-speaking')) {
        window.speechSynthesis.cancel();
        startListening();
      } else {
        closeVoiceOverlay();
      }
    });
  }
  // Tap the robot itself while it's speaking = interrupt, like Alexa/Gemini.
  if (voiceOverlayOrb) {
    voiceOverlayOrb.addEventListener('click', () => {
      if (voiceOverlay.classList.contains('state-speaking')) {
        window.speechSynthesis.cancel();
        startListening();
      }
    });
  }
  if (voiceOverlayMute) {
    voiceOverlayMute.addEventListener('click', () => {
      voiceOutputEnabled = !voiceOutputEnabled;
      voiceOverlayMute.textContent = voiceOutputEnabled ? '🔊' : '🔇';
      if (!voiceOutputEnabled) window.speechSynthesis.cancel();
    });
  }
  if (voiceToggle) {
    voiceToggle.addEventListener('click', () => {
      voiceOutputEnabled = !voiceOutputEnabled;
      voiceToggle.textContent = voiceOutputEnabled ? '🔊' : '🔇';
      voiceToggle.title = voiceOutputEnabled ? 'Voice replies ON — click to mute' : 'Turn on voice replies';
      if (!voiceOutputEnabled) window.speechSynthesis.cancel();
    });
  }
  if (!speechSupported && micBtn) micBtn.style.display = 'none';
})();

// Header icons: restart conversation, and a small options menu.
(function () {
  const refreshBtn = document.getElementById('refreshChatBtn');
  const menuBtn = document.getElementById('menuBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      if (!confirm('Start a new conversation? This will clear the chat.')) return;
      chatWindow.innerHTML = '';
      addMessage("Hello again! 👋 What would you like to know about the college?", 'bot');
      renderSuggestions([]);
    });
  }
  if (menuBtn) {
    menuBtn.addEventListener('click', () => {
      alert('College AI Assistant\nAnswers in English, Hindi & Marathi.\nTap the mic for a hands-free voice conversation.');
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
