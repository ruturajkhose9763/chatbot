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
// VOICE INPUT (mic) & VOICE OUTPUT (speech synthesis)
// =================================================================
let voiceOutputEnabled = false;

function speakText(text) {
  if (!voiceOutputEnabled || !('speechSynthesis' in window)) return;
  const plain = text.replace(/[*_#`]/g, '').replace(/\s+/g, ' ').trim();
  const utterance = new SpeechSynthesisUtterance(plain);
  utterance.rate = 0.95;
  window.speechSynthesis.cancel(); // stop any previous speech first
  window.speechSynthesis.speak(utterance);
}

(function () {
  const voiceToggle = document.getElementById('voiceOutputToggle');
  if (voiceToggle) {
    voiceToggle.addEventListener('click', () => {
      voiceOutputEnabled = !voiceOutputEnabled;
      voiceToggle.textContent = voiceOutputEnabled ? '🔊' : '🔇';
      voiceToggle.title = voiceOutputEnabled ? 'Voice replies ON — click to mute' : 'Turn on voice replies';
      if (!voiceOutputEnabled) window.speechSynthesis.cancel();
    });
  }

  const micBtn = document.getElementById('micBtn');
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

  recognition.addEventListener('result', (e) => {
    const transcript = e.results[0][0].transcript;
    if (userInput) userInput.value = transcript;
  });
  recognition.addEventListener('end', () => micBtn.classList.remove('mic-listening'));
  recognition.addEventListener('error', () => micBtn.classList.remove('mic-listening'));

  micBtn.addEventListener('click', () => {
    micBtn.classList.add('mic-listening');
    recognition.start();
  });
})();
