# Student Account + Attendance System

## Clean flow
1. Main Admin creates a Teacher account and assigns a class.
2. Teacher logs in after mobile verification.
3. Teacher/Admin creates a Student account with Name + Roll No + Mobile + PIN.
4. Student account starts pending mobile verification.
5. OTP is sent when Twilio is configured.
6. Student logs in with Roll No + PIN and completes OTP verification.
7. Teacher marks Present/Absent by Roll No.
8. Attendance is saved by Roll No, with legacy name-based records still readable.
9. Student sees attendance percentage, history and attendance notifications in Student Portal.

## Important
- Main public website was not redesigned.
- Existing college/admin/teacher/chat features remain.
- The old empty attendance/student stores were reset to the clean schema for this fresh build.
- Real SMS OTP requires Twilio environment variables.
