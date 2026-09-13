from flask import render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from functools import wraps
from app.student import bp
from app.models import (Student, Grade, Attendance, Assignment, AssignmentSubmission,
                         AcademicTerm, Exam, ExamSubmission, ExamQuestion, Notification,
                         MicroCredential, FacultyAssignment, Subject, User, FeePayment,
                         FeeType, Announcement, Event, EventRegistration, Feedback,
                         Grievance, AntiRaggingUndertaking, LeaveApplication,
                         StudentDocument, CautionMoney, Section, SoftSkillMetric)
from app import db
from datetime import datetime, date, timedelta
import json
import hashlib


def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Student access required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated)


def get_current_student():
    return Student.query.filter_by(user_id=current_user.id).first()


def get_student_portal_context(student):
    """Compile comprehensive context for the unified Digital Campus ERP student portal."""
    # 1. Course & Session Header Label
    course_name = "B.Tech. (Computer Science & Engineering)"
    if student.course_id and hasattr(student, 'course') and student.course:
        course_name = student.course.name
    elif student.section and hasattr(student.section, 'course') and student.section.course:
        course_name = student.section.course.name
    session_str = student.session or "FCE2026-2027"
    sem_name = student.section.semester_.name if (student.section and student.section.semester_) else "Semester 1"
    course_label = f"{session_str}{course_name}No Shift ({sem_name})"

    # 2. Subject-wise Attendance & Circular Gauge Statistics
    db_total = Attendance.query.filter_by(student_id=student.id).count()
    if db_total > 0:
        db_present = Attendance.query.filter_by(student_id=student.id).filter(Attendance.status.in_(['present', 'late'])).count()
        db_absent = Attendance.query.filter_by(student_id=student.id, status='absent').count()
        total_lectures = db_total
        total_present = db_present
        total_absent = db_absent
        overall_pct = round((db_present / db_total) * 100, 1)
    else:
        total_lectures = 78
        total_present = 76
        total_absent = 2
        overall_pct = 97.4

    # Populate subjects from real section faculty assignments if available
    subjects_data = []
    if student.section_id:
        fa_list = FacultyAssignment.query.filter_by(section_id=student.section_id).all()
        if fa_list:
            for fa in fa_list:
                subj = fa.subject
                if not subj:
                    continue
                s_tot = max(1, total_lectures // len(fa_list))
                s_pres = max(0, min(s_tot, total_present // len(fa_list)))
                s_abs = s_tot - s_pres
                pct = round((s_pres / s_tot * 100), 1) if s_tot > 0 else 100.0
                subjects_data.append({
                    "name": subj.name,
                    "code": subj.code,
                    "percent": pct,
                    "total": s_tot,
                    "present": s_pres,
                    "absent": s_abs,
                    "activity_type": "Theory",
                    "activity_pct": int(pct),
                    "status": "P" if pct >= 75 else "A"
                })
    if not subjects_data:
        subjects_data = [
            {"name": "Communication Skills-I", "code": "26BULCHM1202", "percent": 66.67, "total": 6, "present": 4, "absent": 2, "activity_type": "Practical", "activity_pct": 67, "status": "P"},
            {"name": "Exploratory Project", "code": "26BUVCVD1202", "percent": 100.0, "total": 2, "present": 2, "absent": 0, "activity_type": "Practical", "activity_pct": 100, "status": "P"},
            {"name": "Programming in C", "code": "26BTXCCE1103", "percent": 100.0, "total": 8, "present": 8, "absent": 0, "activity_type": "Theory", "activity_pct": 100, "status": "P"},
            {"name": "Basics of Civil Engineering", "code": "26BTXCCV1104", "percent": 100.0, "total": 10, "present": 10, "absent": 0, "activity_type": "Theory", "activity_pct": 100, "status": "P"},
            {"name": "Engineering Physics", "code": "26BTXCSA1101", "percent": 100.0, "total": 12, "present": 12, "absent": 0, "activity_type": "Theory", "activity_pct": 100, "status": "P"},
            {"name": "Engineering Mathematics", "code": "26BTXCSA1106", "percent": 100.0, "total": 14, "present": 14, "absent": 0, "activity_type": "Theory", "activity_pct": 100, "status": "P"}
        ]

    academics = {
        "course_label": course_label,
        "total_lectures": total_lectures,
        "total_present": total_present,
        "total_absent": total_absent,
        "overall_pct": overall_pct,
        "subjects_data": subjects_data
    }

    # 3. Weekly Timetable Matrix with Attendance Overlay
    days = [
        {"index": 0, "date_num": 31, "day_name": "Mon", "is_active": True},
        {"index": 1, "date_num": 1, "day_name": "Tue", "is_active": False},
        {"index": 2, "date_num": 2, "day_name": "Wed", "is_active": False},
        {"index": 3, "date_num": 3, "day_name": "Thu", "is_active": False},
        {"index": 4, "date_num": 4, "day_name": "Fri", "is_active": False},
        {"index": 5, "date_num": 5, "day_name": "Sat", "is_active": False},
        {"index": 6, "date_num": 6, "day_name": "Sun", "is_active": False}
    ]

    periods = [
        {"index": 1, "name": "Period 1", "time": "09:00-09:55"},
        {"index": 2, "name": "Period 2", "time": "10:00-10:55"},
        {"index": 3, "name": "Period 3", "time": "11:10-12:05"},
        {"index": 4, "name": "Period 4", "time": "12:10-13:05"},
        {"index": 5, "name": "Period 5", "time": "14:00-14:55"},
        {"index": 6, "name": "Period 6", "time": "15:00-15:55"}
    ]

    grid = {}
    if student.section_id:
        from app.models import TimetableSlot
        slots = TimetableSlot.query.filter_by(section_id=student.section_id).all()
        day_indices = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
        for slot in slots:
            d_i = day_indices.get(slot.day_of_week)
            if d_i is not None and slot.subject:
                # Map hour to period
                h = slot.start_time.hour
                p_i = 1
                if h == 9: p_i = 1
                elif h == 10: p_i = 2
                elif h == 11: p_i = 3
                elif h == 12: p_i = 4
                elif h == 14: p_i = 5
                elif h >= 15: p_i = 6
                grid[(p_i, d_i)] = {
                    "subject_code": slot.subject.code or slot.subject.name[:10],
                    "activity_type": "Theory",
                    "faculty_name": slot.faculty.name if slot.faculty else "Faculty",
                    "time_str": f"{slot.start_time.strftime('%H:%M')}-{slot.end_time.strftime('%H:%M')}",
                    "attendance_status": "P"
                }

    # Fallback to demo timetable if grid is empty
    if not grid:
        grid = {
            (1, 0): {"subject_code": "26BULCHM1202", "activity_type": "Practical", "faculty_name": "PU FACE TRAINER VII", "time_str": "09:00-09:55", "attendance_status": "P"},
            (1, 1): {"subject_code": "26BTXCME1206", "activity_type": "Practical", "faculty_name": "DEVESH KUMAR", "time_str": "09:00-09:55", "attendance_status": "P"},
            (1, 2): {"subject_code": "26BTXCCV1104", "activity_type": "Theory", "faculty_name": "VEDATRAYEE ACHARYA", "time_str": "09:00-09:55", "attendance_status": "P"},
            (1, 3): {"subject_code": "26BULCHM1201", "activity_type": "Practical", "faculty_name": "PU FACE TRAINER VIII", "time_str": "09:00-09:55", "attendance_status": "P"},
            (1, 4): {"subject_code": "26BTXCME1206", "activity_type": "Practical", "faculty_name": "DEVESH KUMAR", "time_str": "09:00-09:55", "attendance_status": "P"},
            (2, 0): {"subject_code": "26BULCHM1202", "activity_type": "Practical", "faculty_name": "PU FACE TRAINER VII", "time_str": "10:00-10:55", "attendance_status": "P"},
            (2, 1): {"subject_code": "26BTXCCE1103", "activity_type": "Theory", "faculty_name": "DESHRAJ BAIRWA", "time_str": "10:00-10:55", "attendance_status": "P"},
            (2, 2): {"subject_code": "26BTXCSA1101", "activity_type": "Theory", "faculty_name": "SHIVA SONI", "time_str": "10:00-10:55", "attendance_status": "P"},
            (3, 0): {"subject_code": "26BTXCSA1106", "activity_type": "Theory", "faculty_name": "RAKESH AGGARWAL", "time_str": "11:10-12:05", "attendance_status": "P"},
            (3, 1): {"subject_code": "26BTXCSA1106", "activity_type": "Theory", "faculty_name": "RAKESH AGGARWAL", "time_str": "11:10-12:05", "attendance_status": "P"},
            (5, 0): {"subject_code": "26BTXCCE1103", "activity_type": "Theory", "faculty_name": "DESHRAJ BAIRWA", "time_str": "14:00-14:55", "attendance_status": "P"},
            (6, 0): {"subject_code": "26BTXCSA1108", "activity_type": "Theory", "faculty_name": "SONAL JAIN", "time_str": "15:00-15:55", "attendance_status": "P"},
        }

    timetable_data = {
        "week_range_str": "Current Week",
        "days": days,
        "periods": periods,
        "grid": grid
    }

    # 4. Fee Overview & Transaction History
    payments = FeePayment.query.filter_by(student_id=student.id).order_by(FeePayment.created_at.desc()).all()
    if payments:
        transactions = []
        for p in payments:
            paid_amt = p.amount if p.status == 'paid' else 0
            receipt = p.transaction_ref or f"PU/{p.created_at.strftime('%d-%m-%y')}/{p.payment_method or 'Online'}/{p.id:06d}"
            transactions.append({
                "id": p.id,
                "receipt_no": receipt,
                "due_amount": int(p.amount),
                "arrear": 0,
                "late_fee": 0,
                "paid_amount": int(paid_amt),
                "currency": "INR",
                "date": (p.paid_at or p.created_at).strftime('%dth %b, %y'),
                "instrument_no": (p.payment_method or 'Online').capitalize(),
                "type": "Payment" if p.status == 'paid' else p.status.capitalize()
            })
        total_sched = sum(p.amount for p in payments)
        total_p = sum(p.amount for p in payments if p.status == 'paid')
        total_d = sum(p.amount for p in payments if p.status in ('pending', 'overdue'))
        sem_name = student.section.semester_.name if (student.section and student.section.semester_) else "Semester 1"
        fee_data = {
            "scheduled_amount": float(total_sched),
            "paid_amount": float(total_p),
            "scholarship_amount": 0.0,
            "due_amount": float(total_d),
            "semesters": [
                {"name": sem_name.upper(), "scheduled": int(total_sched), "paid": int(total_p), "scholarship": 0, "due": int(total_d), "active": True},
            ],
            "transactions": transactions
        }
    else:
        transactions = [
            {"id": 1, "receipt_no": "PU/26-08-26/Online/159426", "due_amount": 35625, "arrear": 0, "late_fee": 0, "paid_amount": 35625, "currency": "INR", "date": "26th Aug, 26", "instrument_no": "Online", "type": "Payment"},
        ]
        fee_data = {
            "scheduled_amount": 226500.0,
            "paid_amount": 97125.0,
            "scholarship_amount": 15000.0,
            "due_amount": 114375.0,
            "semesters": [
                {"name": "SEMESTER 1", "scheduled": 226500, "paid": 97125, "scholarship": 15000, "due": 114375, "active": True},
            ],
            "transactions": transactions
        }

    # 5. Leaves
    leaves = LeaveApplication.query.filter_by(student_id=student.id).order_by(LeaveApplication.created_at.desc()).limit(10).all()

    return {
        "student": student,
        "academics": academics,
        "timetable_data": timetable_data,
        "fee_data": fee_data,
        "leaves": leaves
    }


# ─── Dashboard & Digital Campus Portal ──────────────────────────────────────────

@bp.route('/dashboard')
@bp.route('/portal')
@student_required
def dashboard():
    student = get_current_student()
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('auth.login'))

    # Support ?view=classic if desired
    if request.args.get('view') == 'classic':
        active_term = AcademicTerm.query.filter_by(college_id=current_user.college_id, is_active=True).first()
        recent_grades = (Grade.query.filter_by(student_id=student.id)
                         .order_by(Grade.date.desc()).limit(6).all())
        thirty_ago = date.today() - timedelta(days=30)
        total_att = Attendance.query.filter_by(student_id=student.id).filter(Attendance.date >= thirty_ago).count()
        present_att = Attendance.query.filter_by(student_id=student.id, status='present').filter(Attendance.date >= thirty_ago).count()
        att_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 100
        if student.section_id:
            assignments = (Assignment.query.filter_by(section_id=student.section_id, is_active=True)
                           .filter(Assignment.due_date >= datetime.utcnow()).all())
            submitted_ids = {s.assignment_id for s in AssignmentSubmission.query.filter_by(student_id=student.id).all()}
            pending_assignments = [a for a in assignments if a.id not in submitted_ids]
        else:
            pending_assignments = []
        upcoming_exams = (Exam.query.filter_by(section_id=student.section_id, is_published=True)
                          .filter(Exam.end_time >= datetime.utcnow()).order_by(Exam.start_time).limit(3).all()
                          if student.section_id else [])
        notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
        from app.models import BookIssue
        overdue_books = BookIssue.query.filter_by(user_id=current_user.id, status='Issued').filter(BookIssue.due_date < date.today()).all()

        return render_template('student/dashboard.html', student=student,
                               recent_grades=recent_grades, att_pct=att_pct,
                               pending_assignments=pending_assignments,
                               upcoming_exams=upcoming_exams,
                               notifications=notifications,
                               active_term=active_term,
                               overdue_books=overdue_books)

    # Render Unified University ERP Portal
    ctx = get_student_portal_context(student)
    return render_template('student/unified_portal.html', **ctx)



# ─── Faculty Directory ─────────────────────────────────────────────────────────

@bp.route('/faculty')
@student_required
def faculty():
    student = get_current_student()
    if not student or not student.section_id:
        flash('No section assigned.', 'warning')
        return redirect(url_for('student.dashboard'))

    # Get faculty assigned to the student's section
    faculty_assignments = (FacultyAssignment.query
                          .filter_by(section_id=student.section_id)
                          .all())
    return render_template('student/faculty.html', student=student,
                           faculty_assignments=faculty_assignments)


# ─── Profile View ──────────────────────────────────────────────────────────────

@bp.route('/profile-view')
@login_required
def profile_view():
    student_id = request.args.get('student_id', type=int)
    if student_id and current_user.role in ['admin', 'faculty', 'superadmin']:
        student = Student.query.get_or_404(student_id)
    else:
        student = get_current_student()
        
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('student.dashboard') if current_user.role == 'student' else url_for('admin.users'))
    
    from app.models import TransportAllocation, HostelAllocation
    transport = TransportAllocation.query.filter_by(student_id=student.id).first()
    hostel = HostelAllocation.query.filter_by(student_id=student.id, status='Occupied').first()
    
    return render_template('student/profile_view.html', student=student, transport=transport, hostel=hostel)


# ─── Subject List ──────────────────────────────────────────────────────────────

@bp.route('/subjects')
@student_required
def subjects():
    student = get_current_student()
    if not student or not student.section_id:
        flash('No section assigned.', 'warning')
        return redirect(url_for('student.dashboard'))

    faculty_assignments = (FacultyAssignment.query
                          .filter_by(section_id=student.section_id)
                          .all())
    # Get unique subjects with their faculty
    subjects_data = []
    for ta in faculty_assignments:
        subjects_data.append({
            'subject': ta.subject,
            'faculty': ta.faculty,
            'grades': Grade.query.filter_by(student_id=student.id, subject_id=ta.subject_id).order_by(Grade.date.desc()).limit(3).all()
        })
    return render_template('student/subjects.html', student=student,
                           subjects_data=subjects_data)


# ─── Announcements ─────────────────────────────────────────────────────────────

@bp.route('/announcements')
@bp.route('/announcements/<atype>')
@student_required
def announcements(atype=None):
    student = get_current_student()
    query = Announcement.query.filter_by(college_id=current_user.college_id, is_active=True)
    if atype and atype in ('event', 'holiday', 'notice'):
        query = query.filter_by(announcement_type=atype)
    announcements_list = query.order_by(Announcement.created_at.desc()).all()
    return render_template('student/announcements.html', student=student,
                           announcements=announcements_list, current_type=atype)


# ─── Event Access ──────────────────────────────────────────────────────────────

@bp.route('/events')
@student_required
def events():
    student = get_current_student()
    events_list = (Event.query.filter_by(college_id=current_user.college_id, is_active=True)
                  .order_by(Event.event_date.desc()).all())
    # Get student's registrations
    registered_ids = {r.event_id for r in EventRegistration.query.filter_by(student_id=student.id).all()}
    return render_template('student/events.html', student=student,
                           events=events_list, registered_ids=registered_ids)


@bp.route('/events/<int:eid>/register', methods=['POST'])
@student_required
def register_event(eid):
    student = get_current_student()
    event = Event.query.get_or_404(eid)

    existing = EventRegistration.query.filter_by(event_id=eid, student_id=student.id).first()
    if existing:
        flash('Already registered for this event.', 'info')
        return redirect(url_for('student.events'))

    if event.is_full:
        flash('Event is at full capacity.', 'warning')
        return redirect(url_for('student.events'))

    # Generate unique QR code data
    qr_data = hashlib.sha256(f"{student.id}-{eid}-{datetime.utcnow().timestamp()}".encode()).hexdigest()[:20]

    reg = EventRegistration(
        event_id=eid,
        student_id=student.id,
        qr_code=qr_data
    )
    db.session.add(reg)
    db.session.commit()
    flash(f'Successfully registered for {event.title}!', 'success')
    return redirect(url_for('student.events'))


# ─── My Event QR ───────────────────────────────────────────────────────────────

@bp.route('/event-qr')
@student_required
def event_qr_list():
    student = get_current_student()
    registrations = (EventRegistration.query.filter_by(student_id=student.id)
                    .order_by(EventRegistration.registered_at.desc()).all())
    return render_template('student/event_qr.html', student=student,
                           registrations=registrations)


# ─── Feedback ──────────────────────────────────────────────────────────────────

@bp.route('/feedback', methods=['GET', 'POST'])
@student_required
def feedback():
    student = get_current_student()
    if request.method == 'POST':
        fb = Feedback(
            student_id=student.id,
            college_id=current_user.college_id,
            category=request.form.get('category', 'general'),
            subject=request.form.get('subject', ''),
            body=request.form.get('body', ''),
        )
        db.session.add(fb)
        db.session.commit()
        flash('Feedback submitted successfully!', 'success')
        return redirect(url_for('student.feedback'))

    feedbacks = (Feedback.query.filter_by(student_id=student.id)
                .order_by(Feedback.created_at.desc()).all())
    return render_template('student/feedback.html', student=student,
                           feedbacks=feedbacks)


# ─── Grievances ────────────────────────────────────────────────────────────────

@bp.route('/grievances', methods=['GET', 'POST'])
@student_required
def grievances():
    student = get_current_student()
    if request.method == 'POST':
        gr = Grievance(
            student_id=student.id,
            college_id=current_user.college_id,
            category=request.form.get('category', 'general'),
            subject=request.form.get('subject', ''),
            description=request.form.get('description', ''),
            priority=request.form.get('priority', 'medium'),
        )
        db.session.add(gr)
        db.session.commit()
        flash('Grievance submitted successfully!', 'success')
        return redirect(url_for('student.grievances'))

    grievances_list = (Grievance.query.filter_by(student_id=student.id)
                      .order_by(Grievance.created_at.desc()).all())
    return render_template('student/grievances.html', student=student,
                           grievances=grievances_list)


# ─── Anti-Ragging Undertaking ──────────────────────────────────────────────────

@bp.route('/anti-ragging', methods=['GET', 'POST'])
@student_required
def anti_ragging():
    student = get_current_student()
    existing = (AntiRaggingUndertaking.query.filter_by(student_id=student.id)
               .order_by(AntiRaggingUndertaking.submitted_at.desc()).first())

    if request.method == 'POST':
        ref_number = request.form.get('reference_number', '').strip()
        if not ref_number:
            flash('Reference number is required.', 'danger')
            return redirect(url_for('student.anti_ragging'))

        undertaking = AntiRaggingUndertaking(
            student_id=student.id,
            college_id=current_user.college_id,
            reference_number=ref_number,
            academic_year=request.form.get('academic_year', ''),
            parent_name=request.form.get('parent_name', ''),
            parent_contact=request.form.get('parent_contact', ''),
            declaration_accepted=request.form.get('declaration') == 'on',
        )
        db.session.add(undertaking)
        db.session.commit()
        flash('Anti-Ragging undertaking submitted successfully!', 'success')
        return redirect(url_for('student.anti_ragging'))

    return render_template('student/anti_ragging.html', student=student,
                           existing=existing)


# ─── Summer Term ───────────────────────────────────────────────────────────────

@bp.route('/summer-term')
@student_required
def summer_term():
    student = get_current_student()
    # Show summer/special terms
    terms = (AcademicTerm.query.filter_by(college_id=current_user.college_id)
            .order_by(AcademicTerm.start_date.desc()).all())
    summer_terms = [t for t in terms if 'summer' in t.name.lower() or t.term_type == 'summer']
    return render_template('student/summer_term.html', student=student,
                           summer_terms=summer_terms, all_terms=terms)


# ─── Fee Management ────────────────────────────────────────────────────────────

@bp.route('/fee-statement')
@student_required
def fee_statement():
    student = get_current_student()
    payments = (FeePayment.query.filter_by(student_id=student.id)
               .order_by(FeePayment.created_at.desc()).all())
    fee_types = FeeType.query.filter_by(college_id=current_user.college_id, is_active=True).all()

    # Calculate totals
    total_due = sum(p.amount for p in payments if p.status == 'pending')
    total_paid = sum(p.amount for p in payments if p.status == 'paid')
    total_overdue = sum(p.amount for p in payments if p.status == 'overdue')

    return render_template('student/fee_statement.html', student=student,
                           payments=payments, fee_types=fee_types,
                           total_due=total_due, total_paid=total_paid,
                           total_overdue=total_overdue)


@bp.route('/caution-money')
@student_required
def caution_money():
    student = get_current_student()
    records = (CautionMoney.query.filter_by(student_id=student.id)
              .order_by(CautionMoney.created_at.desc()).all())
    return render_template('student/caution_money.html', student=student,
                           records=records)


@bp.route('/transaction-history')
@student_required
def transaction_history():
    student = get_current_student()
    payments = (FeePayment.query.filter_by(student_id=student.id)
               .filter(FeePayment.status == 'paid')
               .order_by(FeePayment.paid_at.desc()).all())
    caution_records = (CautionMoney.query.filter_by(student_id=student.id)
                      .filter(CautionMoney.status.in_(['paid', 'refunded']))
                      .all())
    return render_template('student/transaction_history.html', student=student,
                           payments=payments, caution_records=caution_records)


# ─── OD / Leave Application ───────────────────────────────────────────────────

@bp.route('/leave-application', methods=['GET', 'POST'])
@student_required
def leave_application():
    student = get_current_student()
    if request.method == 'POST':
        from_date_str = request.form.get('from_date')
        to_date_str = request.form.get('to_date')
        try:
            from_dt = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            to_dt = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Invalid dates.', 'danger')
            return redirect(url_for('student.leave_application'))

        leave = LeaveApplication(
            student_id=student.id,
            college_id=current_user.college_id,
            leave_type=request.form.get('leave_type', 'od'),
            from_date=from_dt,
            to_date=to_dt,
            reason=request.form.get('reason', ''),
        )
        db.session.add(leave)
        db.session.commit()
        flash('Leave application submitted!', 'success')
        return redirect(url_for('student.leave_application'))

    applications = (LeaveApplication.query.filter_by(student_id=student.id)
                   .order_by(LeaveApplication.created_at.desc()).all())
    return render_template('student/leave_application.html', student=student,
                           applications=applications)


# ─── Attendance (Enhanced) ─────────────────────────────────────────────────────

@bp.route('/attendance')
@student_required
def attendance():
    student = get_current_student()
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    records = (Attendance.query.filter_by(student_id=student.id)
               .filter(db.extract('month', Attendance.date) == month,
                       db.extract('year', Attendance.date) == year)
               .order_by(Attendance.date).all())

    total = Attendance.query.filter_by(student_id=student.id).count()
    present = Attendance.query.filter_by(student_id=student.id, status='present').count()
    absent = Attendance.query.filter_by(student_id=student.id, status='absent').count()
    late = Attendance.query.filter_by(student_id=student.id, status='late').count()
    att_pct = round((present / total * 100), 1) if total > 0 else 0

    return render_template('student/attendance.html', student=student, records=records,
                           month=month, year=year, total=total, present=present,
                           absent=absent, late=late, att_pct=att_pct)


@bp.route('/attendance-report')
@student_required
def attendance_report():
    student = get_current_student()

    # Monthly breakdown
    all_records = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date).all()

    # Group by month
    monthly_data = {}
    for rec in all_records:
        key = rec.date.strftime('%Y-%m')
        if key not in monthly_data:
            monthly_data[key] = {'total': 0, 'present': 0, 'absent': 0, 'late': 0, 'label': rec.date.strftime('%b %Y')}
        monthly_data[key]['total'] += 1
        if rec.status == 'present':
            monthly_data[key]['present'] += 1
        elif rec.status == 'absent':
            monthly_data[key]['absent'] += 1
        elif rec.status == 'late':
            monthly_data[key]['late'] += 1

    total = len(all_records)
    present = sum(1 for r in all_records if r.status == 'present')
    absent = sum(1 for r in all_records if r.status == 'absent')
    late = sum(1 for r in all_records if r.status == 'late')
    att_pct = round((present / total * 100), 1) if total > 0 else 0

    return render_template('student/attendance_report.html', student=student,
                           monthly_data=monthly_data, total=total,
                           present=present, absent=absent, late=late,
                           att_pct=att_pct)


