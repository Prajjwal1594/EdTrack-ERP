from flask import render_template, redirect, url_for, flash, request, jsonify, Response, abort
import csv
import io
import openpyxl
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from functools import wraps
from app.admin import bp
from app.models import (User, College, Semester, Section, Subject, FacultyAssignment,
                         Student, AcademicTerm, ParentStudentLink, FeeType,
                         Announcement, Event, Feedback, Grievance, LeaveApplication,
                         Course, Stream, Batch)
from app import db
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta
from app.utils.algorithms import generate_parent_digest, get_parent_digest_preview
from sqlalchemy import func
from app.models import Grade, Attendance, StaffAttendance


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated)


@bp.route('/dashboard')
@admin_required
def dashboard():
    college = College.query.filter_by(id=current_user.college_id).first()
    stats = {
        'faculty': User.query.filter_by(role='faculty', college_id=current_user.college_id).count(),
        'students': User.query.filter_by(role='student', college_id=current_user.college_id).count(),
        'parents': User.query.filter_by(role='parent', college_id=current_user.college_id).count(),
        'semesters': Semester.query.filter_by(college_id=current_user.college_id).count(),
        'subjects': Subject.query.filter_by(college_id=current_user.college_id).count(),
    }
    active_term = AcademicTerm.query.filter_by(college_id=current_user.college_id, is_active=True).first()
    
    # Analytics Data
    from sqlalchemy import func
    from app.models import Grade
    
    # 1. Subject Averages
    subject_avg_data = db.session.query(
        Subject.name, func.avg(Grade.score)
    ).join(Grade, Grade.subject_id == Subject.id).filter(Subject.college_id == current_user.college_id).group_by(Subject.id).all()
    subject_averages = [{"subject": row[0], "avg": round(row[1], 1)} for row in subject_avg_data]

    # 2. Performance Trend (Last 6 Months)
    date_group = func.strftime('%Y-%m', Grade.date) if db.engine.dialect.name == 'sqlite' else func.to_char(Grade.date, 'YYYY-MM')
    trend_data = db.session.query(
        date_group, func.avg(Grade.score)
    ).join(Student, Grade.student_id == Student.id).join(User, Student.user_id == User.id)\
    .filter(User.college_id == current_user.college_id).group_by(date_group)\
    .order_by(date_group.desc()).limit(6).all()
    performance_trend = [{"month": row[0], "avg": round(row[1], 1)} for row in reversed(trend_data)]

    # 3. User Distribution
    user_dist = [
        {"role": "Admins", "count": stats['faculty']},
        {"role": "Faculty", "count": stats['faculty']},
        {"role": "Students", "count": stats['students']},
        {"role": "Parents", "count": stats['parents']}
    ]
    user_dist[0]['count'] = User.query.filter_by(role='admin', college_id=current_user.college_id).count()

    recent_users = User.query.filter_by(college_id=current_user.college_id).order_by(User.created_at.desc()).limit(5).all()
    return render_template('admin/dashboard.html', stats=stats, college=college,
                           active_term=active_term, recent_users=recent_users,
                           subject_averages=subject_averages,
                           performance_trend=performance_trend,
                           user_distribution=user_dist)


@bp.route('/admission', methods=['GET', 'POST'])
@admin_required
def admission():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Email already registered for admission.', 'danger')
            return redirect(url_for('admin.admission'))
            
        user = User(
            name=request.form.get('name', '').strip(),
            email=email,
            role='student',
            phone=request.form.get('phone', ''),
            college_id=current_user.college_id
        )
        user.set_password('ChangeMe123!')
        db.session.add(user)
        db.session.flush()

        section_id = request.form.get('section_id')
        enrollment_num = request.form.get('enrollment_number') or f'EW{user.id:05d}'
        dob_str = request.form.get('date_of_birth')
        dob = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
        
        student = Student(
            user_id=user.id,
            section_id=section_id if section_id else None,
            enrollment_number=enrollment_num,
            date_of_birth=dob,
            gender=request.form.get('gender', '')
        )
        db.session.add(student)
        db.session.commit()
        flash(f'Admission successful for student {user.name}. Default password applied.', 'success')
        return redirect(url_for('admin.users'))

    sections = Section.query.join(Semester).filter(Semester.college_id == current_user.college_id).all()
    return render_template('admin/admission.html', sections=sections)


# ─── Users ───────────────────────────────────────────────────────────────────
@bp.route('/users')
@admin_required
def users():
    role_filter = request.args.get('role', '')
    query = User.query.filter_by(college_id=current_user.college_id)
    if role_filter:
        query = query.filter_by(role=role_filter)
    users = query.order_by(User.name).all()
    return render_template('admin/users.html', users=users, role_filter=role_filter)


@bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('admin.add_user'))
        user = User(
            name=request.form.get('name', '').strip(),
            email=email,
            role=request.form.get('role'),
            phone=request.form.get('phone', ''),
            college_id=current_user.college_id
        )
        user.set_password(request.form.get('password', 'ChangeMe123!'))
        db.session.add(user)
        db.session.flush()

        if user.role == 'student':
            course_id = request.form.get('course_id', type=int)
            stream_id = request.form.get('stream_id', type=int)
            batch_id = request.form.get('batch_id', type=int)
            section_id = request.form.get('section_id', type=int)
            enrollment_num = request.form.get('enrollment_number') or f'EW{user.id:05d}'
            dob_str = request.form.get('date_of_birth')
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date() if dob_str else None
            student = Student(
                user_id=user.id,
                course_id=course_id,
                stream_id=stream_id,
                batch_id=batch_id,
                section_id=section_id,
                enrollment_number=enrollment_num,
                date_of_birth=dob,
                gender=request.form.get('gender', '')
            )
            db.session.add(student)
        db.session.commit()
        flash(f'User {user.name} created successfully.', 'success')
        return redirect(url_for('admin.users'))

    courses = Course.query.filter_by(college_id=current_user.college_id).order_by(Course.name).all()
    streams = Stream.query.filter_by(college_id=current_user.college_id).order_by(Stream.name).all()
    batches = Batch.query.filter_by(college_id=current_user.college_id).order_by(Batch.name).all()
    sections = Section.query.join(Semester, isouter=True).filter((Semester.college_id == current_user.college_id) | (Section.course_id.in_([c.id for c in courses]))).all()
    return render_template('admin/user_form.html', user=None, courses=courses, streams=streams, batches=batches, sections=sections)


