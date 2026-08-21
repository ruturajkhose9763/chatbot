# Final integrated project

This build preserves the original college website and existing features, and adds: 
- Teacher mobile verification (optional Twilio SMS; required when a mobile is registered).
- Student accounts created by authorised Teacher/Admin: name, roll number, optional mobile, PIN.
- Student Portal login using Roll Number + PIN.
- Attendance notifications in the Student Portal.
- Attendance summary/history for students.
- Roll number shown in teacher/admin attendance tables.
- Duplicate roll-number protection.

## Run
```bash
pip install -r requirements.txt
python app.py
```

For real teacher OTP SMS, set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER`.
For production also set `SECRET_KEY`, `SITE_URL`, and the existing database/cloud storage environment variables used by the project.
