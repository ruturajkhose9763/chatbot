# College Website — Full Version (Bug-fixed + Multi-Role + Timetable)

## ⚠️ यह पूरा नया folder है (v3) — पुराने folder से पूरी तरह बदलें
यह पिछले सभी features + नए बदलाव मिलाकर बनाया गया **पूरा नया project** है। **अपनी अपलोड की हुई असली Photos** को `static/uploads/` फोल्डर में वापस डालना न भूलें (यह folder खाली है, आपकी पुरानी photos इसमें copy कर लें)।

## Setup
```
pip install -r requirements.txt
python app.py
```
Browser: **http://127.0.0.1:5000**

---

## 🐛 जो Bug Fix हुआ
पहले चैटबॉट पूछे गए से ज़्यादा जानकारी दे देता था। अब:
- "**first year fees** kitni hai" → सिर्फ First Year की fees
- "**direct second year** fees" → सिर्फ उसी की fees
- "**eligibility** kya hai" → सिर्फ eligibility, बाकी admission की जानकारी नहीं
- "**how to apply**" → सिर्फ apply करने का तरीका
- अगर subtopic नहीं बताया (जैसे सिर्फ "fees kitni hai"), तो पूरी जानकारी मिलेगी — यह सही व्यवहार है

## 🔐 3-तरह के Login (एक ही Login Page से, अपने आप सही Dashboard खुलता है)

| Role | Username | Password | क्या कर सकते हैं |
|---|---|---|---|
| **Main Admin** | `Ruturaj` | `ruturaj@9763` | सब कुछ — Staff/Class Rep accounts बनाना, College Info edit करना, News/Events/Gallery सब |
| **Staff (Teacher)** | Admin बनाकर देगा | Admin सेट करेगा | अपनी Profile, News/Events/Testimonials/Gallery/Downloads जोड़ना |
| **Class Representative** | Admin बनाकर देगा | Admin सेट करेगा | सिर्फ अपनी Class का Timetable + Notices manage करना |

⚠️ **Password बदलना न भूलें** असली इस्तेमाल से पहले।

### नए Staff/Class Rep Account कैसे बनाएं
1. Ruturaj से लॉगिन करें (`/admin/login`)
2. "Manage Staff Accounts" सेक्शन में जाकर फॉर्म भरें
3. Staff के लिए: नाम, username, password, department, subject
4. Class Rep के लिए: नाम, username, password, और dropdown से class चुनें

## 🕐 Classroom Timetable System (नया)
- हर branch के 1st Year और Direct 2nd Year के लिए अलग "class" पहले से बनी है (कुल 8 classes)
- Class Representative लॉगिन करके अपनी class का timetable लिख सकता है और notices डाल सकता है
- चैटबॉट से पूछें: *"computer first year timetable"* → तुरंत जवाब मिलेगा

## 🌟 अन्य Features
Multilingual chatbot, Branch-specific answers, Admission Contact info, Chatbot follow-up सुझाव, Search bar, Dark/Light theme toggle, Animated counters, Gallery Lightbox, Testimonials, Downloads, Campus Video, WhatsApp button, Scroll animations, Admission Form verification, Admin से College Info edit, Profile Photo (DP), Login page animation।

## प्रोजेक्ट स्ट्रक्चर
```
college-website-v3/
├── app.py
├── college_info.json
├── content_data.json
├── classroom_data.json
├── staff_accounts.json
├── admissions_data.json
├── requirements.txt
├── templates/ (index.html, login.html, admin.html)
└── static/ (style.css, script.js, uploads/)
```

## Viva Points
- Role-Based Access Control (3 roles, decorator-protected routes)
- Password hashing (werkzeug.security)
- Precise NLU sub-topic detection
- Automated testing including security checks
