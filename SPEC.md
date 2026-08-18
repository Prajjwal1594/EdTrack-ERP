# SPEC.md — Project Specification

> **Status**: `FINALIZED`
> **Project**: Student Progress Tracker
> **Client**: El'Wood International University

## Vision
A comprehensive, full-featured web application for El'Wood International University that enables faculty to track student grades, assignments, attendance, and performance trends. The system supports multiple user roles (admin, faculty, students, parents) with appropriate access levels, provides automated email notifications, generates PDF grade sheets, supports online exams, in-app messaging, LMS integration, and fee management — all branded to El'Wood International University. Deployable both locally and to the cloud with multi-college support.

## Goals
1. **Multi-role authentication** — Secure login for admins, faculty, students, and parents with role-based access control
2. **Grade management** — Percentage-based (0-100%) grading across multiple subjects, organized by class/section
3. **Assignment tracking** — Faculty create assignments, track submissions, and grade them
4. **Attendance tracking** — Daily attendance recording per class/section with absence reporting
5. **Performance analytics** — Visual trend charts showing student progress over time
6. **Grade sheet generation** — PDF grade sheets containing grades, attendance records, and faculty comments
7. **Email notifications** — Automated alerts for low grades, missed attendance, and unsubmitted assignments
8. **Admin panel** — Manage faculty, semesters, sections, subjects, and academic calendar
9. **Student/parent portals** — Read-only access to view individual progress, grades, and attendance
10. **Mobile-responsive design** — Fully usable on phones and tablets
11. **Configurable academic calendar** — Support for semesters, terms, or quarters
12. **Cloud deployment** — Deployable to cloud infrastructure in addition to local
13. **Multi-college/multi-tenant support** — Support multiple colleges within a single instance
14. **Online exam/test-taking** — Students can take exams and tests online within the platform
15. **Chat and messaging** — In-app messaging between faculty, students, and parents
16. **LMS integration** — Integration with external Learning Management Systems
17. **Payment and fee management** — Track and manage student fee payments
18. **Online admission panel** — Admin interface to fill out admission forms and register new students into the database
19. **Downloadable fee receipts** — PDF fee receipts generated and available for download by all relevant users
20. **"Early Warning" Algorithm** — Predictive algorithm to detect at-risk students based on attendance and assignments, triggering automated intervention emails
21. **Unified Parental Weekly Digest** — Automated weekly background job compiling grades, attendance, and missing fees into one parent email
22. **Micro-Credentialing & Extracurriculars** — Verify and generate digital micro-certificates via WeasyPrint for modern soft-skills
23. **Offline/Low-Bandwidth Capability** — Progressive Web App (PWA) architecture with Service Workers to allow offline attendance and grade recording
24. **In-College Digital Micro-Payments Wallet** — Parent wallet system to handle top-ups and micro-fee deductions (field trips, fines) with automated PDF receipts
25. **Timetable Management** — Full scheduling suite with college-scoped collision detection and weekly views
26. **Advanced Analytics** — Role-based Chart.js dashboards (Admin, Faculty, Parent) for data-driven student monitoring

## Non-Goals (Out of Scope)
_None — all proposed features are in scope for v1._

## Users

### Admin (College Principal / Coordinator)
- Manages faculty accounts
- Configures college settings (academic calendar, semesters, sections, subjects)
- Has full visibility across all faculty and students
- Single or small number of admin users

### Faculty
- Manage their assigned semesters and subjects
- Record grades, attendance, and assignments
- Write grade sheet comments
- One faculty handles multiple subjects
- ~100 students per faculty

### Students
- View their own grades, attendance, and assignments (read-only)
- See performance trends over time
- Access their own grade sheets

### Parents
- View their child's grades, attendance, and progress (read-only)
- Receive email notifications about academic concerns
- Linked to one or more students

## Technical Stack
- **Backend**: Python (Flask)
- **Frontend**: HTML + CSS (server-rendered templates, mobile-responsive)
- **Database**: SQLite (local) / PostgreSQL (cloud)
- **PDF Generation**: Python library (e.g., ReportLab or WeasyPrint)
- **Email**: SMTP-based email sending
- **Charts**: JavaScript charting library (e.g., Chart.js)
- **Messaging**: WebSocket or polling-based in-app chat
- **Deployment**: Local machine + cloud-ready

## Data Model (High-Level)
- **Users** — id, name, email, password_hash, role (admin/faculty/student/parent)
- **Semesters** — id, name (e.g., "Semester 10"), academic_year
- **Sections** — id, semester_id, name (e.g., "A", "B")
- **Subjects** — id, name (e.g., "Mathematics", "English")
- **Faculty-Subject-Section assignments** — which faculty teaches what subject in which section
- **Students** — user_id, section_id, enrollment details
- **Parent-Student links** — parent_id, student_id
- **Grades** — student_id, subject_id, exam_name, score (0-100), date
- **Assignments** — id, subject_id, section_id, title, due_date, created_by
- **Assignment Submissions** — assignment_id, student_id, submitted_at, grade
- **Attendance** — student_id, date, status (present/absent/late), section_id
- **Academic Calendar** — term/semester/quarter config, start/end dates
- **Grade Sheet Comments** — student_id, faculty_id, term, comment

## Branding
- **College Name**: El'Wood International University
- **Branding**: College name and identity displayed throughout the app (login page, headers, grade sheets, PDFs)

## Constraints
- Must support both local and cloud deployment
- SQLite for local, PostgreSQL option for cloud/multi-tenant
- Python/Flask — no JavaScript frameworks (vanilla JS only for interactivity)
- Must handle ~100 students per faculty without performance issues
- Email notifications require SMTP configuration
- LMS integration depends on available APIs from target platforms

## Success Criteria
- [x] Admin can create/manage faculty, semesters, sections, and subjects
- [x] Faculty can record and update grades (percentage-based) for their students
- [x] Faculty can create assignments and track submissions
- [x] Faculty can record daily attendance per section
- [x] Performance trend charts display correctly for individual students
- [x] PDF grade sheets generate with grades, attendance, and faculty comments
- [x] Email notifications fire for low grades, absences, and missing assignments
- [x] Students can log in and view their own progress
- [x] Parents can log in and view their child's progress
- [x] App is mobile-responsive and usable on phones
- [x] Academic calendar is configurable (semesters/terms/quarters)
- [x] All pages display El'Wood International University branding
- [x] App can be deployed to cloud infrastructure
- [x] Multi-college tenancy works with isolated data per college
- [x] Students can take online exams/tests within the platform
- [x] Users can send and receive messages in-app
- [x] LMS integration imports/exports data successfully
- [x] Fee payments can be recorded and tracked per student
- [x] Timetable Management allows scheduling with correct college-scoped relation checks
- [x] Advanced Analytics dashboards provide visualizations for Admin, Faculty, and Parent roles
- [x] Admins can use the online admission panel to register new students
- [x] Users can download fee receipts as PDF documents
- [x] Early Warning algorithm correctly identifies at-risk metrics and dispatches counselor/parent emails
- [x] Weekly Digest background worker successfully compiles and sends unified parent reports every Friday
- [x] Micro-certificates for extracurriculars can be generated into verifiable PDFs
- [x] PWA Service Worker caching enables faculty to input attendance/grades while completely offline and syncs upward on reconnection
- [x] Digital wallet successfully accepts top-ups and deducts micro-fees instantly with automated receipt emails
- [x] Gemini AI Academic Assistant provides context-aware progress insights for students and parents
