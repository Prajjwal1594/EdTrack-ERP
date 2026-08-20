from flask import render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from app.reports import bp
from app.models import (Student, Grade, Attendance, AcademicTerm, ReportComment,
                         ParentStudentLink, Subject)
from app import db
from datetime import date


def can_view_student(student_id):
    """Check if current user has permission to view this student."""
    if current_user.role in ['admin', 'superadmin', 'it_admin', 'principal', 'registrar', 'hod', 'admission_officer', 'examination_officer', 'academic_advisor', 'course_coordinator', 'student_affairs', 'placement_officer', 'librarian', 'hostel_warden', 'transport_manager', 'accountant', 'hr', 'alumni', 'employer']:
        return True
    if current_user.role == 'faculty':
        student = Student.query.get(student_id)
        if student and student.section_id:
            from app.models import FacultyAssignment
            ta = FacultyAssignment.query.filter_by(
                faculty_id=current_user.id,
                section_id=student.section_id
            ).first()
            return ta is not None
    if current_user.role == 'student':
        student = Student.query.filter_by(user_id=current_user.id, id=student_id).first()
        return student is not None
    if current_user.role == 'parent':
        link = ParentStudentLink.query.filter_by(
            parent_id=current_user.id, student_id=student_id).first()
        return link is not None
    return False


@bp.route('/card/<int:student_id>')
@login_required
def report_card(student_id):
    if not can_view_student(student_id):
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.dashboard'))

    student = Student.query.get_or_404(student_id)
    terms = AcademicTerm.query.filter_by(college_id=current_user.college_id).all()
    active_term = AcademicTerm.query.filter_by(college_id=current_user.college_id, is_active=True).first()
    term_id = request.args.get('term_id', active_term.id if active_term else None, type=int)
    selected_term = AcademicTerm.query.get(term_id) if term_id else active_term

    grades = Grade.query.filter_by(student_id=student_id)
    if term_id:
        grades = grades.filter_by(term_id=term_id)
    grades = grades.all()

    # Group by subject and compute averages
    subject_summaries = {}
    for g in grades:
        sid = g.subject_id
        if sid not in subject_summaries:
            subject_summaries[sid] = {
                'subject': g.subject,
                'grades': [],
                'average': 0
            }
        subject_summaries[sid]['grades'].append(g)

    for sid, summary in subject_summaries.items():
        pcts = [g.percentage for g in summary['grades']]
        summary['average'] = round(sum(pcts) / len(pcts), 1) if pcts else 0

    # Attendance
    att_query = Attendance.query.filter_by(student_id=student_id)
    if selected_term:
        att_query = att_query.filter(
            Attendance.date >= selected_term.start_date,
            Attendance.date <= selected_term.end_date
        )
    attendance_records = att_query.all()
    total_days = len(attendance_records)
    present_days = sum(1 for a in attendance_records if a.status in ('present', 'late'))
    att_pct = round((present_days / total_days * 100), 1) if total_days > 0 else 0

    # Faculty comments
    comments = []
    if term_id:
        comments = ReportComment.query.filter_by(student_id=student_id, term_id=term_id).all()

    # Overall average
    all_avgs = [s['average'] for s in subject_summaries.values()]
    overall_avg = round(sum(all_avgs) / len(all_avgs), 1) if all_avgs else 0

    pdf_mode = request.args.get('pdf') == '1'

    context = dict(
        student=student,
        subject_summaries=subject_summaries,
        attendance_records=attendance_records,
        total_days=total_days,
        present_days=present_days,
        att_pct=att_pct,
        comments=comments,
        terms=terms,
        selected_term=selected_term,
        selected_term_id=term_id,
        overall_avg=overall_avg,
        today=date.today(),
        pdf_mode=pdf_mode
    )

    if pdf_mode:
        html = render_template('reports/report_card_pdf.html', **context)
        try:
            from weasyprint import HTML
            pdf = HTML(string=html).write_pdf()
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = \
                f'attachment; filename=report_card_{student.enrollment_number}_{term_id}.pdf'
            return response
        except Exception as e:
            flash(f'PDF generation failed: {e}. Showing HTML version.', 'warning')
            return render_template('reports/report_card.html', **context)

    return render_template('reports/report_card.html', **context)


@bp.route('/section/<int:section_id>')
@login_required
def section_report(section_id):
    if current_user.role not in ('admin', 'faculty'):
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.dashboard'))

    from app.models import Section
    section = Section.query.get_or_404(section_id)
    students = Student.query.filter_by(section_id=section_id).all()
    active_term = AcademicTerm.query.filter_by(college_id=current_user.college_id, is_active=True).first()
    term_id = request.args.get('term_id', active_term.id if active_term else None, type=int)
    terms = AcademicTerm.query.filter_by(college_id=current_user.college_id).all()

    student_data = []
    for student in students:
        grades = Grade.query.filter_by(student_id=student.id)
        if term_id:
            grades = grades.filter_by(term_id=term_id)
        grades = grades.all()
        pcts = [g.percentage for g in grades]
        avg = round(sum(pcts) / len(pcts), 1) if pcts else 0

        total_att = Attendance.query.filter_by(student_id=student.id).count()
        present_att = Attendance.query.filter_by(student_id=student.id, status='present').count()
        att_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 0

        student_data.append({
            'student': student,
            'average': avg,
            'att_pct': att_pct,
            'grade_count': len(grades)
        })

    student_data.sort(key=lambda x: x['average'], reverse=True)

    return render_template('reports/section_report.html',
                           section=section, student_data=student_data,
                           terms=terms, selected_term_id=term_id,
                           active_term=active_term)
