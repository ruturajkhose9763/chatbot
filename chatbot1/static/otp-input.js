// Animated OTP box input — auto-advance between boxes, paste support,
// and a resend countdown timer. Used by student_verify.html and
// teacher_verify.html (both share the same box IDs/classes).
(function () {
  const boxRow = document.getElementById('otpBoxRow');
  const hidden = document.getElementById('otpHidden');
  const form = document.getElementById('otpForm');
  if (!boxRow || !hidden || !form) return;

  const boxes = Array.from(boxRow.querySelectorAll('.otp-box'));

  function syncHidden() {
    hidden.value = boxes.map((b) => b.value).join('');
  }

  boxes.forEach((box, i) => {
    box.addEventListener('input', () => {
      box.value = box.value.replace(/[^0-9]/g, '').slice(0, 1);
      box.classList.toggle('filled', !!box.value);
      if (box.value && boxes[i + 1]) boxes[i + 1].focus();
      syncHidden();
    });

    box.addEventListener('keydown', (e) => {
      if (e.key === 'Backspace' && !box.value && boxes[i - 1]) {
        boxes[i - 1].focus();
      }
    });

    box.addEventListener('paste', (e) => {
      e.preventDefault();
      const digits = (e.clipboardData.getData('text') || '').replace(/[^0-9]/g, '').slice(0, boxes.length);
      digits.split('').forEach((d, idx) => {
        if (boxes[idx]) {
          boxes[idx].value = d;
          boxes[idx].classList.add('filled');
        }
      });
      syncHidden();
      const next = boxes[Math.min(digits.length, boxes.length - 1)];
      if (next) next.focus();
    });
  });

  form.addEventListener('submit', (e) => {
    syncHidden();
    if (hidden.value.length < boxes.length) {
      e.preventDefault();
      boxes.forEach((b) => {
        if (!b.value) b.classList.add('otp-error');
      });
      setTimeout(() => boxes.forEach((b) => b.classList.remove('otp-error')), 450);
    }
  });

  if (boxes[0]) boxes[0].focus();

  // Resend countdown
  const timerWrap = document.getElementById('otpTimerWrap');
  const timerEl = document.getElementById('otpTimer');
  const resendBtn = document.getElementById('otpResendBtn');
  const resendForm = document.getElementById('otpResendForm');
  if (timerEl && resendBtn && resendForm) {
    let seconds = 30;
    const tick = setInterval(() => {
      seconds -= 1;
      timerEl.textContent = seconds;
      if (seconds <= 0) {
        clearInterval(tick);
        if (timerWrap) timerWrap.style.display = 'none';
        resendBtn.style.display = 'inline';
      }
    }, 1000);

    resendBtn.addEventListener('click', () => {
      resendBtn.disabled = true;
      resendBtn.textContent = 'Sending…';
      if (window.FIREBASE_ENABLED && window.__resendFirebaseOtp) {
        window.__resendFirebaseOtp();
        setTimeout(() => { resendBtn.disabled = false; resendBtn.textContent = '↻ Resend OTP'; }, 2000);
      } else {
        resendForm.submit();
      }
    });
  }
})();