# ─── Examinations (Enhanced) ──────────────────────────────────────────────────

@bp.route('/marksheets')
@student_required
def marksheets():
    student = get_current_student()
    terms = (AcademicTerm.query.filter_by(college_id=current_user.college_id)
            .order_by(AcademicTerm.start_date.desc()).all())
    selected_term = request.args.get('term_id', type=int)

    grades_query = Grade.query.filter_by(student_id=student.id)
    if selected_term:
        grades_query = grades_query.filter_by(term_id=selected_term)
    grades = grades_query.order_by(Grade.date.desc()).all()

    # Group by subject
    by_subject = {}
    for g in grades:
        subj = g.subject.name
        if subj not in by_subject:
            by_subject[subj] = []
        by_subject[subj].append(g)

    # Overall stats
    if grades:
        avg_pct = round(sum(g.percentage for g in grades) / len(grades), 1)
    else:
        avg_pct = 0

    return render_template('student/marksheets.html', student=student,
                           terms=terms, grades=grades, by_subject=by_subject,
                           avg_pct=avg_pct, selected_term=selected_term)


@bp.route('/mid-term-marks')
@student_required
def mid_term_marks():
    student = get_current_student()
    # Filter grades that are mid-term type
    grades = (Grade.query.filter_by(student_id=student.id)
             .filter(Grade.exam_name.ilike('%mid%'))
             .order_by(Grade.date.desc()).all())
    return render_template('student/mid_term_marks.html', student=student,
                           grades=grades)


