"""
College Website + Smart Offline Chatbot (Full Version 3)
-----------------------------------------------------------
- No external AI API. Fully offline "brain".
- FIX: chatbot now answers only the specific sub-topic asked (e.g. "eligibility"
  alone no longer dumps the whole admission process; "first year fees" alone
  no longer also shows direct-second-year fees).
- Two account roles:
    main_admin  - full control (staff accounts, college info, everything). Can set a
                  custom designation (e.g. "Principal", "HOD") shown instead of "Admin".
    staff       - teacher account (profile + news/events/gallery/testimonials). A teacher
                  can optionally be assigned a class (class_key) to manage that class's
                  timetable, notices, subjects/teacher mapping, and student attendance.
"""

import json
import os
import re
import random
import secrets
import difflib
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, session, flash, has_request_context, Response
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader
from pymongo import MongoClient

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
if not os.environ.get("SECRET_KEY"):
    print("WARNING: SECRET_KEY environment variable not set. Using a random key "
          "for this run only -- all users will be logged out on every restart. "
          "Set SECRET_KEY in Render's environment variables for production.")

# Used for SEO: canonical links, sitemap.xml, and Open Graph/Twitter image
# URLs need the FULL site address. Set SITE_URL in Render's environment
# variables to your real domain once you have one (e.g. https://sedcoe.ac.in
# or https://your-app.onrender.com) — until then this placeholder is used.
SITE_URL = (os.environ.get("SITE_URL") or "https://sedcoe.onrender.com").rstrip("/")

# ---------------------------------------------------------------
# CLOUDINARY CONFIG (free image hosting - photos survive server restarts)
# ---------------------------------------------------------------
cloudinary.config(
    cloud_name="dg3soehs",
    api_key="164175958813331",
    api_secret="o-DmYTursg4gT5mbl_pjqU9s5AQ",
    secure=True
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
DP_FOLDER = os.path.join(UPLOAD_FOLDER, "dp")
DOWNLOADS_FOLDER = os.path.join(UPLOAD_FOLDER, "downloads")
STUDY_MATERIALS_FOLDER = os.path.join(UPLOAD_FOLDER, "study_materials")
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, "videos")
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp"}
ALLOWED_DOC_EXT = {"pdf"}
ALLOWED_MATERIAL_EXT = {"pdf", "ppt", "pptx", "doc", "docx"}
ALLOWED_VIDEO_EXT = {"mp4", "webm", "mov"}

COLLEGE_INFO_PATH = os.path.join(BASE_DIR, "college_info.json")
CONTENT_DATA_PATH = os.path.join(BASE_DIR, "content_data.json")
ADMISSIONS_DATA_PATH = os.path.join(BASE_DIR, "admissions_data.json")
STAFF_ACCOUNTS_PATH = os.path.join(BASE_DIR, "staff_accounts.json")
CLASSROOM_DATA_PATH = os.path.join(BASE_DIR, "classroom_data.json")
ANALYTICS_PATH = os.path.join(BASE_DIR, "chat_analytics.json")
CUSTOM_QA_PATH = os.path.join(BASE_DIR, "custom_qa.json")
SUBJECTS_DATA_PATH = os.path.join(BASE_DIR, "subjects_data.json")
STUDY_MATERIALS_PATH = os.path.join(BASE_DIR, "study_materials.json")
ATTENDANCE_DATA_PATH = os.path.join(BASE_DIR, "attendance_data.json")

# ---------------------------------------------------------------
# MONGODB (persistent storage - data survives every redeploy)
# Falls back to plain local JSON files automatically if MONGO_URI
# is not set (e.g. while testing on a laptop), so nothing breaks.
# ---------------------------------------------------------------
MONGO_URI = os.environ.get("MONGO_URI")
_mongo_collection = None
if MONGO_URI:
    try:
        _mongo_client = MongoClient(MONGO_URI)
        _mongo_db = _mongo_client["college_website"]
        _mongo_collection = _mongo_db["app_data"]
    except Exception as e:
        print("MongoDB connection failed, falling back to local JSON files:", e)
        _mongo_collection = None


def _mongo_key(path):
    """Turn a file path like '.../custom_qa.json' into a Mongo doc key 'custom_qa'."""
    return os.path.splitext(os.path.basename(path))[0]


def data_exists(path):
    """True if this data already exists somewhere (Mongo doc, or local file)."""
    if _mongo_collection is not None:
        if _mongo_collection.find_one({"_id": _mongo_key(path)}) is not None:
            return True
        return os.path.exists(path)
    return os.path.exists(path)


def load_json(path):
    if _mongo_collection is not None:
        key = _mongo_key(path)
        doc = _mongo_collection.find_one({"_id": key})
        if doc is not None:
            return doc["data"]
        # Not in Mongo yet: seed it once from the local JSON file that
        # ships in the repo, so existing college info/etc. isn't lost.
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            _mongo_collection.update_one(
                {"_id": key}, {"$set": {"data": data}}, upsert=True
            )
            return data
        raise FileNotFoundError(path)
    # No MONGO_URI configured (e.g. local dev) - behave exactly as before.
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    if _mongo_collection is not None:
        key = _mongo_key(path)
        _mongo_collection.update_one(
            {"_id": key}, {"$set": {"data": data}}, upsert=True
        )
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_analytics():
    if not data_exists(ANALYTICS_PATH):
        save_json(ANALYTICS_PATH, {"topic_counts": {}, "recent_questions": [], "total_questions": 0})
    return load_json(ANALYTICS_PATH)


def log_chat_question(intent_name, message):
    try:
        data = get_analytics()
        topic = intent_name or "unmatched"
        data["topic_counts"][topic] = data["topic_counts"].get(topic, 0) + 1
        data["total_questions"] = data.get("total_questions", 0) + 1
        data["recent_questions"].insert(0, {
            "text": message[:200],
            "topic": topic,
            "time": datetime.now().strftime("%d %b %Y, %I:%M %p")
        })
        data["recent_questions"] = data["recent_questions"][:50]  # keep last 50 only
        save_json(ANALYTICS_PATH, data)
    except Exception:
        pass  # analytics logging should never break the chatbot


def get_custom_qa():
    """Admin-taught Q&A pairs — created from questions the chatbot could
    not originally answer. Checked as a second-tier fallback (after the
    built-in intents, before the AI hybrid backup)."""
    if not data_exists(CUSTOM_QA_PATH):
        save_json(CUSTOM_QA_PATH, {"items": []})
    return load_json(CUSTOM_QA_PATH)


def save_custom_qa(data):
    save_json(CUSTOM_QA_PATH, data)


def get_data():
    return load_json(COLLEGE_INFO_PATH)


def save_data(d):
    save_json(COLLEGE_INFO_PATH, d)


def get_content():
    return load_json(CONTENT_DATA_PATH)


def get_admissions():
    if not data_exists(ADMISSIONS_DATA_PATH):
        save_json(ADMISSIONS_DATA_PATH, {"submissions": []})
    return load_json(ADMISSIONS_DATA_PATH)


def get_accounts():
    return load_json(STAFF_ACCOUNTS_PATH)


def find_account(username):
    accounts = get_accounts()["accounts"]
    return next((a for a in accounts if a["username"].lower() == username.lower()), None)


def get_classrooms():
    return load_json(CLASSROOM_DATA_PATH)


def get_subjects():
    return load_json(SUBJECTS_DATA_PATH)


def save_subjects(data):
    save_json(SUBJECTS_DATA_PATH, data)


def get_study_materials():
    if not data_exists(STUDY_MATERIALS_PATH):
        return {"items": []}
    return load_json(STUDY_MATERIALS_PATH)


def save_study_materials(data):
    save_json(STUDY_MATERIALS_PATH, data)


def get_attendance():
    if not data_exists(ATTENDANCE_DATA_PATH):
        save_json(ATTENDANCE_DATA_PATH, {"classes": {}})
    return load_json(ATTENDANCE_DATA_PATH)


def save_attendance(data):
    save_json(ATTENDANCE_DATA_PATH, data)