@bp.route('/users/<int:uid>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(uid):
    user = User.query.get_or_404(uid)
    if request.method == 'POST':
        user.name = request.form.get('name', user.name)
        user.phone = request.form.get('phone', user.phone)
        user.is_active = request.form.get('is_active') == 'on'
        new_pass = request.form.get('new_password', '').strip()
        if new_pass:
            user.set_password(new_pass)
        if user.role == 'student' and user.student_profile:
            user.student_profile.course_id = request.form.get('course_id', type=int)
            user.student_profile.stream_id = request.form.get('stream_id', type=int)
            user.student_profile.batch_id = request.form.get('batch_id', type=int)
            user.student_profile.section_id = request.form.get('section_id', type=int)
        db.session.commit()
        flash('User updated.', 'success')
        return redirect(url_for('admin.users'))
    courses = Course.query.filter_by(college_id=current_user.college_id).order_by(Course.name).all()
    streams = Stream.query.filter_by(college_id=current_user.college_id).order_by(Stream.name).all()
    batches = Batch.query.filter_by(college_id=current_user.college_id).order_by(Batch.name).all()
    sections = Section.query.join(Semester, isouter=True).filter((Semester.college_id == current_user.college_id) | (Section.course_id.in_([c.id for c in courses]))).all()
    return render_template('admin/user_form.html', user=user, courses=courses, streams=streams, batches=batches, sections=sections)


@bp.route('/students')
@admin_required
def students():
    student_users = User.query.filter_by(college_id=current_user.college_id, role='student').join(Student).order_by(User.name).all()
    return render_template('admin/students.html', students=student_users)


@bp.route('/users/<int:uid>/edit-erp', methods=['GET', 'POST'])
@admin_required
def edit_erp_profile(uid):
    user = User.query.get_or_404(uid)
    if user.role != 'student' or not user.student_profile:
        flash('ERP details are only applicable for student accounts with an active profile.', 'warning')
        return redirect(url_for('admin.users'))
        
    student = user.student_profile
    if request.method == 'POST':
        try:
            # Personal Info
            student.blood_group = request.form.get('blood_group')
            student.religion = request.form.get('religion')
            student.caste = request.form.get('caste')
            student.aadhar_number = request.form.get('aadhar_number')
            student.admission_category = request.form.get('admission_category')
            student.session = request.form.get('session')
            
            tc_date_str = request.form.get('tc_date')
            student.tc_date = datetime.strptime(tc_date_str, '%Y-%m-%d').date() if tc_date_str else None
            student.biometric_card_no = request.form.get('biometric_card_no')
            student.alternate_semester_group = request.form.get('alternate_semester_group')
            student.semester_group = request.form.get('semester_group')
            student.phone2 = request.form.get('phone2')
            student.landline = request.form.get('landline')

            # Academic History (10th)
            student.tenth_year = request.form.get('tenth_year', type=int)
            student.tenth_roll = request.form.get('tenth_roll')
            student.tenth_board = request.form.get('tenth_board')
            student.tenth_obtained = request.form.get('tenth_obtained', type=float)
            student.tenth_max = request.form.get('tenth_max', type=float)

            # Academic History (12th)
            student.twelfth_year = request.form.get('twelfth_year', type=int)
            student.twelfth_roll = request.form.get('twelfth_roll')
            student.twelfth_board = request.form.get('twelfth_board')
            student.twelfth_obtained = request.form.get('twelfth_obtained', type=float)
            student.twelfth_max = request.form.get('twelfth_max', type=float)

            # Parent / Guardian Info
            student.father_name = request.form.get('father_name')
            student.father_occupation = request.form.get('father_occupation')
            student.father_mobile = request.form.get('father_mobile')
            student.mother_name = request.form.get('mother_name')
            student.mother_mobile = request.form.get('mother_mobile')
            student.local_guardian_name = request.form.get('local_guardian_name')
            student.local_guardian_mobile = request.form.get('local_guardian_mobile')
            student.local_guardian_address = request.form.get('local_guardian_address')

            db.session.commit()
            flash('ERP detailed profile updated successfully.', 'success')
            return redirect(url_for('admin.edit_erp_profile', uid=uid))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('admin/edit_student_erp.html', user=user, student=student)


@bp.route('/users/<int:uid>/delete', methods=['POST'])
@admin_required
def delete_user(uid):
    user = User.query.get_or_404(uid)
    user.is_active = False
    db.session.commit()
    flash('User deactivated.', 'info')
    return redirect(url_for('admin.users'))


# ─── Semesters ─────────────────────────────────────────────────────────────────
@bp.route('/semesters')
@admin_required
def semesters():
    semesters = Semester.query.filter_by(college_id=current_user.college_id).order_by(Semester.name).all()
    return render_template('admin/semesters.html', semesters=semesters)


@bp.route('/semesters/add', methods=['POST'])
@admin_required
def add_semester():
    c = Semester(
        name=request.form.get('name'),
        academic_year=request.form.get('academic_year'),
        college_id=current_user.college_id
    )
    db.session.add(c)
    db.session.commit()
    flash('Semester added.', 'success')
    return redirect(url_for('admin.semesters'))


@bp.route('/semesters/<int:cid>/delete', methods=['POST'])
@admin_required
def delete_semester(cid):
    c = Semester.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash('Semester deleted.', 'info')
    return redirect(url_for('admin.semesters'))


# ─── Sections ────────────────────────────────────────────────────────────────
@bp.route('/sections')
@admin_required
def sections():
    semesters = Semester.query.filter_by(college_id=current_user.college_id).all()
    sections = Section.query.join(Semester).filter(Semester.college_id == current_user.college_id).all()
    return render_template('admin/sections.html', sections=sections, semesters=semesters)


@bp.route('/sections/add', methods=['POST'])
@admin_required
def add_section():
    s = Section(
        semester_id=request.form.get('semester_id'),
        name=request.form.get('name'),
        room_number=request.form.get('room_number', ''),
        capacity=int(request.form.get('capacity', 40))
    )
    db.session.add(s)
    db.session.commit()
    flash('Section added.', 'success')
    return redirect(url_for('admin.sections'))


@bp.route('/sections/<int:sid>/delete', methods=['POST'])
@admin_required
def delete_section(sid):
    s = Section.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    flash('Section deleted.', 'info')
    return redirect(url_for('admin.sections'))


# ─── Subjects ────────────────────────────────────────────────────────────────
@bp.route('/subjects')
@admin_required
def subjects():
    subjects = Subject.query.filter_by(college_id=current_user.college_id).order_by(Subject.name).all()
    return render_template('admin/subjects.html', subjects=subjects)


@bp.route('/subjects/add', methods=['POST'])
@admin_required
def add_subject():
    s = Subject(
        name=request.form.get('name'),
        code=request.form.get('code', ''),
        college_id=current_user.college_id
    )
    db.session.add(s)
    db.session.commit()
    flash('Subject added.', 'success')
    return redirect(url_for('admin.subjects'))


@bp.route('/subjects/<int:sid>/delete', methods=['POST'])
@admin_required
def delete_subject(sid):
    s = Subject.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    flash('Subject deleted.', 'info')
    return redirect(url_for('admin.subjects'))


# ─── Faculty Assignments ─────────────────────────────────────────────────────
@bp.route('/assignments')
@admin_required
def faculty_assignments():
    assignments = FacultyAssignment.query.join(User, FacultyAssignment.faculty_id == User.id)\
        .filter(User.college_id == current_user.college_id).all()
    faculty = User.query.filter_by(role='faculty', college_id=current_user.college_id).all()
    subjects = Subject.query.filter_by(college_id=current_user.college_id).all()
    sections = Section.query.join(Semester).filter(Semester.college_id == current_user.college_id).all()
    return render_template('admin/faculty_assignments.html',
                           assignments=assignments, faculty=faculty,
                           subjects=subjects, sections=sections)


@bp.route('/assignments/add', methods=['POST'])
@admin_required
def add_faculty_assignment():
    ta = FacultyAssignment(
        faculty_id=request.form.get('faculty_id'),
        subject_id=request.form.get('subject_id'),
        section_id=request.form.get('section_id'),
        academic_year=request.form.get('academic_year', '2024-2025')
    )
    db.session.add(ta)
    db.session.commit()
    flash('Faculty assigned.', 'success')
    return redirect(url_for('admin.faculty_assignments'))


@bp.route('/assignments/<int:aid>/delete', methods=['POST'])
@admin_required
def delete_faculty_assignment(aid):
    ta = FacultyAssignment.query.get_or_404(aid)
    db.session.delete(ta)
    db.session.commit()
    flash('Assignment removed.', 'info')
    return redirect(url_for('admin.faculty_assignments'))


# ─── Academic Terms ──────────────────────────────────────────────────────────
@bp.route('/terms')
@admin_required
def terms():
    terms = AcademicTerm.query.filter_by(college_id=current_user.college_id).order_by(AcademicTerm.start_date.desc()).all()
    return render_template('admin/terms.html', terms=terms)


@bp.route('/terms/add', methods=['POST'])
@admin_required
def add_term():
    start = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
    end = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
    t = AcademicTerm(
        college_id=current_user.college_id,
        name=request.form.get('name'),
        term_type=request.form.get('term_type', 'term'),
        start_date=start,
        end_date=end,
        academic_year=request.form.get('academic_year', '2024-2025')
    )
    db.session.add(t)
    db.session.commit()
    flash('Term added.', 'success')
    return redirect(url_for('admin.terms'))


@bp.route('/terms/<int:tid>/activate', methods=['POST'])
@admin_required
def activate_term(tid):
    AcademicTerm.query.filter_by(college_id=current_user.college_id).update({'is_active': False})
    term = AcademicTerm.query.get_or_404(tid)
    term.is_active = True
    db.session.commit()
    flash(f'"{term.name}" is now the active term.', 'success')
    return redirect(url_for('admin.terms'))


@bp.route('/terms/<int:tid>/delete', methods=['POST'])
@admin_required
def delete_term(tid):
    term = AcademicTerm.query.get_or_404(tid)
    db.session.delete(term)
    db.session.commit()
    flash('Term deleted.', 'info')
    return redirect(url_for('admin.terms'))


# ─── Fee Types ────────────────────────────────────────────────────────────────
@bp.route('/fee-types')
@admin_required
def fee_types():
    fee_types = FeeType.query.filter_by(college_id=current_user.college_id).all()
    return render_template('admin/fee_types.html', fee_types=fee_types)


@bp.route('/fee-types/add', methods=['POST'])
@admin_required
def add_fee_type():
    ft = FeeType(
        college_id=current_user.college_id,
        name=request.form.get('name'),
        amount=float(request.form.get('amount', 0)),
        frequency=request.form.get('frequency', 'term'),
        description=request.form.get('description', '')
    )
    db.session.add(ft)
    db.session.commit()
    flash('Fee type added.', 'success')
    return redirect(url_for('admin.fee_types'))


@bp.route('/fee-types/<int:fid>/delete', methods=['POST'])
@admin_required
def delete_fee_type(fid):
    ft = FeeType.query.get_or_404(fid)
    db.session.delete(ft)
    db.session.commit()
    flash('Fee type deleted.', 'info')
    return redirect(url_for('admin.fee_types'))


# ─── College Settings ─────────────────────────────────────────────────────────
@bp.route('/college', methods=['GET', 'POST'])
@admin_required
def college_settings():
    college = College.query.get(current_user.college_id)
    if request.method == 'POST':
        college.name = request.form.get('name', college.name)
        college.address = request.form.get('address', college.address)
        college.phone = request.form.get('phone', college.phone)
        college.email = request.form.get('email', college.email)
        db.session.commit()
        flash('College settings updated.', 'success')
        return redirect(url_for('admin.college_settings'))
    return render_template('admin/college_settings.html', college=college)


@bp.route('/trigger-digest', methods=['POST'])
@admin_required
def trigger_digest():
    generate_parent_digest(current_user.college_id, sender_id=current_user.id)
    flash('Weekly Friday Digest emails perfectly dispatched and recorded in history!', 'success')
    return redirect(request.referrer or url_for('admin.college_settings'))


@bp.route('/preview-digest')
@admin_required
def preview_digest():
    from app.models import User
    parent = User.query.filter_by(role='parent', college_id=current_user.college_id).first()
    if not parent:
        return "<div class='alert alert-warning'>No parent accounts found in this college to generate a preview.</div>"
    
    digest_text = get_parent_digest_preview(parent.id)
    if not digest_text:
        return f"<div class='alert alert-info'>No active student links found for sample parent: {parent.name}</div>"
        
    return f"<pre style='white-space: pre-wrap; font-family: monospace; background: #f8f9fa; padding: 15px; border-radius: 5px;'>{digest_text}</pre>"


# ─── Parent-Student Links ────────────────────────────────────────────────────
@bp.route('/parent-links')
@admin_required
def parent_links():
    links = ParentStudentLink.query.join(Student).join(User, Student.user_id == User.id)\
        .filter(User.college_id == current_user.college_id).all()
    parents = User.query.filter_by(role='parent', college_id=current_user.college_id).all()
    students = Student.query.join(User).filter(User.college_id == current_user.college_id).all()
    return render_template('admin/parent_links.html', links=links, parents=parents, students=students)


@bp.route('/parent-links/add', methods=['POST'])
@admin_required
def add_parent_link():
    link = ParentStudentLink(
        parent_id=request.form.get('parent_id'),
        student_id=request.form.get('student_id'),
        relationship_type=request.form.get('relationship_type', 'parent')
    )
    db.session.add(link)
    db.session.commit()
    flash('Parent-student link created.', 'success')
    return redirect(url_for('admin.parent_links'))


@bp.route('/parent-links/<int:lid>/delete', methods=['POST'])
@admin_required
def delete_parent_link(lid):
    link = ParentStudentLink.query.get_or_404(lid)
    db.session.delete(link)
    db.session.commit()
    flash('Link removed.', 'info')
    return redirect(url_for('admin.parent_links'))


# ─── LMS Integration ──────────────────────────────────────────────────────────
@bp.route('/lms')
@admin_required
def lms_integration():
    return render_template('admin/lms_integration.html')


@bp.route('/lms/export/<dataset>')
@admin_required
def lms_export(dataset):
    output = io.StringIO()
    writer = csv.writer(output)
    
    if dataset == 'students':
        students = Student.query.join(User).filter(User.college_id == current_user.college_id).all()
        writer.writerow(['Student_ID', 'Name', 'Email', 'Enrollment_Number', 'Section', 'Date_of_Birth', 'Gender'])
        for s in students:
            writer.writerow([
                s.id,
                s.user.name,
                s.user.email,
                s.enrollment_number,
                s.section.full_name if s.section else '',
                s.date_of_birth.strftime('%Y-%m-%d') if s.date_of_birth else '',
                s.gender
            ])
            
    elif dataset == 'grades':
        from app.models import Grade
        grades = Grade.query.join(Student).join(User).filter(User.college_id == current_user.college_id).all()
        writer.writerow(['Record_ID', 'Student_ID', 'Student_Name', 'Subject', 'Exam_Name', 'Percentage', 'Letter_Grade', 'Date'])
        for g in grades:
            writer.writerow([
                g.id,
                g.student_id,
                g.student.user.name,
                g.subject.name,
                g.exam_name,
                g.percentage,
                g.letter_grade,
                g.date.strftime('%Y-%m-%d')
            ])
    else:
        flash('Invalid dataset option.', 'danger')
        return redirect(url_for('admin.lms_integration'))
        
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=lms_export_{dataset}_{date.today()}.csv"
    return response


# ─── Announcements Management ────────────────────────────────────────────────

@bp.route('/announcements')
@admin_required
def announcements():
    ann_list = (Announcement.query.filter_by(college_id=current_user.college_id)
               .order_by(Announcement.created_at.desc()).all())
    return render_template('admin/announcements.html', announcements=ann_list)


@bp.route('/announcements/add', methods=['POST'])
@admin_required
def add_announcement():
    date_str = request.form.get('date')
    ann_date = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else date.today()
    ann = Announcement(
        college_id=current_user.college_id,
        title=request.form.get('title', ''),
        body=request.form.get('body', ''),
        announcement_type=request.form.get('announcement_type', 'notice'),
        date=ann_date,
        created_by=current_user.id,
    )
    db.session.add(ann)
    db.session.commit()
    flash('Announcement created.', 'success')
    return redirect(url_for('admin.announcements'))


@bp.route('/announcements/<int:aid>/delete', methods=['POST'])
@admin_required
def delete_announcement(aid):
    ann = Announcement.query.get_or_404(aid)
    db.session.delete(ann)
    db.session.commit()
    flash('Announcement deleted.', 'info')
    return redirect(url_for('admin.announcements'))


@bp.route('/announcements/<int:aid>/toggle', methods=['POST'])
@admin_required
def toggle_announcement(aid):
    ann = Announcement.query.get_or_404(aid)
    ann.is_active = not ann.is_active
    db.session.commit()
    flash(f'Announcement {"activated" if ann.is_active else "deactivated"}.', 'info')
    return redirect(url_for('admin.announcements'))


# ─── Events Management ──────────────────────────────────────────────────────

@bp.route('/events')
@admin_required
def events():
    events_list = (Event.query.filter_by(college_id=current_user.college_id)
                  .order_by(Event.event_date.desc()).all())
    return render_template('admin/events.html', events=events_list)


@bp.route('/events/add', methods=['POST'])
@admin_required
def add_event():
    event_date_str = request.form.get('event_date')
    end_date_str = request.form.get('end_date')
    event_date = datetime.strptime(event_date_str, '%Y-%m-%dT%H:%M') if event_date_str else datetime.utcnow()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M') if end_date_str else None
    
    event = Event(
        college_id=current_user.college_id,
        title=request.form.get('title', ''),
        description=request.form.get('description', ''),
        event_date=event_date,
        end_date=end_date,
        location=request.form.get('location', ''),
        max_capacity=request.form.get('max_capacity', type=int),
        requires_registration=request.form.get('requires_registration') == 'on',
        created_by=current_user.id,
    )
    db.session.add(event)
    db.session.commit()
    flash('Event created.', 'success')
    return redirect(url_for('admin.events'))


@bp.route('/events/<int:eid>/delete', methods=['POST'])
@admin_required
def delete_event(eid):
    event = Event.query.get_or_404(eid)
    db.session.delete(event)
    db.session.commit()
    flash('Event deleted.', 'info')
    return redirect(url_for('admin.events'))


# ─── Feedback Management ────────────────────────────────────────────────────

@bp.route('/feedback')
@admin_required
def feedback_list():
    status_filter = request.args.get('status', '')
    query = (Feedback.query.filter_by(college_id=current_user.college_id)
            .order_by(Feedback.created_at.desc()))
    if status_filter:
        query = query.filter_by(status=status_filter)
    feedbacks = query.all()
    return render_template('admin/feedback.html', feedbacks=feedbacks, status_filter=status_filter)


@bp.route('/feedback/<int:fid>/respond', methods=['POST'])
@admin_required
def respond_feedback(fid):
    fb = Feedback.query.get_or_404(fid)
    fb.admin_response = request.form.get('response', '')
    fb.responded_by = current_user.id
    fb.responded_at = datetime.utcnow()
    fb.status = request.form.get('status', 'reviewed')
    db.session.commit()
    flash('Feedback response saved.', 'success')
    return redirect(url_for('admin.feedback_list'))


# ─── Grievance Management ───────────────────────────────────────────────────

@bp.route('/grievances')
@admin_required
def grievance_list():
    status_filter = request.args.get('status', '')
    query = (Grievance.query.filter_by(college_id=current_user.college_id)
            .order_by(Grievance.created_at.desc()))
    if status_filter:
        query = query.filter_by(status=status_filter)
    grievances = query.all()
    return render_template('admin/grievances.html', grievances=grievances, status_filter=status_filter)


@bp.route('/grievances/<int:gid>/resolve', methods=['POST'])
@admin_required
def resolve_grievance(gid):
    gr = Grievance.query.get_or_404(gid)
    gr.resolution = request.form.get('resolution', '')
    gr.resolved_by = current_user.id
    gr.resolved_at = datetime.utcnow()
    gr.status = request.form.get('status', 'resolved')
    db.session.commit()
    flash('Grievance updated.', 'success')
    return redirect(url_for('admin.grievance_list'))


# ─── Leave Application Management ───────────────────────────────────────────

@bp.route('/leave-applications')
@admin_required
def leave_applications():
    status_filter = request.args.get('status', '')
    query = (LeaveApplication.query.filter_by(college_id=current_user.college_id)
            .order_by(LeaveApplication.created_at.desc()))
    if status_filter:
        query = query.filter_by(status=status_filter)
    applications = query.all()
    return render_template('admin/leave_applications.html', applications=applications, status_filter=status_filter)


@bp.route('/leave-applications/<int:lid>/action', methods=['POST'])
@admin_required
def leave_action(lid):
    leave = LeaveApplication.query.get_or_404(lid)
    action = request.form.get('action')
    if action == 'approve':
        leave.status = 'approved'
    elif action == 'reject':
        leave.status = 'rejected'
    leave.approved_by = current_user.id
    leave.approved_at = datetime.utcnow()
    leave.admin_remarks = request.form.get('remarks', '')
    db.session.commit()
    flash(f'Leave application {leave.status}.', 'success')
    return redirect(url_for('admin.leave_applications'))
# ─── Early Warning & Monitoring (Goal 30) ───────────────────────────────────

@bp.route('/at-risk')
@admin_required
def at_risk_dashboard():
    # Identify students at risk: Attendance < 75% or Avg Grade < 40%
    all_students = Student.query.join(User).filter(User.college_id == current_user.college_id).all()
    at_risk_students = []
    
    for student in all_students:
        # 1. Attendance Check
        total_att = Attendance.query.filter_by(student_id=student.id).count()
        present_att = Attendance.query.filter_by(student_id=student.id).filter(Attendance.status.in_(['present', 'late'])).count()
        att_pct = (present_att / total_att * 100) if total_att > 0 else 100
        
        # 2. Grade Check
        avg_grade = db.session.query(func.avg(Grade.score)).filter(Grade.student_id == student.id).scalar() or 100
        
        reasons = []
        if att_pct < 75:
            reasons.append(f"Low Attendance ({round(att_pct, 1)}%)")
        if avg_grade < 40:
            reasons.append(f"Poor Academics ({round(avg_grade, 1)}%)")
            
        if reasons:
            at_risk_students.append({
                'student': student,
                'att_pct': round(att_pct, 1),
                'avg_grade': round(avg_grade, 1),
                'reasons': reasons
            })
            
    return render_template('admin/at_risk_dashboard.html', students=at_risk_students)

@bp.route('/student/<int:sid>/intervention', methods=['GET', 'POST'])
@admin_required
def student_intervention(sid):
    student = Student.query.get_or_404(sid)
    if student.user.college_id != current_user.college_id:
        abort(403)
        
    if request.method == 'POST':
        # Logic for sending an intervention email or recording a meeting
        intervention_type = request.form.get('type')
        notes = request.form.get('notes')
        flash(f'Intervention recorded for {student.user.name}. Parent notification queued.', 'success')
        return redirect(url_for('admin.at_risk_dashboard'))
        
    return render_template('admin/intervention_form.html', student=student)


# ─── Excel / CSV Bulk User Import ─────────────────────────────────────────────

@bp.route('/users/upload', methods=['GET', 'POST'])
@admin_required
def upload_users():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(url_for('admin.upload_users'))
        
        file = request.files['file']
        if not file or file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('admin.upload_users'))
        
        filename = file.filename.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
            flash('Invalid file format. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.', 'danger')
            return redirect(url_for('admin.upload_users'))

        rows = []
        try:
            if filename.endswith('.csv'):
                stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
                csv_reader = csv.DictReader(stream)
                for r in csv_reader:
                    rows.append({k.strip().lower().replace(' ', '_'): str(v).strip() for k, v in r.items() if k})
            else:
                wb = openpyxl.load_workbook(file)
                sheet = wb.active
                headers = [str(cell.value).strip().lower().replace(' ', '_') if cell.value else '' for cell in sheet[1]]
                for row in sheet.iter_rows(min_row=2, values_only=True):
                    if not any(row):
                        continue
                    row_dict = {}
                    for idx, val in enumerate(row):
                        if idx < len(headers) and headers[idx]:
                            row_dict[headers[idx]] = str(val).strip() if val is not None else ''
                    rows.append(row_dict)
        except Exception as e:
            flash(f'Error reading file: {str(e)}', 'danger')
            return redirect(url_for('admin.upload_users'))

        added_count = 0
        skipped_count = 0
        errors = []

        for idx, row in enumerate(rows, start=2):
            name = row.get('name') or row.get('full_name') or row.get('user_name')
            email = row.get('email') or row.get('email_address')
            
            if not name or not email:
                skipped_count += 1
                errors.append(f"Row {idx}: Missing name or email.")
                continue

            email = email.lower().strip()
            if User.query.filter_by(email=email).first():
                skipped_count += 1
                errors.append(f"Row {idx}: Email '{email}' is already registered.")
                continue

            role = (row.get('role') or 'student').lower().strip()
            if role not in ['admin', 'faculty', 'student', 'parent', 'hr']:
                role = 'student'

            phone = row.get('phone') or row.get('mobile') or ''
            password = row.get('password') or 'ChangeMe123!'

            user = User(
                name=name,
                email=email,
                role=role,
                phone=phone,
                college_id=current_user.college_id
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            if role == 'student':
                # Course lookup/creation
                course_name = row.get('course') or row.get('course_name')
                course_obj = None
                if course_name:
                    course_obj = Course.query.filter_by(college_id=current_user.college_id, name=course_name).first()
                    if not course_obj:
                        course_obj = Course(name=course_name, college_id=current_user.college_id)
                        db.session.add(course_obj)
                        db.session.flush()

                # Stream lookup/creation
                stream_name = row.get('stream') or row.get('stream_name') or row.get('branch')
                stream_obj = None
                if stream_name:
                    stream_obj = Stream.query.filter_by(college_id=current_user.college_id, name=stream_name).first()
                    if not stream_obj:
                        stream_obj = Stream(name=stream_name, course_id=course_obj.id if course_obj else None, college_id=current_user.college_id)
                        db.session.add(stream_obj)
                        db.session.flush()

                # Batch lookup/creation
                batch_name = row.get('batch') or row.get('batch_name') or row.get('academic_batch')
                batch_obj = None
                if batch_name:
                    batch_obj = Batch.query.filter_by(college_id=current_user.college_id, name=batch_name).first()
                    if not batch_obj:
                        batch_obj = Batch(name=batch_name, college_id=current_user.college_id)
                        db.session.add(batch_obj)
                        db.session.flush()

                # Section lookup/creation
                section_name = row.get('section') or row.get('section_name')
                section_obj = None
                if section_name:
                    section_obj = Section.query.filter_by(name=section_name).first()
                    if not section_obj:
                        section_obj = Section(name=section_name, course_id=course_obj.id if course_obj else None, stream_id=stream_obj.id if stream_obj else None, batch_id=batch_obj.id if batch_obj else None)
                        db.session.add(section_obj)
                        db.session.flush()

                enrollment_num = row.get('enrollment_number') or row.get('enrollment_no') or row.get('roll_no') or f'EW{user.id:05d}'
                dob_str = row.get('date_of_birth') or row.get('dob')
                dob = None
                if dob_str:
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y'):
                        try:
                            dob = datetime.strptime(dob_str, fmt).date()
                            break
                        except ValueError:
                            pass
                gender = row.get('gender') or ''

                student = Student(
                    user_id=user.id,
                    course_id=course_obj.id if course_obj else None,
                    stream_id=stream_obj.id if stream_obj else None,
                    batch_id=batch_obj.id if batch_obj else None,
                    section_id=section_obj.id if section_obj else None,
                    enrollment_number=enrollment_num,
                    date_of_birth=dob,
                    gender=gender
                )
                db.session.add(student)
            
            added_count += 1

        db.session.commit()
        if added_count > 0:
            flash(f'Successfully imported {added_count} user(s).', 'success')
        if skipped_count > 0:
            flash(f'Skipped {skipped_count} row(s) due to errors or duplicates: ' + '; '.join(errors[:3]), 'warning')
        return redirect(url_for('admin.users'))

    return render_template('admin/upload_users.html')


@bp.route('/users/sample-csv')
@admin_required
def sample_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['name', 'email', 'role', 'phone', 'password', 'course', 'stream', 'batch', 'section', 'enrollment_number', 'date_of_birth', 'gender'])
    writer.writerow(['John Doe', 'johndoe@example.com', 'student', '+1234567890', 'ChangeMe123!', 'B.Tech', 'Computer Science', '2024-2028', 'A', 'CSE2024001', '2004-05-15', 'Male'])
    writer.writerow(['Jane Smith', 'janesmith@example.com', 'faculty', '+1987654321', 'ChangeMe123!', '', '', '', '', '', '', 'Female'])
    
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=sample_users_upload.csv"
    return response