@bp.route('/moocs-certificates')
@student_required
def moocs_certificates():
    student = get_current_student()
    # Use MicroCredential model for MOOCs certificates
    certs = (MicroCredential.query.filter_by(student_id=student.id)
            .order_by(MicroCredential.issued_date.desc()).all())
    return render_template('student/moocs_certificates.html', student=student,
                           certificates=certs)


@bp.route('/exam-scheme')
@student_required
def exam_scheme():
    student = get_current_student()
    # Show upcoming exams as the exam scheme
    exams = []
    if student.section_id:
        exams = (Exam.query.filter_by(section_id=student.section_id, is_published=True)
                .order_by(Exam.start_time).all())
    return render_template('student/exam_scheme.html', student=student,
                           exams=exams)


@bp.route('/academic-calendar')
@student_required
def academic_calendar():
    student = get_current_student()
    terms = (AcademicTerm.query.filter_by(college_id=current_user.college_id)
            .order_by(AcademicTerm.start_date).all())
    return render_template('student/academic_calendar.html', student=student,
                           terms=terms)


# ─── Documents ─────────────────────────────────────────────────────────────────

@bp.route('/documents')
@student_required
def documents():
    student = get_current_student()
    docs = (StudentDocument.query.filter_by(student_id=student.id)
           .order_by(StudentDocument.uploaded_at.desc()).all())
    return render_template('student/documents.html', student=student,
                           documents=docs)


