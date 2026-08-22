// Client-side Firebase Phone Auth. Only runs when the page sets
// window.FIREBASE_ENABLED = true (i.e. the admin has configured
// Firebase env vars on the server). Otherwise the page falls back to
// the older server-driven Twilio OTP flow untouched.
(function () {
  if (!window.FIREBASE_ENABLED || !window.FIREBASE_CONFIG || !window.firebase) return;

  firebase.initializeApp(window.FIREBASE_CONFIG);

  const otpForm = document.getElementById('otpForm');
  const hidden = document.getElementById('otpHidden');
  const sendStatus = document.getElementById('otpSendStatus');
  const submitBtn = otpForm ? otpForm.querySelector('.login-v2-submit') : null;
  let confirmationResult = null;

  function setStatus(text) {
    if (sendStatus) sendStatus.textContent = text;
  }

  function fullPhone() {
    const raw = (window.FIREBASE_MOBILE || '').replace(/\D/g, '');
    const last10 = raw.slice(-10);
    return '+91' + last10; // Indian numbers — adjust here if the college is outside India.
  }

  function ensureRecaptcha() {
    if (window.__recaptchaVerifier) return window.__recaptchaVerifier;
    window.__recaptchaVerifier = new firebase.auth.RecaptchaVerifier('recaptcha-container', { size: 'invisible' });
    return window.__recaptchaVerifier;
  }

  function sendOtp() {
    setStatus('Sending verification code…');
    if (submitBtn) submitBtn.disabled = true;
    firebase.auth().signInWithPhoneNumber(fullPhone(), ensureRecaptcha())
      .then(function (result) {
        confirmationResult = result;
        setStatus('Code sent to ' + fullPhone());
        if (submitBtn) submitBtn.disabled = false;
      })
      .catch(function (err) {
        setStatus('Could not send code — ' + (err && err.message ? err.message : 'please try Resend.'));
        if (submitBtn) submitBtn.disabled = false;
      });
  }

  // Auto-send as soon as the page loads, so the OTP is already on its
  // way by the time the person looks at the screen (same as before).
  sendOtp();
  window.__resendFirebaseOtp = sendOtp;

  if (otpForm) {
    otpForm.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!confirmationResult) {
        setStatus('Code not sent yet — please wait a moment and try again.');
        return;
      }
      const otp = hidden.value;
      if (otp.length < 6) return;
      if (submitBtn) submitBtn.disabled = true;
      confirmationResult.confirm(otp)
        .then(function (result) { return result.user.getIdToken(); })
        .then(function (idToken) {
          return fetch(window.FIREBASE_VERIFY_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(Object.assign({ id_token: idToken }, window.FIREBASE_VERIFY_PAYLOAD)),
          });
        })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            window.location.href = window.FIREBASE_SUCCESS_REDIRECT;
          } else {
            setStatus(data.error || 'Verification failed. Please try again.');
            if (submitBtn) submitBtn.disabled = false;
          }
        })
        .catch(function () {
          setStatus('Invalid or expired code — please try again.');
          if (submitBtn) submitBtn.disabled = false;
        });
    });
  }
})();