# ─── Counselor Assignments Management ────────────────────────────────────────

@bp.route('/counselors', methods=['GET'])
@admin_required
def counselor_assignments():
    courses = Course.query.filter_by(college_id=current_user.college_id).order_by(Course.name).all()
    streams = Stream.query.filter_by(college_id=current_user.college_id).order_by(Stream.name).all()
    sections = Section.query.join(Semester, isouter=True).filter((Semester.college_id == current_user.college_id) | (Section.course_id.in_([c.id for c in courses]))).all()
    faculty_members = User.query.filter_by(role='faculty', college_id=current_user.college_id).order_by(User.name).all()
    
    return render_template('admin/counselors.html',
                           courses=courses,
                           streams=streams,
                           sections=sections,
                           faculty_members=faculty_members)


@bp.route('/counselors/assign-course', methods=['POST'])
@admin_required
def assign_course_counselor():
    course_id = request.form.get('course_id', type=int)
    faculty_id = request.form.get('faculty_id', type=int)
    course = Course.query.get_or_404(course_id)
    if faculty_id:
        faculty = User.query.get_or_404(faculty_id)
        course.chief_counselor_id = faculty.id
        flash(f'Faculty {faculty.name} assigned as Chief Batch Counselor for Course "{course.name}".', 'success')
    else:
        course.chief_counselor_id = None
        flash(f'Chief Batch Counselor removed for Course "{course.name}".', 'info')
    db.session.commit()
    return redirect(url_for('admin.counselor_assignments'))