@bp.route('/document-checklist')
@student_required
def document_checklist():
    student = get_current_student()
    # Standard document types required
    required_docs = [
        {'type': 'photo', 'label': 'Passport Photo', 'icon': 'fa-camera'},
        {'type': 'aadhar', 'label': 'Aadhar Card', 'icon': 'fa-id-card'},
        {'type': 'marksheet_10', 'label': '10th Marksheet', 'icon': 'fa-file-lines'},
        {'type': 'marksheet_12', 'label': '12th Marksheet', 'icon': 'fa-file-lines'},
        {'type': 'tc', 'label': 'Transfer Certificate', 'icon': 'fa-certificate'},
        {'type': 'migration', 'label': 'Migration Certificate', 'icon': 'fa-right-left'},
        {'type': 'domicile', 'label': 'Domicile Certificate', 'icon': 'fa-house'},
        {'type': 'income', 'label': 'Income Certificate', 'icon': 'fa-indian-rupee-sign'},
        {'type': 'caste', 'label': 'Caste Certificate (if applicable)', 'icon': 'fa-scroll'},
        {'type': 'medical', 'label': 'Medical Certificate', 'icon': 'fa-stethoscope'},
    ]
    # Check which ones are uploaded
    uploaded = {d.doc_type: d for d in StudentDocument.query.filter_by(student_id=student.id).all()}
    return render_template('student/document_checklist.html', student=student,
                           required_docs=required_docs, uploaded=uploaded)


