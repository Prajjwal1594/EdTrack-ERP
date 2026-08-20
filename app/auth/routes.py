from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.models import (User, Student, Course, Subject, Assignment, Enquiry, AdmissionApplication,
                        Event, Grievance, LibraryBook, BookIssue, HostelRoom, HostelAllocation,
                        TransportRoute, Exam, Grade, FeePayment, LeaveApplication, AcademicTerm, AuditLog)
from sqlalchemy import func
from app import db
from datetime import datetime, timedelta


@bp.route('/')
def index():
    return redirect(url_for('auth.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET' and current_user.is_authenticated:
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        if current_user.is_authenticated:
            logout_user()

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            try:
                user.last_login = datetime.utcnow()
                log = AuditLog(
                    college_id=user.college_id,
                    user_id=user.id,
                    action="LOGIN_SUCCESS",
                    module="Auth",
                    ip_address=request.remote_addr,
                    details=f"User {user.name} ({user.email}) logged in as {user.role_display_name}.",
                    severity="info"
                )
                db.session.add(log)
                db.session.commit()
            except Exception:
                db.session.rollback()

            next_page = request.args.get('next')
            if next_page and next_page not in ['/fees/', '/fees', '/login']:
                return redirect(next_page)
            return redirect(url_for('auth.dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


ROLE_DASHBOARD_METADATA = {
    'it_admin': {
        'title': 'IT Administrator', 'category': 'Platform', 'icon': 'fas fa-network-wired',
        'description': 'System infrastructure, user access management, server health, and security controls.',
        'metrics': [
            {'label': 'Active Users', 'value': '1,420', 'icon': 'fas fa-users', 'subtext': '99.8% Uptime'},
            {'label': 'DB Health', 'value': 'Optimal', 'icon': 'fas fa-database', 'subtext': 'Auto-backup active'},
            {'label': 'Security Logs', 'value': '0 Threats', 'icon': 'fas fa-shield-alt', 'subtext': 'SSL & Firewall active'},
            {'label': 'System Load', 'value': '12%', 'icon': 'fas fa-server', 'subtext': 'Normal CPU usage'}
        ],
        'actions': [
            {'name': 'User Provisioning', 'icon': 'fas fa-user-plus', 'description': 'Manage system user accounts, credential resets, and role assignments.'},
            {'name': 'Audit & System Logs', 'icon': 'fas fa-shield-halved', 'description': 'Review authentication history, API usage metrics, and security logs.'},
            {'name': 'Database Maintenance', 'icon': 'fas fa-server', 'description': 'Monitor database connections, migration statuses, and query performance.'}
        ]
    },
    'principal': {
        'title': 'College Principal', 'category': 'Leadership', 'icon': 'fas fa-user-tie',
        'description': 'Institutional oversight, academic performance tracking, faculty leadership, and policy enforcement.',
        'metrics': [
            {'label': 'Total Enrollment', 'value': '2,850', 'icon': 'fas fa-graduation-cap', 'subtext': '+8.5% YoY Growth'},
            {'label': 'Avg Attendance', 'value': '91.4%', 'icon': 'fas fa-clipboard-check', 'subtext': 'Above target threshold'},
            {'label': 'Faculty Count', 'value': '124', 'icon': 'fas fa-chalkboard-teacher', 'subtext': 'All departments staffed'},
            {'label': 'Pass Percentage', 'value': '94.2%', 'icon': 'fas fa-chart-line', 'subtext': 'Latest term results'}
        ],
        'actions': [
            {'name': 'Institutional Performance', 'icon': 'fas fa-chart-pie', 'description': 'Analyze overall campus pass rates, attendance trends, and departmental growth.'},
            {'name': 'Faculty & Staff Review', 'icon': 'fas fa-user-check', 'description': 'Oversee teaching assignments, workload distribution, and performance reports.'},
            {'name': 'Policy & Approvals', 'icon': 'fas fa-file-signature', 'description': 'Review institutional policy updates, major leave approvals, and academic calendars.'}
        ]
    },
    'registrar': {
        'title': 'Registrar', 'category': 'Leadership', 'icon': 'fas fa-scroll',
        'description': 'Official academic records, student transcripts, enrollment verification, and degree certification.',
        'metrics': [
            {'label': 'Registered Students', 'value': '2,850', 'icon': 'fas fa-id-card', 'subtext': 'Active academic year'},
            {'label': 'Transcripts Issued', 'value': '342', 'icon': 'fas fa-file-pdf', 'subtext': 'This semester'},
            {'label': 'Degree Approvals', 'value': '480', 'icon': 'fas fa-award', 'subtext': 'Pending graduation'},
            {'label': 'Enrollment Verifications', 'value': '98%', 'icon': 'fas fa-check-double', 'subtext': 'Verified records'}
        ],
        'actions': [
            {'name': 'Transcript Processing', 'icon': 'fas fa-file-invoice', 'description': 'Generate and verify official academic transcripts and bonafide certificates.'},
            {'name': 'Course & Degree Registration', 'icon': 'fas fa-book-bookmark', 'description': 'Manage student course registrations, add/drop periods, and degree audits.'},
            {'name': 'Academic Year Archiving', 'icon': 'fas fa-box-archive', 'description': 'Maintain permanent student history, roll numbers, and graduation records.'}
        ]
    },
    'hod': {
        'title': 'Head of Department (HOD)', 'category': 'Leadership', 'icon': 'fas fa-building-columns',
        'description': 'Departmental curriculum management, faculty workload balancing, course completion, and student progress.',
        'metrics': [
            {'label': 'Dept Students', 'value': '420', 'icon': 'fas fa-users-rectangle', 'subtext': 'Computer Science'},
            {'label': 'Faculty Members', 'value': '18', 'icon': 'fas fa-chalkboard-user', 'subtext': 'Full-time faculty'},
            {'label': 'Syllabus Completion', 'value': '88%', 'icon': 'fas fa-list-progress', 'subtext': 'On track for finals'},
            {'label': 'Defaulter Count', 'value': '14', 'icon': 'fas fa-exclamation-triangle', 'subtext': 'Low attendance alert'}
        ],
        'actions': [
            {'name': 'Curriculum & Syllabi', 'icon': 'fas fa-book-open', 'description': 'Review course offerings, lesson plans, learning outcomes, and subject assignments.'},
            {'name': 'Workload Balancing', 'icon': 'fas fa-scale-balanced', 'description': 'Monitor teaching hours, lab supervision, and substitute faculty coverage.'},
            {'name': 'Department Performance', 'icon': 'fas fa-square-poll-vertical', 'description': 'Inspect student attendance trends, internal marks distributions, and backlogs.'}
        ]
    },
    'admission_officer': {
        'title': 'Admission Officer', 'category': 'Operations', 'icon': 'fas fa-user-plus',
        'description': 'Student recruitment, lead pipeline, application verification, and enrollment processing.',
        'metrics': [
            {'label': 'Total Enquiries', 'value': '1,280', 'icon': 'fas fa-headset', 'subtext': 'Current season'},
            {'label': 'Applications Received', 'value': '640', 'icon': 'fas fa-file-lines', 'subtext': 'Online & walk-in'},
            {'label': 'Approved Admissions', 'value': '320', 'icon': 'fas fa-user-check', 'subtext': 'Enrolled students'},
            {'label': 'Conversion Rate', 'value': '50%', 'icon': 'fas fa-bullseye', 'subtext': '+4% vs last year'}
        ],
        'actions': [
            {'name': 'Lead & Enquiry Pipeline', 'icon': 'fas fa-filter', 'description': 'Track website, phone, and walk-in enquiries through the admission funnel.'},
            {'name': 'Application Review', 'icon': 'fas fa-id-card-clip', 'description': 'Verify submitted documents, academic history, and eligibility requirements.'},
            {'name': 'Onboarding & Roll No.', 'icon': 'fas fa-user-graduate', 'description': 'Confirm initial fee payments and assign new students to batches and sections.'}
        ]
    },
    'examination_officer': {
        'title': 'Examination Officer', 'category': 'Operations', 'icon': 'fas fa-file-signature',
        'description': 'Midterm & final exam scheduling, question paper blueprints, hall tickets, and mark entry validation.',
        'metrics': [
            {'label': 'Exams Scheduled', 'value': '48', 'icon': 'fas fa-calendar-check', 'subtext': 'Upcoming finals'},
            {'label': 'Hall Tickets Issued', 'value': '2,400', 'icon': 'fas fa-ticket', 'subtext': '100% generated'},
            {'label': 'Marks Entered', 'value': '86%', 'icon': 'fas fa-pen-to-square', 'subtext': 'Faculty submission'},
            {'label': 'Revaluation Requests', 'value': '12', 'icon': 'fas fa-rotate-left', 'subtext': 'Under review'}
        ],
        'actions': [
            {'name': 'Exam Scheduling & Halls', 'icon': 'fas fa-building', 'description': 'Allocate exam centers, seating arrangements, and invigilation rosters.'},
            {'name': 'Question Bank & Moderation', 'icon': 'fas fa-file-circle-question', 'description': 'Oversee question paper blueprints, moderation, and secure distribution.'},
            {'name': 'Results & Grade Sheets', 'icon': 'fas fa-calculator', 'description': 'Validate faculty mark entries, compute GPA/CGPA, and issue official grade sheets.'}
        ]
    },
    'course_coordinator': {
        'title': 'Course Coordinator', 'category': 'Academic', 'icon': 'fas fa-diagram-project',
        'description': 'Subject curriculum alignment, assessment standards, learning outcomes, and section synchronization.',
        'metrics': [
            {'label': 'Coordinated Courses', 'value': '6', 'icon': 'fas fa-cubes', 'subtext': 'Core curriculum'},
            {'label': 'Active Sections', 'value': '12', 'icon': 'fas fa-layer-group', 'subtext': 'Across semesters'},
            {'label': 'Assignments Approved', 'value': '24', 'icon': 'fas fa-tasks', 'subtext': 'Aligned with syllabus'},
            {'label': 'Avg Completion', 'value': '92%', 'icon': 'fas fa-chart-simple', 'subtext': 'Section progress'}
        ],
        'actions': [
            {'name': 'Course Blueprinting', 'icon': 'fas fa-book', 'description': 'Define course goals, required textbooks, assignment rubrics, and exam standards.'},
            {'name': 'Section Harmony', 'icon': 'fas fa-code-branch', 'description': 'Ensure all faculty teaching parallel sections maintain identical pace and coverage.'},
            {'name': 'Learning Analytics', 'icon': 'fas fa-chart-line', 'description': 'Analyze student outcome metrics across different batches and subject sections.'}
        ]
    },
    'academic_advisor': {
        'title': 'Academic Advisor', 'category': 'Academic', 'icon': 'fas fa-user-doctor',
        'description': 'Student academic counseling, degree progress monitoring, remedial support, and early warning interventions.',
        'metrics': [
            {'label': 'Assigned Advisees', 'value': '45', 'icon': 'fas fa-users-gear', 'subtext': 'Undergraduate students'},
            {'label': 'At-Risk Students', 'value': '3', 'icon': 'fas fa-triangle-exclamation', 'subtext': 'Early warning alerts'},
            {'label': 'Counseling Sessions', 'value': '28', 'icon': 'fas fa-comments', 'subtext': 'Completed this term'},
            {'label': 'Improvement Rate', 'value': '85%', 'icon': 'fas fa-arrow-trend-up', 'subtext': 'Post-intervention'}
        ],
        'actions': [
            {'name': 'Advisee Dashboard', 'icon': 'fas fa-address-book', 'description': 'Track individual student GPAs, credit completion, attendance trends, and backlogs.'},
            {'name': 'Intervention Planning', 'icon': 'fas fa-notes-medical', 'description': 'Create targeted study plans, schedule tutoring, and record counseling notes.'},
            {'name': 'Parent & Faculty Liaison', 'icon': 'fas fa-people-arrows', 'description': 'Coordinate academic support between parents, subject teachers, and guardians.'}
        ]
    },
    'librarian': {
        'title': 'Librarian', 'category': 'Services', 'icon': 'fas fa-book-bookmark',
        'description': 'Library cataloging, book circulation, digital repository access, fines management, and e-resources.',
        'metrics': [
            {'label': 'Total Volume Count', 'value': '18,500', 'icon': 'fas fa-books', 'subtext': 'Physical catalog'},
            {'label': 'Active Book Loans', 'value': '340', 'icon': 'fas fa-book-reader', 'subtext': 'Currently issued'},
            {'label': 'Overdue Books', 'value': '18', 'icon': 'fas fa-clock-rotate-left', 'subtext': 'Reminders sent'},
            {'label': 'E-Journal Access', 'value': '4,200', 'icon': 'fas fa-globe', 'subtext': 'Digital repository'}
        ],
        'actions': [
            {'name': 'Book Issue & Return', 'icon': 'fas fa-right-left', 'description': 'Process book loans, renewals, returns, and barcode/RFID circulation.'},
            {'name': 'Catalog & ISBN Registry', 'icon': 'fas fa-barcode', 'description': 'Add new titles, digital dissertations, journal subscriptions, and shelf locations.'},
            {'name': 'Fines & Wallet Deduction', 'icon': 'fas fa-receipt', 'description': 'Track overdue book fines and automatically link deductions to student fee accounts.'}
        ]
    },
    'hostel_warden': {
        'title': 'Hostel Warden', 'category': 'Services', 'icon': 'fas fa-hotel',
        'description': 'Hostel room allocations, student check-in/out, visitor gate passes, mess management, and building maintenance.',
        'metrics': [
            {'label': 'Hostel Occupancy', 'value': '94%', 'icon': 'fas fa-bed', 'subtext': '320 / 340 Beds'},
            {'label': 'Active Gate Passes', 'value': '12', 'icon': 'fas fa-door-open', 'subtext': 'Outing approved'},
            {'label': 'Maintenance Tickets', 'value': '4', 'icon': 'fas fa-wrench', 'subtext': 'In progress'},
            {'label': 'Mess Meals Served', 'value': '960/day', 'icon': 'fas fa-utensils', 'subtext': '3 meals daily'}
        ],
        'actions': [
            {'name': 'Room Allocation & Occupancy', 'icon': 'fas fa-key', 'description': 'Assign hostel blocks, rooms, and beds; manage roommate preferences and check-ins.'},
            {'name': 'Outing & Gate Pass Approvals', 'icon': 'fas fa-passport', 'description': 'Review student leave and weekend outing requests with automated parent SMS alerts.'},
            {'name': 'Hostel Safety & Maintenance', 'icon': 'fas fa-shield-virus', 'description': 'Oversee room inspections, incident reporting, visitor logs, and repair work orders.'}
        ]
    },
    'transport_manager': {
        'title': 'Transport Manager', 'category': 'Services', 'icon': 'fas fa-bus-simple',
        'description': 'Bus fleet management, route scheduling, driver records, student route allocations, and vehicle safety.',
        'metrics': [
            {'label': 'Active Fleet Buses', 'value': '14', 'icon': 'fas fa-bus', 'subtext': 'All routes operational'},
            {'label': 'Commuter Students', 'value': '620', 'icon': 'fas fa-users-line', 'subtext': 'Assigned bus passes'},
            {'label': 'Route Coverage', 'value': '8 Routes', 'icon': 'fas fa-route', 'subtext': 'City & suburbs'},
            {'label': 'Vehicle Maintenance', 'value': '100%', 'icon': 'fas fa-gears', 'subtext': 'Fitness certified'}
        ],
        'actions': [
            {'name': 'Route Creation & Stops', 'icon': 'fas fa-map-location-dot', 'description': 'Manage bus routes, pickup points, timing schedules, and driver assignments.'},
            {'name': 'Student Route Allocation', 'icon': 'fas fa-address-card', 'description': 'Assign commuting students to routes and manage transport fee billing.'},
            {'name': 'Fleet Safety & Maintenance', 'icon': 'fas fa-oil-can', 'description': 'Log vehicle fuel records, insurance renewal dates, permit expiries, and service checks.'}
        ]
    },
    'placement_officer': {
        'title': 'Placement Officer', 'category': 'Services', 'icon': 'fas fa-briefcase',
        'description': 'Corporate relations, placement drives, student resume building, eligibility shortlists, and job offers.',
        'metrics': [
            {'label': 'Partner Companies', 'value': '48', 'icon': 'fas fa-city', 'subtext': 'Recruiting partners'},
            {'label': 'Placement Drives', 'value': '16', 'icon': 'fas fa-calendar-week', 'subtext': 'Scheduled this season'},
            {'label': 'Offers Issued', 'value': '185', 'icon': 'fas fa-file-contract', 'subtext': 'Avg Package 8.2 LPA'},
            {'label': 'Placement Rate', 'value': '88.5%', 'icon': 'fas fa-circle-check', 'subtext': 'Eligible batch'}
        ],
        'actions': [
            {'name': 'Company & Job Drives', 'icon': 'fas fa-building-user', 'description': 'Manage corporate profiles, job postings, salary packages, and campus interview dates.'},
            {'name': 'Student Eligibility Shortlisting', 'icon': 'fas fa-user-check', 'description': 'Filter student candidates by CGPA, backlogs, department, and skill certifications.'},
            {'name': 'Offer Tracking & Analytics', 'icon': 'fas fa-chart-column', 'description': 'Record student offer acceptances, package stats, and placement report summaries.'}
        ]
    },
    'student_affairs': {
        'title': 'Student Affairs Officer', 'category': 'Services', 'icon': 'fas fa-people-roof',
        'description': 'Campus extracurricular activities, student clubs, grievance redressal, anti-ragging undertakings, and campus welfare.',
        'metrics': [
            {'label': 'Active Student Clubs', 'value': '14', 'icon': 'fas fa-icons', 'subtext': 'Cultural & Technical'},
            {'label': 'Events Organized', 'value': '32', 'icon': 'fas fa-champagne-glasses', 'subtext': 'This academic year'},
            {'label': 'Grievances Resolved', 'value': '98%', 'icon': 'fas fa-hand-holding-heart', 'subtext': 'Resolved within SLA'},
            {'label': 'Micro-Credentials', 'value': '240', 'icon': 'fas fa-award', 'subtext': 'Certificates awarded'}
        ],
        'actions': [
            {'name': 'Events & Club Management', 'icon': 'fas fa-calendar-plus', 'description': 'Approve campus events, manage club registrations, student leadership, and participation.'},
            {'name': 'Grievance & Welfare Desk', 'icon': 'fas fa-shield-heart', 'description': 'Review confidential student feedback, anti-ragging compliance, and support tickets.'},
            {'name': 'Micro-Credential Issuance', 'icon': 'fas fa-award', 'description': 'Award digital extracurricular certificates for soft-skills, sports, and leadership achievements.'}
        ]
    },
    'alumni': {
        'title': 'Alumni', 'category': 'Users', 'icon': 'fas fa-user-graduate',
        'description': 'Graduate network, alumni directory, career updates, mentorship, and institution engagement.',
        'metrics': [
            {'label': 'Graduation Batch', 'value': 'Class of 2023', 'icon': 'fas fa-graduation-cap', 'subtext': 'B.Tech CS'},
            {'label': 'Network Alumni', 'value': '4,500+', 'icon': 'fas fa-users-view-finder', 'subtext': 'Global network'},
            {'label': 'Reunions & Events', 'value': '3 Upcoming', 'icon': 'fas fa-calendar-days', 'subtext': 'Annual meet'},
            {'label': 'Mentorship Programs', 'value': 'Active', 'icon': 'fas fa-user-nurse', 'subtext': 'Guiding juniors'}
        ],
        'actions': [
            {'name': 'Alumni Directory & Connect', 'icon': 'fas fa-address-card', 'description': 'Connect with fellow graduates, filter by company, location, and industry sector.'},
            {'name': 'Career & Mentorship', 'icon': 'fas fa-hands-holding-child', 'description': 'Share job referrals, conduct webinars, and mentor current college students.'},
            {'name': 'Transcript & Verification', 'icon': 'fas fa-file-certificate', 'description': 'Request official duplicate degree certificates, transcripts, and alumni verification.'}
        ]
    },
    'employer': {
        'title': 'Employer / Corporate Recruiter', 'category': 'Users', 'icon': 'fas fa-building-flag',
        'description': 'Campus recruitment portal, candidate shortlisting, interview scheduling, and job offer uploads.',
        'metrics': [
            {'label': 'Posted Job Roles', 'value': '4', 'icon': 'fas fa-rectangle-ad', 'subtext': 'Software Engineer & QA'},
            {'label': 'Total Applicants', 'value': '142', 'icon': 'fas fa-users', 'subtext': 'Campus candidates'},
            {'label': 'Shortlisted Candidates', 'value': '28', 'icon': 'fas fa-user-check', 'subtext': 'Interview round'},
            {'label': 'Offers Sent', 'value': '6', 'icon': 'fas fa-envelope-open-text', 'subtext': 'Pending acceptance'}
        ],
        'actions': [
            {'name': 'Job Postings & Requirements', 'icon': 'fas fa-file-pen', 'description': 'Publish new campus job roles, required CGPA cutoffs, and salary compensation details.'},
            {'name': 'Applicant Screening', 'icon': 'fas fa-users-rectangle', 'description': 'Review student profiles, GitHub projects, transcripts, and micro-credential badges.'},
            {'name': 'Interview & Offer Upload', 'icon': 'fas fa-paper-plane', 'description': 'Schedule interview slots with placement cell and upload official job offer letters.'}
        ]
    }
}


@bp.route('/dashboard')
@login_required
def dashboard():
    role = current_user.role
    if role == 'superadmin':
        return redirect(url_for('superadmin.dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'faculty':
        return redirect(url_for('faculty.dashboard'))
    elif role == 'student':
        return redirect(url_for('student.dashboard'))
    elif role == 'accountant':
        return redirect(url_for('accountant.dashboard'))
    elif role == 'hr':
        return redirect(url_for('hr.dashboard'))
    elif role == 'it_admin':
        return redirect(url_for('it_admin.dashboard'))
    elif role == 'parent':
        return redirect(url_for('parent.dashboard'))

    # Gather metrics for custom role dashboards
    total_students = Student.query.count()
    total_faculty = User.query.filter_by(role='faculty').count()
    total_courses = Course.query.count()
    total_subjects = Subject.query.count()
    total_assignments = Assignment.query.count()
    total_enquiries = Enquiry.query.count()
    total_applications = AdmissionApplication.query.count()
    total_events = Event.query.count()
    total_grievances = Grievance.query.count()
    total_books = LibraryBook.query.count()
    total_issues = BookIssue.query.filter_by(status='issued').count()
    overdue_count = BookIssue.query.filter_by(status='overdue').count()
    total_rooms = HostelRoom.query.count()
    total_allocations = HostelAllocation.query.count()
    total_routes = TransportRoute.query.count()
    total_exams = Exam.query.count()
    total_grades = Grade.query.count()
    
    rev = db.session.query(func.sum(FeePayment.amount)).scalar() or 1250000.0
    college_name = current_user.college.name if current_user.college else "EdTrack Institution"

    context = {
        'college_name': college_name,
        'total_students': total_students,
        'total_faculty': total_faculty,
        'total_courses': total_courses,
        'total_subjects': total_subjects,
        'total_assignments': total_assignments,
        'total_enquiries': total_enquiries,
        'total_applications': total_applications,
        'total_events': total_events,
        'total_grievances': total_grievances,
        'total_books': total_books,
        'total_issues': total_issues,
        'overdue_count': overdue_count,
        'total_rooms': total_rooms,
        'total_allocations': total_allocations,
        'total_routes': total_routes,
        'total_exams': total_exams,
        'total_grades': total_grades,
        'total_revenue': float(rev),
        'avg_attendance': 89.2,
        'at_risk_count': 6,
        'faculty_attendance_rate': 96.5,
        'fee_clearance_pct': 92.4,
        'active_terms': AcademicTerm.query.filter_by(is_active=True).count(),
        'occupancy_pct': round((total_allocations / max(total_rooms, 1)) * 100, 1),
        'pending_leaves': LeaveApplication.query.filter_by(status='pending').count()
    }

    if role in ['principal', 'executive']:
        return render_template('roles/principal_dashboard.html', **context)
    elif role in ['registrar']:
        return render_template('roles/registrar_dashboard.html', **context)
    elif role in ['hod']:
        return render_template('roles/hod_dashboard.html', **context)
    elif role in ['admission_officer']:
        return render_template('roles/admission_officer_dashboard.html', **context)
    elif role in ['examination_officer']:
        return render_template('roles/examination_officer_dashboard.html', **context)
    elif role in ['course_coordinator']:
        return render_template('roles/course_coordinator_dashboard.html', **context)
    elif role in ['academic_advisor']:
        return render_template('roles/academic_advisor_dashboard.html', **context)
    elif role in ['librarian']:
        return render_template('roles/librarian_dashboard.html', **context)
    elif role in ['hostel_warden']:
        return render_template('roles/hostel_warden_dashboard.html', **context)
    elif role in ['transport_manager']:
        return render_template('roles/transport_manager_dashboard.html', **context)
    elif role in ['placement_officer']:
        return render_template('roles/placement_officer_dashboard.html', **context)
    elif role in ['student_affairs']:
        return render_template('roles/student_affairs_dashboard.html', **context)
    elif role in ['alumni']:
        return render_template('roles/alumni_dashboard.html', **context)
    elif role in ['employer']:
        return render_template('roles/employer_dashboard.html', **context)
    elif role in ROLE_DASHBOARD_METADATA:
        return render_template('auth/role_dashboard.html', role_info=ROLE_DASHBOARD_METADATA[role])
    
    return redirect(url_for('admin.dashboard'))


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.name = request.form.get('name', current_user.name)
        current_user.phone = request.form.get('phone', current_user.phone)
        new_password = request.form.get('new_password', '').strip()
        if new_password:
            current_password = request.form.get('current_password', '')
            if current_user.check_password(current_password):
                current_user.set_password(new_password)
                flash('Password updated successfully.', 'success')
            else:
                flash('Current password is incorrect.', 'danger')
                return render_template('auth/profile.html')
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('auth.profile'))
    return render_template('auth/profile.html')


@bp.route('/academic-calendar')
@login_required
def academic_calendar():
    college_id = current_user.college_id or 1
    terms = AcademicTerm.query.filter_by(college_id=college_id).order_by(AcademicTerm.start_date.asc()).all()
    events = Event.query.filter_by(college_id=college_id).order_by(Event.event_date.asc()).all()
    
    # If no events exist yet in DB, create standard institutional academic calendar milestones
    if not events:
        now = datetime.utcnow()
        sample_events = [
            Event(college_id=college_id, title="Fall Semester Course Registration", description="Online portal opens for course add/drop and elective selections.", event_date=now, end_date=now + timedelta(days=5), location="Academic Portal", created_by=current_user.id),
            Event(college_id=college_id, title="Commencement of Fall Teaching Session", description="Regular class lectures begin across all undergraduate & postgraduate departments.", event_date=now + timedelta(days=7), location="Campus Lecture Halls", created_by=current_user.id),
            Event(college_id=college_id, title="Mid-Term Examination Window", description="Centralized mid-term assessments and practical evaluation labs.", event_date=now + timedelta(days=45), end_date=now + timedelta(days=52), location="Examination Halls", created_by=current_user.id),
            Event(college_id=college_id, title="Mid-Semester Break & Festivities", description="Diwali & Autumn Inter-College Sports & Cultural Festival.", event_date=now + timedelta(days=60), end_date=now + timedelta(days=67), location="Main Auditorium & Grounds", created_by=current_user.id),
            Event(college_id=college_id, title="End-Term Final Semester Examinations", description="Theory paper evaluations and external viva voice examinations.", event_date=now + timedelta(days=90), end_date=now + timedelta(days=105), location="Examination Complex", created_by=current_user.id),
            Event(college_id=college_id, title="Winter Vacations & Result Declaration", description="Semester grade publishing and winter break for students.", event_date=now + timedelta(days=110), end_date=now + timedelta(days=130), location="College Portal", created_by=current_user.id),
        ]
        for se in sample_events:
            db.session.add(se)
        db.session.commit()
        events = Event.query.filter_by(college_id=college_id).order_by(Event.event_date.asc()).all()

    return render_template('auth/academic_calendar.html', terms=terms, events=events)


@bp.route('/principal/academic-delivery')
@login_required
def principal_academic_delivery():
    total_faculty = User.query.filter_by(role='faculty').count()
    total_courses = Course.query.count()
    total_subjects = Subject.query.count()
    total_assignments = Assignment.query.count()
    return render_template('roles/principal_academic_delivery.html',
                           total_faculty=total_faculty,
                           total_courses=total_courses,
                           total_subjects=total_subjects,
                           total_assignments=total_assignments)


@bp.route('/principal/admissions-growth')
@login_required
def principal_admissions_growth():
    total_students = Student.query.count()
    total_enquiries = Enquiry.query.count()
    total_applications = AdmissionApplication.query.count()
    rev = db.session.query(func.sum(FeePayment.amount)).scalar() or 1250000.0
    return render_template('roles/principal_admissions_growth.html',
                           total_students=total_students,
                           total_enquiries=total_enquiries,
                           total_applications=total_applications,
                           total_revenue=float(rev),
                           fee_clearance_pct=92.4)


@bp.route('/principal/accreditation-audit')
@login_required
def principal_accreditation_audit():
    return render_template('roles/principal_accreditation_audit.html')


@bp.route('/registrar/transcripts')
@login_required
def registrar_transcripts():
    students = User.query.filter_by(role='student').all()
    return render_template('roles/registrar_transcripts.html', students=students)


@bp.route('/hod/department-workload')
@login_required
def hod_workload():
    faculty = User.query.filter_by(role='faculty').all()
    return render_template('roles/hod_workload.html', faculty=faculty)


@bp.route('/admissions/merit-list')
@login_required
def admissions_merit_list():
    applications = AdmissionApplication.query.all()
    return render_template('roles/admissions_merit_list.html', applications=applications)


@bp.route('/exam-officer/hall-tickets')
@login_required
def exam_hall_tickets():
    students = User.query.filter_by(role='student').all()
    return render_template('roles/exam_hall_tickets.html', students=students)


@bp.route('/course-coordinator/co-po')
@login_required
def course_coordinator_copo():
    subjects = Subject.query.all()
    return render_template('roles/course_coordinator_copo.html', subjects=subjects)


@bp.route('/academic-advisor/counseling-logs')
@login_required
def academic_advisor_counseling():
    students = User.query.filter_by(role='student').all()
    return render_template('roles/academic_advisor_counseling.html', students=students)


@bp.route('/librarian/fines-e-resources')
@login_required
def librarian_fines():
    books = LibraryBook.query.all()
    return render_template('roles/librarian_fines.html', books=books)


@bp.route('/warden/mess-inspections')
@login_required
def warden_mess_inspection():
    rooms = HostelRoom.query.all()
    return render_template('roles/warden_mess_inspection.html', rooms=rooms)


@bp.route('/transport/fleet-maintenance')
@login_required
def transport_fleet():
    routes = TransportRoute.query.all()
    return render_template('roles/transport_fleet.html', routes=routes)


@bp.route('/placement/drive-manager')
@login_required
def placement_drives():
    events = Event.query.all()
    return render_template('roles/placement_drives.html', events=events)


@bp.route('/student-affairs/clubs-antiragging')
@login_required
def student_affairs_clubs():
    return render_template('roles/student_affairs_clubs.html')


@bp.route('/alumni/job-referrals')
@login_required
def alumni_referrals():
    return render_template('roles/alumni_referrals.html')


@bp.route('/employer/recruitment-portal')
@login_required
def employer_recruitment():
    students = User.query.filter_by(role='student').all()
    return render_template('roles/employer_recruitment.html', students=students)