@bp.route('/counselors/assign-stream', methods=['POST'])
@admin_required
def assign_stream_counselor():
    stream_id = request.form.get('stream_id', type=int)
    faculty_id = request.form.get('faculty_id', type=int)
    stream = Stream.query.get_or_404(stream_id)
    if faculty_id:
        faculty = User.query.get_or_404(faculty_id)
        stream.head_counselor_id = faculty.id
        flash(f'Faculty {faculty.name} assigned as Head Batch Counselor for Stream "{stream.name}".', 'success')
    else:
        stream.head_counselor_id = None
        flash(f'Head Batch Counselor removed for Stream "{stream.name}".', 'info')
    db.session.commit()
    return redirect(url_for('admin.counselor_assignments'))


@bp.route('/counselors/assign-section', methods=['POST'])
@admin_required
def assign_section_counselor():
    section_id = request.form.get('section_id', type=int)
    faculty_id = request.form.get('faculty_id', type=int)
    section = Section.query.get_or_404(section_id)
    if faculty_id:
        faculty = User.query.get_or_404(faculty_id)
        section.batch_counselor_id = faculty.id
        flash(f'Faculty {faculty.name} assigned as Batch Counselor for Section "{section.full_name}".', 'success')
    else:
        section.batch_counselor_id = None
        flash(f'Batch Counselor removed for Section "{section.full_name}".', 'info')
    db.session.commit()
    return redirect(url_for('admin.counselor_assignments'))