# ─── Existing Routes ──────────────────────────────────────────────────────────

@bp.route('/grades')
@student_required
def grades():
    student = get_current_student()
    term_id = request.args.get('term_id', type=int)
    terms = AcademicTerm.query.filter_by(college_id=current_user.college_id).order_by(AcademicTerm.start_date.desc()).all()
    active_term = AcademicTerm.query.filter_by(college_id=current_user.college_id, is_active=True).first()

    query = Grade.query.filter_by(student_id=student.id)
    if term_id:
        query = query.filter_by(term_id=term_id)
    grades_list = query.order_by(Grade.date.desc()).all()

    # Group by subject
    by_subject = {}
    for g in grades_list:
        subj = g.subject.name
        if subj not in by_subject:
            by_subject[subj] = []
        by_subject[subj].append(g)

    # Chart data
    chart_labels = []
    chart_data = {}
    for g in sorted(grades_list, key=lambda x: x.date):
        label = f"{g.exam_name} ({g.date.strftime('%b %d')})"
        if label not in chart_labels:
            chart_labels.append(label)
        subj = g.subject.name
        if subj not in chart_data:
            chart_data[subj] = []
        chart_data[subj].append(g.percentage)

    return render_template('student/grades.html', student=student, grades=grades_list,
                           by_subject=by_subject, terms=terms, active_term=active_term,
                           selected_term_id=term_id,
                           chart_labels=chart_labels, chart_data=chart_data)