def allowed_image(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT


def allowed_doc(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_DOC_EXT


def allowed_video(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_VIDEO_EXT


# =================================================================
# CHATBOT ENGINE (rule-based, multilingual, branch-aware, PRECISE)
# =================================================================

BRANCH_ALIASES = {
    "computer": ["computer", "comp", "cse", "cs branch", "संगणक", "कंप्यूटर"],
    "civil": ["civil", "सिव्हिल", "सिविल"],
    "mechanical": ["mechanical", "mech", "मेकॅनिकल", "मैकेनिकल"],
    "electrical": ["electrical", "eee", "इलेक्ट्रिकल"],
}

YEAR_ALIASES = {
    "first": ["1st year", "first year", "pahile varsh", "pahla saal", "पहिले वर्ष", "प्रथम वर्ष"],
    "second": ["2nd year", "second year", "direct second", "dsy", "lateral", "द्वितीय वर्ष"],
    "third": ["3rd year", "third year", "tisra saal", "tisre varsh", "तिसरे वर्ष", "तृतीय वर्ष"],
}

CONTACT_WORDS = ["contact", "number", "mobile", "phone", "sir ka number", "sir number",
                 "नंबर", "संपर्क", "फोन"]
ADMISSION_WORDS = ["admission", "admison", "प्रवेश", "एडमिशन", "apply"]

SCHOLARSHIP_WORDS = ["scholarship", "scholarships", "chatravrutti", "chatrawrutti", "mahadbt",
                      "freeship", "tfws", "shishyavrutti", "शिष्यवृत्ती", "छात्रवृत्ति", "स्कॉलरशिप"]
HOSTEL_WORDS = ["hostel", "vasatigruh", "वसतिगृह", "हॉस्टल"]
EXAM_SCHEDULE_WORDS = ["exam schedule", "exam timetable", "exam date", "exam dates", "msbte exam",
                       "pariksha", "परीक्षा वेळापत्रक", "परीक्षेचे वेळापत्रक", "परीक्षा कधी"]


def detect_branch(message):
    msg = message.lower()
    for branch, aliases in BRANCH_ALIASES.items():
        for alias in aliases:
            if alias in msg:
                return branch
    return None


def detect_year(message):
    msg = message.lower()
    for year, aliases in YEAR_ALIASES.items():
        for alias in aliases:
            if alias in msg:
                return year
    return None


def mentions_any(message, words):
    msg = message.lower()
    return any(w in msg for w in words)


# ---------- Formatter functions (each answers ONLY its specific sub-topic) ----------

def fmt_admission_contact(d, branch=None, message=""):
    contacts = d.get("admission_contacts", [])
    if not contacts:
        return "Sorry, I don't have admission contact details right now. Please call the college office directly."
    branch_txt = f" for {branch.title()} Engineering" if branch else ""
    lines = [f"Sure! Here's who you can contact for admission{branch_txt} 😊"]
    for c in contacts:
        lines.append(f"• {c['name']}: {c['phone']}")
    return "\n".join(lines)


def fmt_courses(d, branch=None, message=""):
    courses = d.get("courses_offered", [])
    if branch:
        courses = [c for c in courses if branch in c["name"].lower()]
        if not courses:
            return f"Hmm, I couldn't find a '{branch}' branch. We offer Computer, Civil, Mechanical, and Electrical Diploma courses."
        c = courses[0]
        return (f"Great choice! {c['name']} is a {c['duration']} course with {c['seats']} seats "
                f"(Direct 2nd Year seats: {c.get('direct_second_year_seats', 'N/A')}). 😊")
    lines = ["Here are the Diploma courses we offer:"]
    for c in courses:
        lines.append(
            f"• {c['name']} — {c['duration']}, {c['seats']} seats "
            f"(Direct 2nd Year seats: {c.get('direct_second_year_seats', 'N/A')})"
        )
    return "\n".join(lines)


def fmt_seats(d, branch=None, message=""):
    courses = d.get("courses_offered", [])
    if branch:
        courses = [c for c in courses if branch in c["name"].lower()]
        if not courses:
            return f"I couldn't find seat information for '{branch}'."
        c = courses[0]
        return f"{c['name']}: {c['seats']} seats (1st year), {c.get('direct_second_year_seats', 'N/A')} (Direct 2nd Year)"
    lines = ["Seat intake per branch:"]
    for c in courses:
        lines.append(f"• {c['name']}: {c['seats']} seats (1st year), {c.get('direct_second_year_seats', 'N/A')} (Direct 2nd Year)")
    return "\n".join(lines)


def fmt_admission(d, branch=None, message=""):
    """FIXED: only answers the specific sub-topic asked, not the whole bundle."""
    a = d.get("admission_process", {})
    msg = (message or "").lower()

    if mentions_any(msg, ["eligibility", "patrata", "पात्रता", "eligible"]):
        return f"Eligibility: {a.get('eligibility', 'N/A')}"

    if mentions_any(msg, ["minimum marks", "kitne percent", "kitna percentage", "% marks"]):
        return f"Minimum marks required: {a.get('minimum_marks', 'N/A')}"

    if mentions_any(msg, ["how to apply", "kaise apply", "apply kaise", "kaise le", "kaise admission le"]):
        return f"How to apply: {a.get('how_to_apply', 'N/A')}"

    if mentions_any(msg, ["entrance", "cap", "merit"]):
        return f"Entrance process: {a.get('entrance_exam', 'N/A')}"

    if mentions_any(msg, ["institute code", "college code"]):
        return f"Institute Code: {a.get('institute_code', 'N/A')}"

    # No specific sub-topic asked -> give the full overview (reasonable default)
    branch_txt = f" for {branch.title()} Engineering" if branch else ""
    return (
        f"Happy to help with admission{branch_txt}! 😊\n\n"
        f"Eligibility: {a.get('eligibility', 'N/A')}\n\n"
        f"Minimum marks: {a.get('minimum_marks', 'N/A')}\n\n"
        f"Entrance process: {a.get('entrance_exam', 'N/A')}\n\n"
        f"How to apply: {a.get('how_to_apply', 'N/A')}\n\n"
        f"Institute Code: {a.get('institute_code', 'N/A')}"
    )


def fmt_documents(d, branch=None, message=""):
    a = d.get("admission_process", {})
    msg = (message or "").lower()
    d1 = a.get("documents_required_1st_year", [])
    d2 = a.get("documents_required_direct_second_year", [])

    if mentions_any(msg, ["second year", "2nd year", "dsy", "lateral", "direct second"]):
        lines = ["Documents needed for Direct Second Year admission:"]
        lines += [f"• {x}" for x in d2]
        return "\n".join(lines)

    if mentions_any(msg, ["first year", "1st year"]):
        lines = ["Documents needed for 1st Year admission:"]
        lines += [f"• {x}" for x in d1]
        return "\n".join(lines)

    lines = ["Here are the documents you'll need 📄", "\nFor 1st Year admission:"]
    lines += [f"• {x}" for x in d1]
    lines.append("\nFor Direct Second Year admission:")
    lines += [f"• {x}" for x in d2]
    return "\n".join(lines)


def fmt_fees(d, branch=None, message=""):
    """FIXED: if user specifies first-year or direct-second-year, answer only that."""
    f = d.get("fees", {})
    fy = f.get("first_year", {})
    dsy = f.get("direct_second_year", {})
    msg = (message or "").lower()

    if mentions_any(msg, ["second year", "2nd year", "dsy", "lateral", "direct second"]):
        lines = ["Direct Second Year Fees:"]
        for k, v in dsy.items():
            lines.append(f"• {k.replace('_', ' / ')}: {v}")
        return "\n".join(lines)

    if mentions_any(msg, ["first year", "1st year"]):
        lines = ["First Year Fees:"]
        for k, v in fy.items():
            lines.append(f"• {k.replace('_', ' / ')}: {v}")
        return "\n".join(lines)

    lines = ["Here's the fee structure for Diploma courses:", "\nFirst Year:"]
    for k, v in fy.items():
        lines.append(f"• {k.replace('_', ' / ')}: {v}")
    lines.append("\nDirect Second Year:")
    for k, v in dsy.items():
        lines.append(f"• {k.replace('_', ' / ')}: {v}")
    return "\n".join(lines)


def fmt_facilities(d, branch=None, message=""):
    lines = ["Here's what's available on campus 🏫"]
    lines += [f"• {x}" for x in d.get("facilities", [])]
    return "\n".join(lines)


def fmt_placements(d, branch=None, message=""):
    p = d.get("placements", {})
    msg = (message or "").lower()

    if mentions_any(msg, ["company", "companies", "recruiter", "recruiters"]) and not mentions_any(msg, ["package", "salary", "rate", "%"]):
        lines = ["Top recruiters at our college:"]
        lines += [f"• {c}" for c in p.get("top_recruiters", [])]
        return "\n".join(lines)

    if mentions_any(msg, ["package", "salary", "lpa"]) and not mentions_any(msg, ["company", "companies"]):
        return (f"Average package: {p.get('average_package', 'N/A')}\n"
                f"Highest package: {p.get('highest_package', 'N/A')}\n"
                f"Starting package: {p.get('starting_package', 'N/A')}")

    lines = [
        "Good news on placements! 🎉",
        f"Placement rate: {p.get('placement_rate', 'N/A')}",
        f"Average package: {p.get('average_package', 'N/A')}",
        f"Highest package: {p.get('highest_package', 'N/A')}",
        f"Starting package: {p.get('starting_package', 'N/A')}",
        "\nTop recruiters:",
    ]
    lines += [f"• {c}" for c in p.get("top_recruiters", [])]
    return "\n".join(lines)


def fmt_contact(d, branch=None, message=""):
    c = d.get("contact", {})
    return (
        f"Here's how you can reach us 📞\n\n"
        f"Address: {c.get('address', 'N/A')}\n\n"
        f"Phone: {c.get('phone', 'N/A')}\n"
        f"Email: {c.get('email', 'N/A')}\n"
        f"Institute Code: {c.get('institute_code', 'N/A')}"
    )


def fmt_timings(d, branch=None, message=""):
    t = d.get("timings", {})
    return (
        f"College Lecture Timing: {t.get('college_hours', 'N/A')}\n"
        f"Office Timing: {t.get('office_hours', 'N/A')}\n"
        f"Saturday: {t.get('saturday', 'N/A')}"
    )


def fmt_staff(d, branch=None, message=""):
    m = d.get("management_and_staff", {})
    dep = d.get("departments", {})
    committee_hods = d.get("committee_designated_hods", {})

    if branch:
        matched_key = next((k for k in dep.keys() if branch in k), None)
        if matched_key:
            info = dep[matched_key]
            reply = (f"{matched_key.replace('_', ' ').title()} HOD (teaching) is {info.get('hod_name', 'N/A')}.\n"
                     f"Contact: {info.get('contact_number', 'N/A')}\n"
                     f"Email: {info.get('email', 'N/A')}")
            branch_title = matched_key.replace("_", " ").title().replace("Engineering", "Engineering").strip()
            committee_name = next((v for k, v in committee_hods.items() if branch in k.lower()), None)
            if committee_name:
                reply += f"\n\nNote: In the college's official committee records, {committee_name} is listed as the committee-designated HOD for this department."
            return reply
        return f"I don't have HOD information specifically for '{branch}'."

    lines = ["College Management:"]
    for role, info in m.items():
        if isinstance(info, dict):
            lines.append(f"• {role.replace('_', ' ').title()}: {info.get('name', 'N/A')} ({info.get('contact_number', 'N/A')})")
        else:
            lines.append(f"• {role.replace('_', ' ').title()}: {info}")
    lines.append("\nDepartment HODs (teaching):")
    for dept, info in dep.items():
        lines.append(f"• {dept.replace('_', ' ').title()}: {info.get('hod_name', 'N/A')} ({info.get('contact_number', 'N/A')})")
    if committee_hods:
        lines.append("\nCommittee-designated HODs (official committee records):")
        for dept, name in committee_hods.items():
            lines.append(f"• {dept}: {name}")
    return "\n".join(lines)


def fmt_committees(d, branch=None, message=""):
    committees = d.get("committees", [])
    if not committees:
        return "Committee information is not available right now."
    lines = ["Here are the college committees on record:"]
    for c in committees:
        lines.append(f"\n{c['identified_by']}:")
        for member in c.get("members", []):
            lines.append(f"  • {member['name']} — {member['designation']}")
    return "\n".join(lines)


def fmt_institution_details(d, branch=None, message=""):
    info = d.get("institution_details", {})
    if not info:
        return "Institution approval details are not available right now."
    lines = [
        f"Institution: {info.get('institution_name', 'N/A')}",
        f"Society/Trust: {info.get('society_trust_name', 'N/A')}",
        f"Address: {info.get('institution_address', 'N/A')}",
        f"Institution Type: {info.get('institution_type', 'N/A')}",
        f"Year of Establishment: {info.get('year_of_establishment', 'N/A')}",
        f"Permanent ID: {info.get('permanent_id', 'N/A')}",
        "\nApproved Programs (2025-26):",
    ]
    for p in info.get("programs_2025_26", []):
        lines.append(f"• {p['course']} ({p['level']}) — Intake: {p['intake_2025_26']}, Affiliated to: {p['affiliating_body']}")
    return "\n".join(lines)


def fmt_about(d, branch=None, message=""):
    return "Here's a bit about us 🎓\n\n" + d.get("about", "Information not available.")


def fmt_news(_d, branch=None, message=""):
    news = get_content().get("news", [])
    if not news:
        return "No news updates right now. Check back soon! 📰"
    lines = ["Here's the latest news:"]
    for n in sorted(news, key=lambda x: x["date"], reverse=True):
        lines.append(f"• [{n['date']}] {n['title']} — {n['description']}")
    return "\n".join(lines)


def fmt_events(_d, branch=None, message=""):
    events = get_content().get("events", [])
    if not events:
        return "No upcoming events right now. Stay tuned! 🎪"
    lines = ["Here are the upcoming events:"]
    for e in sorted(events, key=lambda x: x["date"]):
        lines.append(f"• [{e['date']}] {e['title']} — {e['description']}")
    return "\n".join(lines)


def fmt_scholarship(d, branch=None, message=""):
    s = d.get("scholarship", {})
    msg = (message or "").lower()

    if mentions_any(msg, ["apply", "how to apply", "kaise apply", "kaise", "mahadbt", "portal"]):
        return "How to apply for scholarship:\n" + s.get("how_to_apply", "Please contact the college office.")

    if mentions_any(msg, ["eligib", "eligible", "kaun", "patrata"]):
        return "Scholarship Eligibility:\n" + s.get("eligibility", "N/A")

    lines = ["Here's scholarship information 🎓", "\n" + s.get("note", ""), "\nAvailable scholarships:"]
    lines += [f"• {t}" for t in s.get("types", [])]
    lines.append(f"\nHow to apply: {s.get('how_to_apply', 'N/A')}")
    return "\n".join(lines)


def fmt_hostel(d, branch=None, message=""):
    h = d.get("hostel", {})
    msg = (message or "").lower()

    if mentions_any(msg, ["fee", "fees", "paisa", "paise", "cost"]):
        return "Hostel Fees:\n" + h.get("fees_note", "Please contact the college office.")

    if mentions_any(msg, ["apply", "admission", "kaise le"]):
        return "Hostel Admission:\n" + h.get("how_to_apply", "Please contact the college office.")

    if not h.get("available"):
        return "Sorry, hostel facility information is not available right now."

    lines = [f"Yes! We have {h.get('type', 'a hostel facility')} on campus 🏠", "\nHostel facilities:"]
    lines += [f"• {f}" for f in h.get("facilities", [])]
    lines.append(f"\n{h.get('fees_note', '')}")
    lines.append(f"How to apply: {h.get('how_to_apply', 'N/A')}")
    return "\n".join(lines)


def fmt_exam_schedule(d, branch=None, message=""):
    e = d.get("exam_schedule", {})
    lines = ["Exam Schedule Information 📝", "\n" + e.get("note", "")]
    lines.append("\nTypes of exams:")
    lines += [f"• {t}" for t in e.get("types", [])]
    lines.append(f"\nWhere to check dates: {e.get('how_to_check', 'N/A')}")
    lines.append(f"\n{e.get('current_status', '')}")
    return "\n".join(lines)


def _format_timetable(c):
    """Format a class's timetable for the chatbot: prefer the new structured
    rows (time/subject/teacher); fall back to the old free-text field for
    any class that hasn't been updated to the new table format yet."""
    rows = c.get("timetable_rows")
    if rows:
        return "\n".join(f"• {r.get('time', '')} — {r.get('subject', '')}"
                          + (f" ({r['teacher']})" if r.get("teacher") else "")
                          for r in rows)
    return c.get("timetable", "Timetable not set yet.")


def fmt_classroom(d, branch=None, message=""):
    classes = get_classrooms().get("classes", {})
    year = detect_year(message or "")

    if not branch:
        return ("Please tell me which branch (Computer / Civil / Mechanical / Electrical) "
                "and year (1st Year / Direct 2nd Year / 3rd Year) you'd like the timetable for.")

    if branch and year:
        key = f"{branch}_{year}"
        c = classes.get(key)
        if not c:
            return f"I couldn't find timetable info for that class."
        reply = f"{c['display_name']} Timetable:\n{_format_timetable(c)}"
        if c.get("notices"):
            reply += "\n\nClass Notices:"
            for n in c["notices"]:
                reply += f"\n• {n['title']}: {n['message']}"
        return reply

    # branch known, year not specified -> show both years briefly
    lines = [f"Here's the timetable info for {branch.title()} Engineering:"]
    for suffix in ("first", "second", "third"):
        c = classes.get(f"{branch}_{suffix}")
        if c:
            lines.append(f"\n{c['display_name']}:\n{_format_timetable(c)}")
    return "\n".join(lines)


# Suggested follow-up questions shown as chips after the bot replies
FOLLOWUPS = {
    "greeting": ["What courses do you offer?", "Fees kitni hai?", "Admission process?"],
    "courses": ["Fees kitni hai?", "Seats kitni hai?", "Placement kaisa hai?"],
    "admission": ["Documents kya chahiye?", "Fees kitni hai?", "Admission contact number?"],
    "fees": ["Admission process kya hai?", "Facilities kya hai?"],
    "facilities": ["Placement kaisa hai?", "Contact number batao"],
    "placements": ["Courses konse hai?", "Admission kaise le?"],
    "contact": ["Timings kya hai?", "Admission contact number?"],
    "staff": ["Contact number batao", "Courses konse hai?"],
    "admission_contact": ["Documents kya chahiye?", "Fees kitni hai?"],
    "classroom": ["Admission contact number?", "Fees kitni hai?"],
    "scholarship": ["Scholarship kaise apply kare?", "Eligibility kya hai?", "Fees kitni hai?"],
    "hostel": ["Hostel fees kitni hai?", "Hostel me admission kaise le?", "Facilities kya hai?"],
    "exam_schedule": ["Timetable dikhao", "News kya hai?", "Contact number batao"],
    "thanks": ["Courses konse hai?", "Fees kitni hai?", "Admission kaise le?"],
    "goodbye": [],
    "bot_identity": ["Courses konse hai?", "Fees kitni hai?", "Admission kaise le?"],
}

INTENTS = [
    {"name": "greeting", "keywords": ["hi", "hello", "hey", "namaste", "namaskar", "नमस्ते", "नमस्कार",
                                        "good morning", "good evening"], "answer": None},
    {"name": "about", "keywords": ["about", "about college", "college ke bare", "college kaisa hai",
                                     "कॉलेज के बारे", "कॉलेज कसे आहे", "college mahiti", "history"], "answer": fmt_about},
    {"name": "admission_contact", "keywords": [], "answer": fmt_admission_contact},  # special-cased
    {"name": "classroom", "keywords": ["timetable", "time table", "class schedule", "classroom",
                     "वेळापत्रक", "टाइमटेबल", "class ki jankari"], "answer": fmt_classroom},
    {"name": "courses", "keywords": ["course", "courses", "branch", "branches", "diploma",
                     "kaunsa course", "konsa course", "kaun se course",
                     "कोर्स", "कोणते कोर्स", "शाखा", "अभ्यासक्रम", "kaunte abhyaskram"], "answer": fmt_courses},
    {"name": "seats", "keywords": ["seat", "seats", "kitni seat", "intake", "सीट", "जागा", "किती जागा", "kiti jaga"],
     "answer": fmt_seats},
    {"name": "admission", "keywords": ["admission", "admison", "eligibility", "apply", "entrance", "kaise admission",
                     "admission kaise le", "admission process", "cap", "merit",
                     "प्रवेश", "प्रवेश कसा घ्यायचा", "एडमिशन कैसे ले", "पात्रता", "patrata"], "answer": fmt_admission},
    {"name": "documents", "keywords": ["document", "documents", "kagaz", "kagajpatra", "certificate", "papers needed",
                     "कागदपत्रे", "दस्तावेज़", "कागज़ात"], "answer": fmt_documents},
    {"name": "fees", "keywords": ["fee", "fees", "paisa", "paise", "kharcha", "cost", "fee kitni", "total fees",
                     "फीस", "शुल्क", "पैसे कितने", "किती पैसे", "kiti paise"], "answer": fmt_fees},
    {"name": "facilities", "keywords": ["facility", "facilities", "lab", "library", "hostel", "canteen",
                     "sports", "wifi", "computer lab", "workshop",
                     "सुविधा", "सुविधाएं", "सोयीसुविधा", "वसतिगृह", "ग्रंथालय", "लायब्ररी"], "answer": fmt_facilities},
    {"name": "placements", "keywords": ["placement", "placements", "job", "jobs", "package", "salary",
                     "company", "companies", "naukri", "recruit",
                     "नौकरी", "प्लेसमेंट", "प्लेसमेंट कसे आहे", "पगार", "salary kiti"], "answer": fmt_placements},
    {"name": "contact", "keywords": ["contact", "phone", "number", "email", "address", "pata", "location", "kaha hai",
                     "संपर्क", "फोन नंबर", "पत्ता", "कुठे आहे", "kuthe aahe"], "answer": fmt_contact},
    {"name": "timings", "keywords": ["timing", "timings", "time", "samay", "hours", "kab khulta", "college time",
                     "वेळ", "वेळापत्रक", "समय", "कधी सुरू", "kadhi suru"], "answer": fmt_timings},
    {"name": "staff", "keywords": ["hod", "principal", "chairman", "staff", "teacher", "faculty", "management",
                     "director", "department", "dept", "विभाग",
                     "प्राचार्य", "अध्यक्ष", "शिक्षक", "स्टाफ", "व्यवस्थापन"], "answer": fmt_staff},
    {"name": "committees", "keywords": ["committee", "committees", "anti ragging", "grievance", "iqac",
                     "governing body", "समिती", "समिति", "कमिटी"], "answer": fmt_committees},
    {"name": "institution_details", "keywords": ["permanent id", "application id", "aicte", "msbte approval",
                     "intake capacity", "approved intake", "institution type", "year of establishment",
                     "society trust", "affiliating body"], "answer": fmt_institution_details},
    {"name": "news", "keywords": ["news", "notice", "announcement", "khabar", "समाचार", "बातम्या", "सूचना"],
     "answer": fmt_news},
    {"name": "events", "keywords": ["event", "events", "function", "karyakram", "कार्यक्रम", "इवेंट", "उपक्रम"],
     "answer": fmt_events},
    {"name": "scholarship", "keywords": ["scholarship", "scholarships", "chatravrutti", "chatrawrutti",
                     "mahadbt", "freeship", "tfws", "shishyavrutti",
                     "शिष्यवृत्ती", "छात्रवृत्ति", "स्कॉलरशिप"], "answer": fmt_scholarship},
    {"name": "hostel", "keywords": ["hostel", "hostel facility", "boys hostel", "girls hostel", "vasatigruh",
                     "वसतिगृह", "हॉस्टल"], "answer": fmt_hostel},
    {"name": "exam_schedule", "keywords": ["exam schedule", "exam timetable", "exam date", "exam dates",
                     "msbte exam", "pariksha", "kab hai exam", "exam kab hai",
                     "परीक्षा वेळापत्रक", "परीक्षेचे वेळापत्रक", "परीक्षा कधी"], "answer": fmt_exam_schedule},
    {"name": "thanks", "keywords": ["thanks", "thank you", "thanku", "thnx", "dhanyawad", "shukriya",
                     "धन्यवाद", "आभारी आहे"], "answer": None},
    {"name": "goodbye", "keywords": ["bye", "bye bye", "goodbye", "alvida", "tata", "phir milenge",
                     "chalta hoon", "nikalta hoon", "अलविदा", "निघतो"], "answer": None},
    {"name": "bot_identity", "keywords": ["your name", "tumhara naam", "tumhara naam kya hai", "aap kaun ho",
                     "who are you", "bot ka naam", "tum kaun ho", "tu kaun hai"], "answer": None},
]

FALLBACK = (
    "Hmm, I'm not sure about that one 🤔 / माफ़ करें, यह जानकारी उपलब्ध नहीं है। "
    "You can ask me about courses, admission, fees, facilities, placements, staff, timings, "
    "classroom timetables, scholarship, hostel, exam schedule, news, events, or contact details. "
    "You can also just say hi, thanks, or bye anytime! 😊"
)

BRANCH_AWARE_INTENTS = {"courses", "seats", "staff", "admission", "admission_contact",
                         "fees", "documents", "placements", "classroom"}


def clean(text):
    text = text.lower()
    text = re.sub(r"[^\w\s\u0900-\u097F]", " ", text)
    words = [TYPO_MAP.get(w, w) for w in text.split()]
    return " ".join(words)


# Common, frequently-seen typos mapped directly to the correct word. This is
# faster and safer than fuzzy-matching for these specific known mistakes, and
# it runs before intent matching so every keyword/fuzzy check below benefits.
TYPO_MAP = {
    "admision": "admission", "addmission": "admission", "admisson": "admission",
    "admition": "admission", "admisiion": "admission",
    "collage": "college", "colege": "college", "collge": "college", "collej": "college",
    "shedule": "schedule", "schedual": "schedule", "sedule": "schedule",
    "hostle": "hostel", "hostal": "hostel", "hostell": "hostel",
    "scolarship": "scholarship", "scholorship": "scholarship", "schollarship": "scholarship",
    "scholarhip": "scholarship", "scholarshp": "scholarship",
    "fes": "fees", "fies": "fees", "fee's": "fees",
    "plesment": "placement", "placment": "placement", "plasment": "placement",
    "placemnt": "placement",
    "pricipal": "principal", "prinicipal": "principal", "principle": "principal",
    "facilty": "facility", "faciltiy": "facility", "facilites": "facilities",
    "recieve": "receive", "seperate": "separate", "adress": "address",
    "timming": "timing", "timmings": "timings", "tming": "timing",
    "eligiblity": "eligibility", "eligibilty": "eligibility",
    "documnet": "document", "documnets": "documents", "docments": "documents",
    "cource": "course", "corse": "course", "coures": "course",
}

# Words that signal the person may be stressed, confused, or in a hurry —
# used to add a short empathetic opening line before the normal answer.
EMOTION_WORDS = {
    "urgent", "jaldi", "please help", "help me", "confuse", "confused",
    "pareshan", "pareshaan", "tension", "problem", "dikkat", "worried",
    "gussa", "angry", "frustrated", "समझ नहीं", "परेशान", "जल्दी",
}

EMOTION_OPENERS = [
    "I understand this is important to you — here's the info right away. 🙏\n\n",
    "No worries, let me help you with this quickly. 😊\n\n",
    "I hear you — let's sort this out. Here's what you need: \n\n",
]


# Common filler / helper words in Hinglish that appear inside many keyword
# phrases (e.g. "kaise admission", "fee kitni"). These must NOT count as a
# "match" on their own during fuzzy/typo-tolerant matching — otherwise a
# typo like "plesment" could accidentally score points for the "admission"
# intent just because the message also happens to contain "kaisa"/"kaise".
STOPWORDS = {
    "hai", "he", "hei", "hain", "kya", "kaisa", "kaise", "kitni", "kitne", "kiti",
    "ka", "ki", "ke", "ho", "kab", "kahan", "batao", "bata", "do", "de",
    "please", "plz", "sir", "madam", "mujhe", "mujhko", "chahiye",
    "milegi", "milega", "milta", "milte", "tha", "thi", "the", "abhi",
    "aap", "aapka", "aapke", "apna", "hoon", "hun", "kese", "kesa",
}


def fuzzy_word_match(word_a, word_b, threshold=0.75):
    """True if two words are close enough to be the same word with a typo."""
    if max(len(word_a), len(word_b)) < 4:
        return word_a == word_b  # too short/risky to fuzzy-match
    return difflib.SequenceMatcher(None, word_a, word_b).ratio() >= threshold


def fuzzy_keyword_score(msg_words, keyword):
    """Return a score if `keyword` (possibly multi-word) roughly matches
    words in the message, even with typos (e.g. 'admision', 'scholarhip',
    'schollarship', 'fes', 'hostle'). Filler words like 'kitni'/'kaise' are
    ignored so they can't accidentally trigger the wrong topic."""
    kw_words = [w for w in keyword.lower().split() if w not in STOPWORDS]
    if not kw_words:
        return 0

    matched_flags = []
    for kw_word in kw_words:
        if len(kw_word) < 4:
            found = kw_word in msg_words  # too short/risky to fuzzy-match
        else:
            found = any(fuzzy_word_match(kw_word, mw) for mw in msg_words)
        matched_flags.append(found)

    matched = sum(matched_flags)
    if matched == 0:
        return 0
    # Require a clear majority of the significant words in the phrase to
    # match (strictly more than half) — a single filler-word coincidence,
    # or exactly half of a 2-word phrase, should never be enough on its own.
    if matched / len(kw_words) <= 0.5:
        return 0
    return matched


def fuzzy_mentions_any(msg, words, threshold=0.75):
    """Typo-tolerant version of mentions_any — catches misspelled words too
    (e.g. 'scolarship', 'hostle', 'schedule' typed as 'shedule')."""
    if mentions_any(msg, words):
        return True
    msg_words = msg.split()
    for phrase in words:
        phrase_words = [w for w in phrase.lower().split() if w not in STOPWORDS]
        if phrase_words and all(
            any(fuzzy_word_match(pw, mw, threshold=threshold) for mw in msg_words)
            for pw in phrase_words
        ):
            return True
    return False


def extract_keywords(text):
    """Pull the significant words out of an admin-entered question, so a
    future student's message (even worded differently) can still be
    matched to it. Stopwords/filler words and very short words are
    dropped since they carry little meaning on their own."""
    cleaned = clean(text)
    words = [w for w in cleaned.split() if w not in STOPWORDS and len(w) >= 3]
    # de-duplicate while keeping order
    seen = set()
    keywords = []
    for w in words:
        if w not in seen:
            seen.add(w)
            keywords.append(w)
    return keywords


def match_custom_qa(cleaned_msg, msg_words):
    """Check admin-taught Q&A pairs (built from previously-unanswered
    questions). Returns the best matching answer, or None if nothing is
    a confident enough match. Runs after the built-in intents/context
    fail and before the AI hybrid backup, since an admin-confirmed
    answer is more trustworthy than a generic AI guess."""
    qa_data = get_custom_qa()
    items = qa_data.get("items", [])
    if not items:
        return None

    best_item = None
    best_ratio = 0.0
    for item in items:
        keywords = item.get("keywords") or []
        if not keywords:
            continue
        matched = sum(
            1 for kw in keywords
            if any(fuzzy_word_match(kw, mw) for mw in msg_words) or kw in msg_words
        )
        ratio = matched / len(keywords)
        if ratio > best_ratio:
            best_ratio = ratio
            best_item = item

    # Require a clear majority of the saved question's keywords to show up
    # in the new message, so unrelated questions never get a wrong answer.
    if best_item and best_ratio > 0.6:
        return best_item.get("answer")
    return None


def get_best_intent(message):
    msg = clean(message)
    msg_words = msg.split()

    if fuzzy_mentions_any(msg, ADMISSION_WORDS, threshold=0.82) and fuzzy_mentions_any(msg, CONTACT_WORDS, threshold=0.82):
        return next(i for i in INTENTS if i["name"] == "admission_contact"), 99

    # These topics share generic words (like "apply") with the admission intent,
    # so if their own distinctive keywords are present, they take priority.
    # fuzzy_mentions_any also catches common spelling mistakes. A stricter
    # threshold is used here since these checks short-circuit and bypass
    # the safer weighted scoring below (e.g. "pareshan" must NOT match
    # "pariksha"/exam just because the letters are similar).
    if fuzzy_mentions_any(msg, SCHOLARSHIP_WORDS, threshold=0.82):
        return next(i for i in INTENTS if i["name"] == "scholarship"), 99
    if fuzzy_mentions_any(msg, HOSTEL_WORDS, threshold=0.82):
        return next(i for i in INTENTS if i["name"] == "hostel"), 99
    if fuzzy_mentions_any(msg, EXAM_SCHEDULE_WORDS, threshold=0.82):
        return next(i for i in INTENTS if i["name"] == "exam_schedule"), 99

    best_intent = None
    best_score = 0
    for intent in INTENTS:
        if intent["name"] == "admission_contact":
            continue
        score = 0
        for kw in intent["keywords"]:
            # Word-boundary match, not plain substring — otherwise short
            # keywords like "hi" would false-match inside words such as
            # "scholarship" (scholar-SHIp) or "history".
            pattern = r"(?<!\w)" + re.escape(kw.lower()) + r"(?!\w)"
            if re.search(pattern, msg):
                # Exact matches are weighted heavily so they always win over
                # a fuzzy coincidence from an unrelated intent (e.g. "kaun"
                # loosely matching "kaunsa" in the courses keyword list
                # should never outrank an exact "staff"/"principal" match).
                score += len(kw.split()) * 10
            else:
                # Typo-tolerant: give partial credit for a close-enough match
                # so common spelling mistakes (e.g. "admision", "scolarship",
                # "fes", "hostle") are still understood.
                score += fuzzy_keyword_score(msg_words, kw)
        if score > best_score:
            best_score = score
            best_intent = intent

    return best_intent, best_score


GREETING_REPLIES = [
    "Hello! 👋 I'm College AI Assistant, {college}'s enquiry chatbot. Ask me about courses, admission, fees, placements, facilities, news, events, or contact details.",
    "Hi there! 😊 I'm College AI Assistant from {college}. How can I help you today — admission, fees, courses, or something else?",
    "Namaste! 🙏 I'm College AI Assistant, {college}'s chatbot assistant. Ask me anything about admission, fees, courses, hostel, scholarship, and more.",
]

THANKS_REPLIES = [
    "You're most welcome! 😊 Feel free to ask if you have any other questions.",
    "Glad I could help! 🙌 Let me know if there's anything else you'd like to know.",
    "Anytime! 😊 I'm here if you need anything else about {college}.",
]

GOODBYE_REPLIES = [
    "Goodbye! 👋 Have a great day. Feel free to come back anytime you have questions.",
    "Take care! 😊 Come back whenever you need help with admission, fees, or anything else.",
    "Bye! 👋 All the best — I'm here whenever you need info about {college}.",
]

BOT_IDENTITY_REPLIES = [
    "I'm College AI Assistant 🤖, {college}'s enquiry chatbot! I can help you with admission, fees, courses, hostel, scholarship, and more.",
    "My name is College AI Assistant 🤖 — I'm here to answer your questions about {college}, like admission, fees, courses, and facilities.",
]


# Intents whose answer function can meaningfully use `message` text to
# refine/re-filter a response (used for multi-turn follow-up context, e.g.
# "fees kitni hai?" -> "first year?" should still answer about fees).
CONTEXT_CAPABLE_INTENTS = BRANCH_AWARE_INTENTS | {"scholarship", "hostel", "exam_schedule"}

# For non-branch-aware context intents, a follow-up must contain one of
# these words to count as "relevant" to the remembered topic — this stops
# an unrelated/gibberish message from accidentally reusing the old topic.
REFINEMENT_KEYWORDS = {
    "fees": ["first year", "1st year", "second year", "2nd year", "dsy",
             "lateral", "direct second"],
    "scholarship": ["apply", "eligibility", "eligible", "patrata",
                     "how to apply", "mahadbt", "contact"],
    "hostel": ["fee", "fees", "apply", "admission", "facility",
               "facilities", "room", "contact"],
    "exam_schedule": ["date", "dates", "timetable", "schedule", "contact"],
}

# Intents that are just small-talk, not "topics" worth remembering as context.
SMALLTALK_INTENTS = {"greeting", "thanks", "goodbye", "bot_identity"}


def _session_get(key, default=None):
    """Safe session read — returns `default` outside a Flask request
    context (e.g. when testing get_reply_with_suggestions directly)."""
    if has_request_context():
        return session.get(key, default)
    return default


def _session_set(key, value):
    """Safe session write — no-op outside a Flask request context."""
    if has_request_context():
        session[key] = value


CHAT_HISTORY_MAX_TURNS = 6  # keep the last few exchanges only (cheap + enough context)


def _history_get():
    return _session_get("chat_history", [])


def _history_append(user_msg, bot_reply):
    """Remember this exchange so the AI (Gemini) can hold a real conversation
    instead of answering each message in isolation. Capped in length so the
    session doesn't grow forever."""
    history = _history_get()
    history.append({"role": "user", "text": user_msg})
    history.append({"role": "model", "text": bot_reply})
    history = history[-(CHAT_HISTORY_MAX_TURNS * 2):]
    _session_set("chat_history", history)


def detect_emotion(msg):
    """Very lightweight tone check — looks for words suggesting the person
    is stressed, confused, or in a hurry, so we can open with a bit of
    empathy before the normal factual answer."""
    return any(w in msg for w in EMOTION_WORDS)


AI_USAGE_PATH = os.path.join(BASE_DIR, "ai_usage.json")
AI_DAILY_LIMIT = 40  # keeps well within Gemini's free-tier daily quota


def _ai_usage_ok_and_increment():
    """Very small daily counter so the AI backup is only ever used a
    limited number of times per day — common questions should never need
    it, so this is just a safety cap for genuinely unusual questions."""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        usage = load_json(AI_USAGE_PATH) if data_exists(AI_USAGE_PATH) else {}
    except Exception:
        usage = {}
    if usage.get("date") != today:
        usage = {"date": today, "count": 0}
    if usage.get("count", 0) >= AI_DAILY_LIMIT:
        return False
    usage["count"] = usage.get("count", 0) + 1
    try:
        save_json(AI_USAGE_PATH, usage)
    except Exception:
        pass
    return True


def ai_hybrid_reply(message, data, history=None):
    """Very limited AI backup, used ONLY when the local rule-based matcher
    (and the multi-turn context fallback) both find nothing. Uses Google
    Gemini's free-tier API. Common questions never reach this — they're
    all answered locally, so the bot stays fast, free, and reliable, and
    Gemini is only spent on genuinely tricky/unusual questions.

    `history` (optional) is a list of {"role": "user"/"model", "text": ...}
    from earlier in this same conversation, so Gemini can hold real context
    (e.g. "which one is cheaper?" right after discussing two branches)
    instead of treating every message in isolation.

    Requires the GEMINI_API_KEY environment variable. If it's not set, or
    the request fails for any reason (no internet, rate limit, quota
    used up, etc.), this returns None and the caller shows the normal
    static FALLBACK message instead — the chatbot never breaks because
    of this."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    if not _ai_usage_ok_and_increment():
        return None
    try:
        import requests
        college_name = data.get("college_name", "the college")
        context_summary = json.dumps(data, ensure_ascii=False)[:6000]
        system_prompt = (
            f"You are College AI Assistant, the friendly enquiry chatbot for {college_name}. "
            "Answer the student's question ONLY using the JSON college data given below. "
            "If the answer truly isn't in the data, politely say you don't have that "
            "information and suggest they contact the college office. "
            "Reply in the same mixed Hinglish/English style as the question, keep it short "
            f"(under 80 words). Use the earlier conversation turns (if any) for context, "
            f"e.g. follow-up questions like 'what about civil?' or 'which is cheaper?'.\n\n"
            f"College data:\n{context_summary}"
        )

        contents = [{"role": "user", "parts": [{"text": system_prompt}]},
                    {"role": "model", "parts": [{"text": "Understood, I'll answer using only that data."}]}]
        for turn in (history or [])[-(CHAT_HISTORY_MAX_TURNS * 2):]:
            contents.append({"role": turn["role"], "parts": [{"text": turn["text"]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        resp = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={api_key}",
            json={
                "contents": contents,
                "generationConfig": {"maxOutputTokens": 300},
            },
            timeout=8,
        )
        if resp.status_code == 200:
            candidates = resp.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)
                return text.strip() or None
    except Exception:
        pass
    return None


def get_reply_with_suggestions(message):
    if not message.strip():
        return "Please type a question. / कृपया अपना सवाल टाइप करें।", []

    intent, score = get_best_intent(message)
    d = get_data()
    college_name = d.get("college_name")
    cleaned_msg = clean(message)
    emotional = detect_emotion(cleaned_msg)

    if intent and score > 0:
        if intent["name"] == "greeting":
            reply = random.choice(GREETING_REPLIES).format(college=college_name)
        elif intent["name"] == "thanks":
            reply = random.choice(THANKS_REPLIES).format(college=college_name)
        elif intent["name"] == "goodbye":
            reply = random.choice(GOODBYE_REPLIES).format(college=college_name)
        elif intent["name"] == "bot_identity":
            reply = random.choice(BOT_IDENTITY_REPLIES).format(college=college_name)
        elif intent["name"] in BRANCH_AWARE_INTENTS:
            branch = detect_branch(message)
            reply = intent["answer"](d, branch=branch, message=message)
        else:
            reply = intent["answer"](d, message=message)

        if emotional and intent["name"] not in SMALLTALK_INTENTS:
            reply = random.choice(EMOTION_OPENERS) + reply

        # Remember this topic so a short follow-up question (e.g. "first
        # year?" right after asking about fees) can still be understood.
        if intent["name"] not in SMALLTALK_INTENTS:
            _session_set("last_intent", intent["name"])

        suggestions = FOLLOWUPS.get(intent["name"], [])
        log_chat_question(intent["name"], message)
        if intent["name"] not in SMALLTALK_INTENTS:
            _history_append(message, reply)
        return reply, suggestions

    # Nothing matched directly — try using the topic from the previous
    # message as context, for short follow-up questions. This only fires
    # when the new message actually contains a recognizable refinement
    # word (e.g. "first year", "apply", a branch name) — a random/unrelated
    # message must NOT silently reuse the old topic.
    last_intent_name = _session_get("last_intent")
    if last_intent_name and len(cleaned_msg.split()) <= 6:
        last_intent = next((i for i in INTENTS if i["name"] == last_intent_name), None)
        is_branch_aware = last_intent_name in BRANCH_AWARE_INTENTS
        branch = detect_branch(message) if is_branch_aware else None
        relevant = bool(branch) or fuzzy_mentions_any(
            cleaned_msg, REFINEMENT_KEYWORDS.get(last_intent_name, [])
        )
        if last_intent and last_intent_name in CONTEXT_CAPABLE_INTENTS and relevant:
            try:
                reply = (last_intent["answer"](d, branch=branch, message=message)
                         if is_branch_aware
                         else last_intent["answer"](d, message=message))
                if reply:
                    if emotional:
                        reply = random.choice(EMOTION_OPENERS) + reply
                    log_chat_question(last_intent_name, message)
                    _history_append(message, reply)
                    return reply, FOLLOWUPS.get(last_intent_name, [])
            except Exception:
                pass

    # Local matching (with or without context) found nothing — check if
    # an admin has already taught the bot an answer for a similar
    # previously-unanswered question.
    custom_answer = match_custom_qa(cleaned_msg, cleaned_msg.split())
    if custom_answer:
        if emotional:
            custom_answer = random.choice(EMOTION_OPENERS) + custom_answer
        log_chat_question("custom_qa", message)
        _history_append(message, custom_answer)
        return custom_answer, ["Courses konse hai?", "Fees kitni hai?", "Admission kaise le?"]

    # Still nothing — try the optional AI hybrid backup before giving up
    # entirely.
    ai_reply = ai_hybrid_reply(message, d, history=_history_get())
    if ai_reply:
        log_chat_question("ai_hybrid", message)
        _history_append(message, ai_reply)
        return ai_reply, ["Courses konse hai?", "Fees kitni hai?", "Admission kaise le?"]

    # Gemini fail hua toh OpenRouter try karo
    or_reply = openrouter_reply(message, d, history=_history_get())
    if or_reply:
        log_chat_question("openrouter", message)
        _history_append(message, or_reply)
        return or_reply, ["Courses konse hai?", "Fees kitni hai?", "Admission kaise le?"]
    log_chat_question(None, message)
    
    reply = FALLBACK
    if emotional:
        reply = random.choice(EMOTION_OPENERS) + reply
    return reply, ["Courses konse hai?", "Fees kitni hai?", "Admission kaise le?"]


# =================================================================
# AUTH HELPERS
# =================================================================

def redirect_to_dashboard():
    if session.get("role") == "main_admin":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("teacher_dashboard"))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def main_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        if session.get("role") != "main_admin":
            flash("Only the main admin can do that.")
            return redirect_to_dashboard()
        return view(*args, **kwargs)
    return wrapped


def class_teacher_required(view):
    """A 'staff' (teacher) account that has been assigned a class (class_key)
    can manage that class's timetable, notices, and attendance."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        account = find_account(session["username"])
        if session.get("role") != "staff" or not (account and account.get("class_key")):
            flash("Only a teacher assigned to a class can do that.")
            return redirect_to_dashboard()
        return view(*args, **kwargs)
    return wrapped


# =================================================================
# SEO — meta tags, robots.txt, sitemap.xml
# =================================================================

@app.context_processor
def inject_seo_globals():
    """Makes `site_url` available in every template, so canonical links,
    Open Graph tags, and JSON-LD structured data can build full URLs."""
    return {"site_url": SITE_URL, "current_year": datetime.now().year}


@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /teacher",
        f"Sitemap: {SITE_URL}/sitemap.xml",
    ]
    return Response("\n".join(lines), mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    """Only genuinely public, search-worthy pages are listed here.
    Login pages and staff/admin dashboards are deliberately left out —
    they're blocked in robots.txt too, since there's nothing there for
    Google to usefully index and it's not meant for public visitors."""
    pages = [
        {"loc": url_for("home", _external=False), "changefreq": "weekly", "priority": "1.0"},
        {"loc": url_for("full_chat", _external=False), "changefreq": "monthly", "priority": "0.6"},
        {"loc": url_for("study_material", _external=False), "changefreq": "weekly", "priority": "0.7"},
    ]
    xml_items = "".join(
        f"<url><loc>{SITE_URL}{p['loc']}</loc>"
        f"<changefreq>{p['changefreq']}</changefreq>"
        f"<priority>{p['priority']}</priority></url>"
        for p in pages
    )
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{xml_items}</urlset>'
    return Response(xml, mimetype="application/xml")


# =================================================================
# PUBLIC ROUTES
# =================================================================

@app.route("/")
def home():
    data = get_data()
    content = get_content()
    news = sorted(content.get("news", []), key=lambda x: x["date"], reverse=True)
    for n in news:
        try:
            n["is_new"] = (datetime.utcnow().date() - datetime.strptime(n["date"], "%Y-%m-%d").date()).days <= 3
        except (ValueError, KeyError):
            n["is_new"] = False
    events = sorted(content.get("events", []), key=lambda x: x["date"])
    gallery = content.get("gallery", [])
    testimonials = content.get("testimonials", [])
    downloads = content.get("downloads", [])
    video_url = content.get("video_url", "")
    video_type = content.get("video_type", "youtube")
    video_file = content.get("video_file", "")

    a, b = random.randint(1, 9), random.randint(1, 9)
    session["captcha_answer"] = a + b
    captcha_question = f"{a} + {b}"

    form_success = request.args.get("submitted") == "1"
    form_error = session.pop("form_error", None)

    return render_template(
        "index.html", college=data, news=news, events=events, gallery=gallery,
        testimonials=testimonials, downloads=downloads, video_url=video_url,
        video_type=video_type, video_file=video_file,
        captcha_question=captcha_question, form_success=form_success, form_error=form_error
    )


@app.route("/chat")
def full_chat():
    data = get_data()
    return render_template("chat.html", college=data)


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json()
    user_message = body.get("message", "").strip()
    reply_lang = (body.get("lang") or "en").strip()  # "en", "hi", or "mr" — same selector as voice
    reply, suggestions = get_reply_with_suggestions(user_message)
    if reply_lang in ("hi", "mr"):
        reply = translate_text(reply, reply_lang)
    return jsonify({"reply": reply, "suggestions": suggestions})


def translate_text(text, target_lang):
    """Translate `text` into target_lang ('hi' or 'mr') using Gemini.
    Returns the original text unchanged if there's no API key, no internet,
    or the request fails for any reason — voice output should never break
    because of this, it just stays in whatever language it already was.
    Retries once if the first attempt comes back empty or clearly isn't
    actually in Devanagari script (a common partial-translation failure),
    so voice replies come out fully in the selected language more reliably."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return text
    lang_names = {"hi": "Hindi", "mr": "Marathi"}
    lang_name = lang_names.get(target_lang)
    if not lang_name:
        return text

    def _looks_translated(candidate_text):
        # At least some Devanagari characters should be present for a
        # genuine Hindi/Marathi translation of non-trivial text.
        devanagari_chars = sum(1 for ch in candidate_text if "\u0900" <= ch <= "\u097F")
        return devanagari_chars >= max(3, len(candidate_text) // 6)

    def _attempt():
        import requests
        prompt = (
            f"Translate the following college chatbot reply COMPLETELY into "
            f"natural, conversational {lang_name} (Devanagari script). "
            f"Translate everything, not just part of it. Keep it short and "
            f"friendly, don't translate proper nouns like college names or numbers. "
            f"Reply with ONLY the translated text, nothing else.\n\n"
            f"Text: {text}"
        )
        resp = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={api_key}",
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": 400},
            },
            timeout=12,
        )
        if resp.status_code == 200:
            candidates = resp.json().get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                return "".join(p.get("text", "") for p in parts).strip()
        return ""

    try:
        result = _attempt()
        if result and _looks_translated(result):
            return result
        # First attempt was empty or looked like it didn't really translate
        # (e.g. came back mostly in English) — try once more before giving up.
        result2 = _attempt()
        if result2 and _looks_translated(result2):
            return result2
        return result or result2 or text
    except Exception:
        pass
    return text


@app.route("/api/translate", methods=["POST"])
def translate_endpoint():
    body = request.get_json() or {}
    text = (body.get("text") or "").strip()
    target_lang = (body.get("lang") or "").strip()  # "hi", "mr", or "en"
    if not text or target_lang not in ("hi", "mr"):
        return jsonify({"translated": text})
    translated = translate_text(text, target_lang)
    return jsonify({"translated": translated})


@app.route("/apply", methods=["POST"])
def apply_admission():
    expected = session.get("captcha_answer")
    submitted_answer = request.form.get("captcha_answer", "").strip()
    try:
        correct = int(submitted_answer) == int(expected)
    except (ValueError, TypeError):
        correct = False

    if not correct:
        session["form_error"] = "Verification answer was incorrect. Please try again."
        return redirect(url_for("home") + "#apply")

    admissions = get_admissions()
    submissions = admissions.setdefault("submissions", [])
    new_id = (max([s["id"] for s in submissions], default=0)) + 1
    submissions.append({
        "id": new_id,
        "name": request.form.get("name", "").strip(),
        "phone": request.form.get("phone", "").strip(),
        "email": request.form.get("email", "").strip(),
        "course": request.form.get("course", "").strip(),
        "message": request.form.get("message", "").strip(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    save_json(ADMISSIONS_DATA_PATH, admissions)
    return redirect(url_for("home", submitted=1) + "#apply")


@app.route("/manifest.json")
def manifest():
    return app.send_static_file("manifest.json")


@app.route("/service-worker.js")
def service_worker():
    return app.send_static_file("service-worker.js")


# =================================================================
# ADMIN AUTH ROUTES
# =================================================================

# Simple in-memory login-attempt tracker (per IP address) to slow down
# brute-force password guessing. Resets on server restart, which is fine --
# its job is just to stop rapid automated guessing, not to be a permanent log.
LOGIN_ATTEMPTS = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def _is_locked_out(ip):
    entry = LOGIN_ATTEMPTS.get(ip)
    if not entry or not entry.get("locked_until"):
        return False
    if datetime.utcnow() < entry["locked_until"]:
        return True
    LOGIN_ATTEMPTS.pop(ip, None)
    return False


def _record_failed_login(ip):
    entry = LOGIN_ATTEMPTS.setdefault(ip, {"count": 0, "locked_until": None})
    entry["count"] += 1
    if entry["count"] >= MAX_LOGIN_ATTEMPTS:
        entry["locked_until"] = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)


def _clear_login_attempts(ip):
    LOGIN_ATTEMPTS.pop(ip, None)


@app.route("/admin/login", methods=["GET", "POST"])
def login():
    ip = request.remote_addr or "unknown"
    if request.method == "POST":
        if _is_locked_out(ip):
            flash(f"Too many failed attempts. Please try again in {LOCKOUT_MINUTES} minutes.")
            return render_template("login.html", college=get_data())

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        account = find_account(username)
        if account and check_password_hash(account["password_hash"], password):
            _clear_login_attempts(ip)
            session["logged_in"] = True
            session["username"] = account["username"]
            session["role"] = account["role"]
            session["full_name"] = account["full_name"]
            return redirect_to_dashboard()
        _record_failed_login(ip)
        flash("Invalid username or password.")
    return render_template("login.html", college=get_data())


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# =================================================================
# ADMIN DASHBOARD
# =================================================================

def _build_dashboard_context():
    content = get_content()
    admissions = sorted(get_admissions().get("submissions", []), key=lambda x: x["date"], reverse=True)
    accounts = get_accounts()["accounts"]
    college = get_data()
    current_account = find_account(session["username"])
    classrooms = get_classrooms()["classes"]

    my_class = None
    if current_account["role"] == "staff" and current_account.get("class_key"):
        my_class = classrooms.get(current_account["class_key"])

    subjects_data = get_subjects()
    attendance_data = get_attendance()
    my_class_students = []
    my_class_attendance_dates = []
    my_class_attendance_pct = []
    my_class_attendance_table = []
    if my_class is not None:
        class_att = attendance_data["classes"].get(current_account.get("class_key"), {"students": [], "records": {}})
        my_class_students = class_att.get("students", [])
        records = class_att.get("records", {})
        my_class_attendance_dates = sorted(records.keys(), reverse=True)[:10]

        # Graph data: % of recorded days each student was present.
        for student in my_class_students:
            total_days = 0
            present_days = 0
            for day_status in records.values():
                if student in day_status:
                    total_days += 1
                    if day_status[student] == "present":
                        present_days += 1
            pct = round((present_days / total_days) * 100) if total_days else 0
            my_class_attendance_pct.append({"name": student, "pct": pct, "present_days": present_days, "total_days": total_days})

        # Table data: student x date grid for the recent dates.
        for student in my_class_students:
            row = {"name": student, "statuses": []}
            for d in my_class_attendance_dates:
                row["statuses"].append(records.get(d, {}).get(student, "-"))
            my_class_attendance_table.append(row)

    is_main_admin = session.get("role") == "main_admin"

    analytics = None
    custom_qa_items = []
    if is_main_admin:
        raw_analytics = get_analytics()
        analytics = {
            "total_questions": raw_analytics.get("total_questions", 0),
            "top_topics": sorted(raw_analytics.get("topic_counts", {}).items(), key=lambda x: x[1], reverse=True)[:8],
            "recent_questions": raw_analytics.get("recent_questions", [])[:15],
            "unanswered_questions": [
                q for q in raw_analytics.get("recent_questions", []) if q.get("topic") == "unmatched"
            ][:15],
        }
        custom_qa_items = get_custom_qa().get("items", [])

    # Teachers get a lighter version of the same AI Assistant info: just the
    # questions students asked that the chatbot couldn't answer, so they can
    # add a learned answer for their subject -- without full site analytics.
    teacher_unanswered = []
    if not is_main_admin:
        raw_analytics = get_analytics()
        teacher_unanswered = [
            q for q in raw_analytics.get("recent_questions", []) if q.get("topic") == "unmatched"
        ][:15]
        custom_qa_items = get_custom_qa().get("items", [])

    # ---- Read-only dashboard summary stats (derived from existing data, no schema changes) ----
    dash_stats = None
    if is_main_admin:
        try:
            att_all = get_attendance().get("classes", {})
            total_students = sum(len(c.get("students", [])) for c in att_all.values())
        except Exception:
            total_students = 0
        total_departments = len({c.get("branch") for c in classrooms.values() if c.get("branch")})
        total_courses = len(college.get("courses_offered", []))
        dash_stats = {
            "total_students": total_students,
            "total_staff": len(accounts),
            "total_departments": total_departments,
            "total_courses": total_courses,
            "chatbot_queries": analytics["total_questions"] if analytics else 0,
            "total_admissions": len(admissions),
        }

    study_materials = get_study_materials().get("items", [])
    if not is_main_admin:
        study_materials = [m for m in study_materials if m.get("uploaded_by") == session["username"]]

    return dict(
        content=content, admissions=admissions, accounts=accounts,
        college=college, current_account=current_account,
        is_main_admin=is_main_admin,
        my_class=my_class, my_class_key=current_account.get("class_key"),
        my_class_students=my_class_students, my_class_attendance_dates=my_class_attendance_dates,
        my_class_attendance_pct=my_class_attendance_pct, my_class_attendance_table=my_class_attendance_table,
        all_classes=classrooms, analytics=analytics, custom_qa_items=custom_qa_items,
        teacher_unanswered=teacher_unanswered,
        subjects_data=subjects_data, dash_stats=dash_stats, study_materials=study_materials
    )


@app.route("/admin", methods=["GET"])
@main_admin_required
def admin_dashboard():
    ctx = _build_dashboard_context()
    return render_template("admin.html", panel_role="admin", **ctx)


@app.route("/teacher", methods=["GET"])
@login_required
def teacher_dashboard():
    if session.get("role") == "main_admin":
        return redirect_to_dashboard()
    if session.get("role") != "staff":
        flash("Please log in as a teacher to view this page.")
        return redirect(url_for("login"))
    ctx = _build_dashboard_context()
    return render_template("teacher.html", panel_role="teacher", **ctx)


# ---------- Profile / DP (all roles) ----------

@app.route("/admin/clear-analytics", methods=["POST"])
@main_admin_required
def clear_analytics():
    save_json(ANALYTICS_PATH, {"topic_counts": {}, "recent_questions": [], "total_questions": 0})
    flash("Chatbot analytics data cleared.")
    return redirect_to_dashboard()


@app.route("/admin/add-custom-qa", methods=["POST"])
@login_required
def add_custom_qa():
    question = (request.form.get("question") or "").strip()
    answer = (request.form.get("answer") or "").strip()
    if not question or not answer:
        flash("Please provide both the question and an answer.")
        return redirect_to_dashboard()

    qa_data = get_custom_qa()
    items = qa_data.get("items", [])
    new_id = (max((item.get("id", 0) for item in items), default=0) + 1)
    items.append({
        "id": new_id,
        "question": question,
        "answer": answer,
        "keywords": extract_keywords(question),
        "added_on": datetime.now().strftime("%d %b %Y, %I:%M %p"),
    })
    qa_data["items"] = items
    save_custom_qa(qa_data)
    flash("Chatbot taught this answer — it will now recognise similar questions.")
    return redirect_to_dashboard()


@app.route("/admin/delete-custom-qa/<int:qa_id>", methods=["POST"])
@login_required
def delete_custom_qa(qa_id):
    qa_data = get_custom_qa()
    qa_data["items"] = [item for item in qa_data.get("items", []) if item.get("id") != qa_id]
    save_custom_qa(qa_data)
    flash("Learned answer removed.")
    return redirect_to_dashboard()


@app.route("/admin/upload-dp", methods=["POST"])
@login_required
def upload_dp():
    file = request.files.get("dp")
    if not file or file.filename == "" or not allowed_image(file.filename):
        flash("Please choose a valid image file (PNG/JPG/JPEG/WEBP).")
        return redirect_to_dashboard()

    try:
        result = cloudinary.uploader.upload(file, folder="college_dp")
        dp_url = result["secure_url"]
    except Exception as e:
        flash(f"Photo upload failed: {e}")
        return redirect_to_dashboard()

    accounts_data = get_accounts()
    for acc in accounts_data["accounts"]:
        if acc["username"] == session["username"]:
            acc["dp_filename"] = dp_url  # now stores a full Cloudinary URL
    save_json(STAFF_ACCOUNTS_PATH, accounts_data)

    flash("Profile photo updated.")
    return redirect_to_dashboard()


@app.route("/admin/upload-hero-photo", methods=["POST"])
@main_admin_required
def upload_hero_photo():
    """Lets the main admin change the homepage's main campus photo
    (used in the Hero banner, About section, and Campus Tour placeholder)
    — the same way a profile DP is updated, just for the whole site."""
    file = request.files.get("hero_photo")
    if not file or file.filename == "" or not allowed_image(file.filename):
        flash("Please choose a valid image file (PNG/JPG/JPEG/WEBP).")
        return redirect_to_dashboard()

    try:
        result = cloudinary.uploader.upload(file, folder="college_hero")
        photo_url = result["secure_url"]
    except Exception as e:
        flash(f"Photo upload failed: {e}")
        return redirect_to_dashboard()

    college = get_data()
    college["hero_image_url"] = photo_url
    save_data(college)

    flash("Campus photo updated — it now shows on the homepage.")
    return redirect_to_dashboard()


@app.route("/admin/set-designation", methods=["POST"])
@main_admin_required
def set_designation():
    designation = request.form.get("designation", "").strip()
    accounts_data = get_accounts()
    for acc in accounts_data["accounts"]:
        if acc["username"] == session["username"]:
            acc["designation"] = designation or None
    save_json(STAFF_ACCOUNTS_PATH, accounts_data)
    flash("Designation updated.")
    return redirect_to_dashboard()


@app.route("/admin/attendance/add-student", methods=["POST"])
@class_teacher_required
def attendance_add_student():
    account = find_account(session["username"])
    class_key = account.get("class_key")
    student_name = (request.form.get("student_name") or "").strip()
    if not student_name:
        flash("Please enter a student name.")
        return redirect_to_dashboard()

    attendance = get_attendance()
    cls = attendance["classes"].setdefault(class_key, {"students": [], "records": {}})
    if student_name not in cls["students"]:
        cls["students"].append(student_name)
        save_attendance(attendance)
        flash(f"'{student_name}' added to the class list.")
    else:
        flash("That student is already in the list.")
    return redirect_to_dashboard()


@app.route("/admin/attendance/remove-student", methods=["POST"])
@class_teacher_required
def attendance_remove_student():
    account = find_account(session["username"])
    class_key = account.get("class_key")
    student_name = (request.form.get("student_name") or "").strip()

    attendance = get_attendance()
    cls = attendance["classes"].setdefault(class_key, {"students": [], "records": {}})
    cls["students"] = [s for s in cls["students"] if s != student_name]
    save_attendance(attendance)
    flash(f"'{student_name}' removed from the class list.")
    return redirect_to_dashboard()


@app.route("/admin/attendance/mark", methods=["POST"])
@class_teacher_required
def attendance_mark():
    account = find_account(session["username"])
    class_key = account.get("class_key")
    att_date = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")

    attendance = get_attendance()
    cls = attendance["classes"].setdefault(class_key, {"students": [], "records": {}})

    day_record = {}
    for student in cls["students"]:
        status = request.form.get(f"status_{student}", "absent")
        day_record[student] = status
    cls["records"][att_date] = day_record
    save_attendance(attendance)
    flash(f"Attendance saved for {att_date}.")
    return redirect_to_dashboard()


# ---------- Subjects & Teacher Mapping ----------

@app.route("/admin/subjects/set-teacher", methods=["POST"])
@main_admin_required
def subjects_set_teacher():
    branch = request.form.get("branch", "")
    semester = request.form.get("semester", "")
    subject = request.form.get("subject", "")
    teacher_name = (request.form.get("teacher_name") or "").strip()

    subjects_data = get_subjects()
    branch_data = subjects_data.get("branches", {}).get(branch)
    if not branch_data or semester not in branch_data.get("semesters", {}):
        flash("Invalid branch or semester.")
        return redirect_to_dashboard()

    branch_data["semesters"][semester].setdefault("teachers", {})
    branch_data["semesters"][semester]["teachers"][subject] = teacher_name
    save_subjects(subjects_data)
    flash(f"'{subject}' teacher set to '{teacher_name}'.")
    return redirect_to_dashboard()


@app.route("/study-material")
def study_material():
    subjects_data = get_subjects()
    return render_template("study_material.html", college=get_data(), subjects_data=subjects_data)


@app.route("/admin/change-password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    account = find_account(session["username"])

    if not check_password_hash(account["password_hash"], current_password):
        flash("Current password is incorrect.")
        return redirect_to_dashboard()

    if len(new_password) < 6:
        flash("New password must be at least 6 characters long.")
        return redirect_to_dashboard()

    if new_password != confirm_password:
        flash("New password and confirm password do not match.")
        return redirect_to_dashboard()

    accounts_data = get_accounts()
    for acc in accounts_data["accounts"]:
        if acc["username"] == session["username"]:
            acc["password_hash"] = generate_password_hash(new_password)
    save_json(STAFF_ACCOUNTS_PATH, accounts_data)

    flash("Password changed successfully.")
    return redirect_to_dashboard()


# ---------- Staff / Class Rep management (main admin only) ----------

@app.route("/admin/add-staff", methods=["POST"])
@main_admin_required
def add_staff():
    accounts_data = get_accounts()
    username = request.form.get("username", "").strip()

    if find_account(username):
        flash("That username already exists.")
        return redirect_to_dashboard()

    new_id = (max([a["id"] for a in accounts_data["accounts"]], default=0)) + 1
    accounts_data["accounts"].append({
        "id": new_id,
        "username": username,
        "password_hash": generate_password_hash(request.form.get("password", "")),
        "full_name": request.form.get("full_name", "").strip(),
        "role": "staff",
        "department": request.form.get("department", "").strip(),
        "subject": request.form.get("subject", "").strip(),
        "class_key": request.form.get("class_key") or None,
        "designation": None,
        "dp_filename": None,
    })
    save_json(STAFF_ACCOUNTS_PATH, accounts_data)
    flash(f"Staff account '{username}' created.")
    return redirect_to_dashboard()


@app.route("/admin/delete-staff/<int:item_id>")
@main_admin_required
def delete_staff(item_id):
    accounts_data = get_accounts()
    target = next((a for a in accounts_data["accounts"] if a["id"] == item_id), None)
    if target and target["role"] == "main_admin":
        flash("Cannot delete the main admin account.")
        return redirect_to_dashboard()
    accounts_data["accounts"] = [a for a in accounts_data["accounts"] if a["id"] != item_id]
    save_json(STAFF_ACCOUNTS_PATH, accounts_data)
    flash("Account removed.")
    return redirect_to_dashboard()


# ---------- Class Representative: timetable + notices ----------

@app.route("/admin/update-timetable", methods=["POST"])
@class_teacher_required
def update_timetable():
    account = find_account(session["username"])
    class_key = account.get("class_key")
    if not class_key:
        flash("No class assigned to your account.")
        return redirect_to_dashboard()

    times = request.form.getlist("tt_time")
    subjects = request.form.getlist("tt_subject")
    teachers = request.form.getlist("tt_teacher")

    rows = []
    for t, s, tc in zip(times, subjects, teachers):
        t, s, tc = t.strip(), s.strip(), tc.strip()
        if t or s or tc:  # skip fully-empty rows
            rows.append({"time": t, "subject": s, "teacher": tc})

    classrooms = get_classrooms()
    if class_key in classrooms["classes"]:
        classrooms["classes"][class_key]["timetable_rows"] = rows
        save_json(CLASSROOM_DATA_PATH, classrooms)
        flash("Timetable updated.")
    return redirect_to_dashboard()


@app.route("/admin/add-class-notice", methods=["POST"])
@class_teacher_required
def add_class_notice():
    account = find_account(session["username"])
    class_key = account.get("class_key")
    if not class_key:
        flash("No class assigned to your account.")
        return redirect_to_dashboard()

    classrooms = get_classrooms()
    cls = classrooms["classes"].get(class_key)
    if cls:
        notices = cls.setdefault("notices", [])
        new_id = (max([n["id"] for n in notices], default=0)) + 1
        notices.append({
            "id": new_id,
            "title": request.form.get("title", "").strip(),
            "message": request.form.get("message", "").strip(),
        })
        save_json(CLASSROOM_DATA_PATH, classrooms)
        flash("Notice added.")
    return redirect_to_dashboard()


@app.route("/admin/delete-class-notice/<int:item_id>")
@class_teacher_required
def delete_class_notice(item_id):
    account = find_account(session["username"])
    class_key = account.get("class_key")
    classrooms = get_classrooms()
    cls = classrooms["classes"].get(class_key)
    if cls:
        cls["notices"] = [n for n in cls.get("notices", []) if n["id"] != item_id]
        save_json(CLASSROOM_DATA_PATH, classrooms)
        flash("Notice deleted.")
    return redirect_to_dashboard()


# ---------- Edit college info (main admin only) ----------

@app.route("/admin/edit-college-info", methods=["POST"])
@main_admin_required
def edit_college_info():
    d = get_data()
    d["college_name"] = request.form.get("college_name", d.get("college_name"))
    d["about"] = request.form.get("about", d.get("about"))

    d.setdefault("contact", {})
    d["contact"]["address"] = request.form.get("address", d["contact"].get("address"))
    d["contact"]["phone"] = request.form.get("phone", d["contact"].get("phone"))
    d["contact"]["email"] = request.form.get("email", d["contact"].get("email"))

    d.setdefault("timings", {})
    d["timings"]["college_hours"] = request.form.get("college_hours", d["timings"].get("college_hours"))
    d["timings"]["office_hours"] = request.form.get("office_hours", d["timings"].get("office_hours"))

    d.setdefault("admission_process", {})
    d["admission_process"]["eligibility"] = request.form.get("eligibility", d["admission_process"].get("eligibility"))
    d["admission_process"]["how_to_apply"] = request.form.get("how_to_apply", d["admission_process"].get("how_to_apply"))

    d.setdefault("social_links", {})
    d["social_links"]["facebook"] = request.form.get("facebook", d["social_links"].get("facebook", ""))
    d["social_links"]["instagram"] = request.form.get("instagram", d["social_links"].get("instagram", ""))
    d["social_links"]["youtube"] = request.form.get("youtube", d["social_links"].get("youtube", ""))

    save_data(d)
    flash("College information updated.")
    return redirect_to_dashboard()


# ---------- News / Events / Gallery / Testimonials / Downloads (admin + staff) ----------

@app.route("/admin/add-news", methods=["POST"])
@main_admin_required
def add_news():
    content = get_content()
    news_list = content.setdefault("news", [])
    new_id = (max([n["id"] for n in news_list], default=0)) + 1
    news_list.append({
        "id": new_id,
        "title": request.form.get("title", "").strip(),
        "description": request.form.get("description", "").strip(),
        "date": request.form.get("date") or datetime.now().strftime("%Y-%m-%d"),
    })
    save_json(CONTENT_DATA_PATH, content)
    flash("News added successfully.")
    return redirect_to_dashboard()


@app.route("/admin/add-event", methods=["POST"])
@main_admin_required
def add_event():
    content = get_content()
    events_list = content.setdefault("events", [])
    new_id = (max([e["id"] for e in events_list], default=0)) + 1

    banner_url = ""
    banner = request.files.get("banner")
    if banner and banner.filename and allowed_image(banner.filename):
        try:
            result = cloudinary.uploader.upload(banner, folder="college_events")
            banner_url = result["secure_url"]
        except Exception as e:
            flash(f"Event saved, but banner upload failed: {e}")

    events_list.append({
        "id": new_id,
        "title": request.form.get("title", "").strip(),
        "description": request.form.get("description", "").strip(),
        "date": request.form.get("date") or datetime.now().strftime("%Y-%m-%d"),
        "banner_url": banner_url,
    })
    save_json(CONTENT_DATA_PATH, content)
    flash("Event added successfully.")
    return redirect_to_dashboard()


@app.route("/admin/delete-item/<kind>/<int:item_id>")
@main_admin_required
def delete_item(kind, item_id):
    content = get_content()
    if kind in ("news", "events", "testimonials", "downloads"):
        content[kind] = [x for x in content.get(kind, []) if x["id"] != item_id]
        save_json(CONTENT_DATA_PATH, content)
        flash("Deleted successfully.")
    return redirect_to_dashboard()


@app.route("/admin/upload-photo", methods=["POST"])
@main_admin_required
def upload_photo():
    file = request.files.get("photo")
    caption = request.form.get("caption", "").strip()

    if not file or file.filename == "":
        flash("No file selected.")
        return redirect_to_dashboard()
    if not allowed_image(file.filename):
        flash("Only PNG/JPG/JPEG/WEBP images are allowed.")
        return redirect_to_dashboard()

    try:
        result = cloudinary.uploader.upload(file, folder="college_gallery")
        photo_url = result["secure_url"]
        public_id = result["public_id"]
    except Exception as e:
        flash(f"Photo upload failed: {e}")
        return redirect_to_dashboard()

    content = get_content()
    gallery = content.setdefault("gallery", [])
    new_id = (max([g["id"] for g in gallery], default=0)) + 1
    gallery.append({"id": new_id, "url": photo_url, "public_id": public_id, "caption": caption})
    save_json(CONTENT_DATA_PATH, content)

    flash("Photo uploaded successfully.")
    return redirect_to_dashboard()


@app.route("/admin/delete-photo/<int:item_id>")
@main_admin_required
def delete_photo(item_id):
    content = get_content()
    gallery = content.get("gallery", [])
    photo = next((g for g in gallery if g["id"] == item_id), None)
    if photo:
        if photo.get("public_id"):
            try:
                cloudinary.uploader.destroy(photo["public_id"])
            except Exception:
                pass  # if Cloudinary delete fails, still remove it from our list
        content["gallery"] = [g for g in gallery if g["id"] != item_id]
        save_json(CONTENT_DATA_PATH, content)
        flash("Photo deleted.")
    return redirect_to_dashboard()


@app.route("/admin/delete-admission/<int:item_id>")
@main_admin_required
def delete_admission(item_id):
    admissions = get_admissions()
    admissions["submissions"] = [s for s in admissions.get("submissions", []) if s["id"] != item_id]
    save_json(ADMISSIONS_DATA_PATH, admissions)
    flash("Application deleted.")
    return redirect_to_dashboard()


@app.route("/admin/add-testimonial", methods=["POST"])
@main_admin_required
def add_testimonial():
    content = get_content()
    items = content.setdefault("testimonials", [])
    new_id = (max([t["id"] for t in items], default=0)) + 1

    photo_url = ""
    photo = request.files.get("photo")
    if photo and photo.filename and allowed_image(photo.filename):
        try:
            result = cloudinary.uploader.upload(photo, folder="college_testimonials")
            photo_url = result["secure_url"]
        except Exception as e:
            flash(f"Testimonial saved, but photo upload failed: {e}")

    items.append({
        "id": new_id,
        "name": request.form.get("name", "").strip(),
        "course": request.form.get("course", "").strip(),
        "batch": request.form.get("batch", "").strip(),
        "message": request.form.get("message", "").strip(),
        "photo_url": photo_url,
    })
    save_json(CONTENT_DATA_PATH, content)
    flash("Testimonial added.")
    return redirect_to_dashboard()


@app.route("/admin/upload-download", methods=["POST"])
@main_admin_required
def upload_download():
    file = request.files.get("document")
    title = request.form.get("title", "").strip()

    if not file or file.filename == "" or not allowed_doc(file.filename):
        flash("Please choose a valid PDF file.")
        return redirect_to_dashboard()

    os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    file.save(os.path.join(DOWNLOADS_FOLDER, filename))

    content = get_content()
    items = content.setdefault("downloads", [])
    new_id = (max([x["id"] for x in items], default=0)) + 1
    items.append({"id": new_id, "title": title or file.filename, "filename": filename})
    save_json(CONTENT_DATA_PATH, content)

    flash("Document uploaded.")
    return redirect_to_dashboard()


@app.route("/admin/upload-material", methods=["POST"])
@login_required
def upload_material():
    file = request.files.get("material")
    title = request.form.get("title", "").strip()
    material_type = request.form.get("material_type", "Notes")

    if not file or file.filename == "" or "." not in file.filename or \
            file.filename.rsplit(".", 1)[1].lower() not in ALLOWED_MATERIAL_EXT:
        flash("Please choose a valid PDF, PPT, or DOC file.")
        return redirect_to_dashboard()

    os.makedirs(STUDY_MATERIALS_FOLDER, exist_ok=True)
    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    file.save(os.path.join(STUDY_MATERIALS_FOLDER, filename))

    account = find_account(session["username"])
    data = get_study_materials()
    items = data.setdefault("items", [])
    new_id = (max([x["id"] for x in items], default=0)) + 1
    items.append({
        "id": new_id,
        "title": title or file.filename,
        "filename": filename,
        "material_type": material_type,
        "subject": account.get("subject") if account else None,
        "uploaded_by": session["username"],
        "uploaded_by_name": session.get("full_name", session["username"]),
        "date": datetime.now().strftime("%Y-%m-%d"),
    })
    save_study_materials(data)

    flash("Study material uploaded.")
    return redirect_to_dashboard()


@app.route("/admin/delete-material/<int:item_id>")
@login_required
def delete_material(item_id):
    data = get_study_materials()
    items = data.get("items", [])
    material = next((m for m in items if m["id"] == item_id), None)
    if material:
        # Teachers can only delete their own uploads; the main admin can delete any.
        if session.get("role") != "main_admin" and material.get("uploaded_by") != session["username"]:
            flash("You can only delete materials you uploaded.")
            return redirect_to_dashboard()
        try:
            os.remove(os.path.join(STUDY_MATERIALS_FOLDER, material["filename"]))
        except OSError:
            pass
        data["items"] = [m for m in items if m["id"] != item_id]
        save_study_materials(data)
        flash("Study material deleted.")
    return redirect_to_dashboard()


def to_youtube_embed_url(url):
    """Auto-convert a normal YouTube link (watch?v=, youtu.be/, shorts/)
    into the embeddable format so it always plays correctly in an <iframe>."""
    url = (url or "").strip()
    if not url:
        return ""

    # Already an embed link — leave as is.
    if "youtube.com/embed/" in url:
        return url

    video_id = None
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|shorts/))([A-Za-z0-9_-]{6,})", url)
    if m:
        video_id = m.group(1)

    if video_id:
        return f"https://www.youtube.com/embed/{video_id}"

    return url  # not a recognised YouTube link — save whatever was given


@app.route("/admin/set-video", methods=["POST"])
@main_admin_required
def set_video():
    content = get_content()
    content["video_url"] = to_youtube_embed_url(request.form.get("video_url", ""))
    content["video_type"] = "youtube"
    save_json(CONTENT_DATA_PATH, content)
    flash("Video updated.")
    return redirect_to_dashboard()


@app.route("/admin/upload-video", methods=["POST"])
@main_admin_required
def upload_video():
    file = request.files.get("video_file")

    if not file or file.filename == "":
        flash("No video file selected.")
        return redirect_to_dashboard()
    if not allowed_video(file.filename):
        flash("Only MP4/WEBM/MOV video files are allowed.")
        return redirect_to_dashboard()

    os.makedirs(VIDEO_FOLDER, exist_ok=True)
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{filename}"
    file.save(os.path.join(VIDEO_FOLDER, filename))

    content = get_content()
    content["video_file"] = filename
    content["video_type"] = "file"
    save_json(CONTENT_DATA_PATH, content)

    flash("Video uploaded successfully.")
    return redirect_to_dashboard()


if __name__ == "__main__":
    os.makedirs(DP_FOLDER, exist_ok=True)
    os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
    os.makedirs(VIDEO_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000, host="0.0.0.0")