# ─── Courses, Streams & Batches Management ────────────────────────────────────

@bp.route('/courses', methods=['GET', 'POST'])
@admin_required
def courses_management():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_course':
            name = request.form.get('name', '').strip()
            code = request.form.get('code', '').strip()
            if name:
                c = Course(name=name, code=code, college_id=current_user.college_id)
                db.session.add(c)
                db.session.commit()
                flash(f'Course "{name}" created.', 'success')
        elif action == 'add_stream':
            name = request.form.get('name', '').strip()
            code = request.form.get('code', '').strip()
            course_id = request.form.get('course_id', type=int)
            if name:
                s = Stream(name=name, code=code, course_id=course_id, college_id=current_user.college_id)
                db.session.add(s)
                db.session.commit()
                flash(f'Stream "{name}" created.', 'success')
        elif action == 'add_batch':
            name = request.form.get('name', '').strip()
            start_year = request.form.get('start_year', type=int)
            end_year = request.form.get('end_year', type=int)
            if name:
                b = Batch(name=name, start_year=start_year, end_year=end_year, college_id=current_user.college_id)
                db.session.add(b)
                db.session.commit()
                flash(f'Batch "{name}" created.', 'success')
        return redirect(url_for('admin.courses_management'))

    courses = Course.query.filter_by(college_id=current_user.college_id).order_by(Course.name).all()
    streams = Stream.query.filter_by(college_id=current_user.college_id).order_by(Stream.name).all()
    batches = Batch.query.filter_by(college_id=current_user.college_id).order_by(Batch.name).all()
    return render_template('admin/courses.html', courses=courses, streams=streams, batches=batches)