@bp.route('/assignments')
@student_required
def assignments():
    student = get_current_student()
    all_assignments = (Assignment.query.filter_by(section_id=student.section_id, is_active=True)
                       .order_by(Assignment.due_date).all() if student.section_id else [])
    submissions = {s.assignment_id: s for s in
                   AssignmentSubmission.query.filter_by(student_id=student.id).all()}
    return render_template('student/assignments.html', assignments=all_assignments,
                           submissions=submissions, student=student)


@bp.route('/assignments/<int:aid>/submit', methods=['GET', 'POST'])
@student_required
def submit_assignment(aid):
    student = get_current_student()
    assignment = Assignment.query.get_or_404(aid)
    existing_sub = AssignmentSubmission.query.filter_by(assignment_id=aid, student_id=student.id).first()

    if request.method == 'POST':
        if existing_sub:
            flash('Already submitted.', 'info')
        else:
            sub = AssignmentSubmission(
                assignment_id=aid,
                student_id=student.id,
                content=request.form.get('content', ''),
                is_late=datetime.utcnow() > assignment.due_date,
                submitted_at=datetime.utcnow()
            )
            db.session.add(sub)
            db.session.commit()
            flash('Assignment submitted!', 'success')
        return redirect(url_for('student.assignments'))
    return render_template('student/submit_assignment.html', assignment=assignment, existing_sub=existing_sub)


@bp.route('/notifications/mark-read', methods=['POST'])
@student_required
def mark_notifications_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'success': True})


# ─── Micro-Credentials ────────────────────────────────────────────────────────

@bp.route('/credentials')
@student_required
def credentials():
    student = get_current_student()
    creds = MicroCredential.query.filter_by(student_id=student.id).order_by(MicroCredential.issued_date.desc()).all()
    return render_template('student/credentials.html', student=student, credentials=creds)


@bp.route('/credentials/<int:cid>/download')
@login_required
def download_credential(cid):
    c = MicroCredential.query.get_or_404(cid)

    # Check access permission (only the student or their parent can view)
    if current_user.role == 'student':
        if c.student.user_id != current_user.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('student.dashboard'))
    elif current_user.role == 'parent':
        from app.models import ParentStudentLink
        link = ParentStudentLink.query.filter_by(parent_id=current_user.id, student_id=c.student_id).first()
        if not link:
            flash('Access denied.', 'danger')
            return redirect(url_for('parent.dashboard'))

    html = render_template('credentials/certificate_pdf.html', credential=c, today=date.today())

    try:
        from weasyprint import HTML  # type: ignore
        pdf = HTML(string=html).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=credential_{c.id}_{c.category}.pdf'
        return response
    except Exception as e:
        flash(f'PDF generation failed: {e}. Showing HTML version instead.', 'warning')
        return html