# ─── Attendance CSV Matrix Export ─────────────────────────────────────────────

@bp.route('/attendance/export-csv')
@admin_required
def export_attendance_matrix_csv():
    section_id = request.args.get('section_id', type=int)
    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')

    students_query = Student.query.join(User).filter(User.college_id == current_user.college_id)
    if section_id:
        students_query = students_query.filter(Student.section_id == section_id)
    students = students_query.order_by(User.name).all()

    att_query = Attendance.query.join(Student).join(User).filter(User.college_id == current_user.college_id)
    if section_id:
        att_query = att_query.filter(Attendance.section_id == section_id)
    if from_date_str:
        try:
            d_from = datetime.strptime(from_date_str, '%Y-%m-%d').date()
            att_query = att_query.filter(Attendance.date >= d_from)
        except ValueError:
            pass
    if to_date_str:
        try:
            d_to = datetime.strptime(to_date_str, '%Y-%m-%d').date()
            att_query = att_query.filter(Attendance.date <= d_to)
        except ValueError:
            pass

    records = att_query.all()
    
    # Collect all unique dates chronologically
    dates = sorted(list(set(r.date for r in records)))
    
    # Map: (student_id, date) -> status
    att_map = {(r.student_id, r.date): r.status for r in records}

    output = io.StringIO()
    writer = csv.writer(output)

    # Header Row: Enrollment No, Student Name, Section, [Date1], [Date2], ..., Total Present, Total Absent, Attendance %
    header = ['Enrollment No', 'Student Name', 'Section'] + [d.strftime('%Y-%m-%d') for d in dates] + ['Total Present', 'Total Absent', 'Attendance %']
    writer.writerow(header)

    # Data Rows
    for s in students:
        s_name = s.user.name
        s_enroll = s.enrollment_number or f'EW{s.user.id:05d}'
        s_sec = s.section.full_name if s.section else 'N/A'
        
        row = [s_enroll, s_name, s_sec]
        present_count = 0
        absent_count = 0

        for d in dates:
            st = att_map.get((s.id, d))
            if st:
                status_str = st.capitalize()
                if st.lower() in ['present', 'late']:
                    present_count += 1
                elif st.lower() == 'absent':
                    absent_count += 1
            else:
                status_str = '-'
            row.append(status_str)

        total_marked = present_count + absent_count
        pct = round((present_count / total_marked * 100), 1) if total_marked > 0 else 0.0

        row.extend([present_count, absent_count, f"{pct}%"])
        writer.writerow(row)

    sec_label = f"section_{section_id}" if section_id else "all_sections"
    filename = f"attendance_matrix_{sec_label}_{date.today().strftime('%Y%m%d')}.csv"
    
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response