@bp.route('/timetable')
@student_required
def timetable():
    """Show the student's section timetable from TimetableSlot model."""
    from app.models import TimetableSlot
    student = get_current_student()
    if not student:
        flash('Student profile not found.', 'warning')
        return redirect(url_for('student.dashboard'))

    section = student.section
    slots = []
    if section:
        slots = (TimetableSlot.query
                 .filter_by(section_id=section.id)
                 .order_by(TimetableSlot.day_of_week, TimetableSlot.start_time)
                 .all())

    # Organise by day
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    timetable_by_day = {day: [] for day in days_order}
    for slot in slots:
        if slot.day_of_week in timetable_by_day:
            timetable_by_day[slot.day_of_week].append(slot)

    return render_template('student/timetable.html',
                           student=student,
                           section=section,
                           timetable_by_day=timetable_by_day,
                           days_order=days_order,
                           total_slots=len(slots))


@bp.route('/library')
@student_required
def library():
    """Show library books and the student's currently issued books."""
    from app.models import LibraryBook, BookIssue
    student = get_current_student()
    if not student:
        flash('Student profile not found.', 'warning')
        return redirect(url_for('student.dashboard'))

    college_id = current_user.college_id
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()

    query = LibraryBook.query.filter_by(college_id=college_id)
    if search:
        query = query.filter(
            db.or_(
                LibraryBook.title.ilike(f'%{search}%'),
                LibraryBook.author.ilike(f'%{search}%'),
                LibraryBook.isbn.ilike(f'%{search}%')
            )
        )
    if category:
        query = query.filter_by(category=category)

    books = query.order_by(LibraryBook.title).all()
    categories = db.session.query(LibraryBook.category).filter_by(college_id=college_id).distinct().all()
    categories = sorted([c[0] for c in categories if c[0]])

    # Books currently issued to this student
    my_issues = (BookIssue.query
                 .filter_by(user_id=current_user.id, college_id=college_id)
                 .filter(BookIssue.status.in_(['issued', 'overdue']))
                 .join(LibraryBook)
                 .order_by(BookIssue.due_date)
                 .all())

    overdue_count = sum(1 for i in my_issues if i.status == 'overdue')

    return render_template('student/library.html',
                           books=books,
                           my_issues=my_issues,
                           categories=categories,
                           search=search,
                           selected_category=category,
                           overdue_count=overdue_count,
                           today=date.today())
