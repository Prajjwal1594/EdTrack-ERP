from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app.parent import bp
from app.models import (ParentStudentLink, Student, Grade, Attendance,
                         Assignment, AssignmentSubmission, AcademicTerm, FeePayment, Message)
from app import db
from datetime import date, timedelta


def parent_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'parent':
            flash('Parent access required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated)


@bp.route('/children')
@parent_required
def children_list():
    return redirect(url_for('parent.dashboard'))


@bp.route('/dashboard')
@parent_required
def dashboard():
    links = ParentStudentLink.query.filter_by(parent_id=current_user.id).all()
    children = [link.student for link in links]

    summaries = []
    for child in children:
        # Recent grades
        recent_grades = Grade.query.filter_by(student_id=child.id).order_by(Grade.date.desc()).limit(3).all()

        # Attendance
        thirty_ago = date.today() - timedelta(days=30)
        total = Attendance.query.filter_by(student_id=child.id).filter(Attendance.date >= thirty_ago).count()
        present = Attendance.query.filter_by(student_id=child.id, status='present').filter(Attendance.date >= thirty_ago).count()
        att_pct = round((present / total * 100), 1) if total > 0 else 100

        # Holistic Score & Soft Skills
        holistic_score = child.holistic_growth_score()
        holistic_rating = child.holistic_rating
        from app.models import SoftSkillMetric
        latest_skills = child.soft_skills.order_by(SoftSkillMetric.week_ending.desc()).first()
        
        # Subject Averages
        from sqlalchemy import func
        subject_avg_data = db.session.query(
            Grade.subject_id, func.avg(Grade.score)
        ).filter(Grade.student_id == child.id).group_by(Grade.subject_id).all()
        
        from app.models import Subject
        subject_averages = []
        for sid, avg in subject_avg_data:
            subj = Subject.query.get(sid)
            subject_averages.append({"subject": subj.name if subj else "Unknown", "avg": round(avg, 1) if avg is not None else 0.0})

        # Performance Trend
        trend_data = (Grade.query.filter_by(student_id=child.id)
                      .order_by(Grade.date.desc()).limit(10).all())
        performance_trend = [{"exam": g.exam_name, "avg": g.percentage} for g in reversed(trend_data)]

        # Holistic Data for Radar
        radar_data = {
            'avg_grade': sum(v['avg'] for v in subject_averages) / len(subject_averages) if subject_averages else 75,
            'attendance_pct': att_pct,
            'soft_skills': {
                'leadership': latest_skills.leadership if latest_skills else 5,
                'discipline': latest_skills.discipline if latest_skills else 5,
                'communication': latest_skills.communication if latest_skills else 5,
                'teamwork': latest_skills.teamwork if latest_skills else 5
            }
        }
        # Pending Fees
        pending_fees = FeePayment.query.filter_by(student_id=child.id, status='pending').count()

        summaries.append({
            'student': child,
            'recent_grades': recent_grades,
            'att_pct': att_pct,
            'pending_fees': pending_fees,
            'holistic_score': holistic_score,
            'holistic_rating': holistic_rating,
            'subject_averages': subject_averages,
            'performance_trend': performance_trend,
            'radar_data': radar_data
        })

    # Weekly Digest History
    digests = Message.query.filter_by(recipient_id=current_user.id, message_type='digest').order_by(Message.sent_at.desc()).all()

    return render_template('parent/dashboard.html', summaries=summaries, digests=digests)


@bp.route('/child/<int:student_id>')
@parent_required
def child_detail(student_id):
    # Verify this is their child
    link = ParentStudentLink.query.filter_by(parent_id=current_user.id, student_id=student_id).first()
    if not link:
        flash('Access denied.', 'danger')
        return redirect(url_for('parent.dashboard'))

    student = Student.query.get_or_404(student_id)
    terms = AcademicTerm.query.filter_by(college_id=current_user.college_id).all()
    active_term = AcademicTerm.query.filter_by(college_id=current_user.college_id, is_active=True).first()
    term_id = request.args.get('term_id', active_term.id if active_term else None, type=int)

    grades = Grade.query.filter_by(student_id=student_id)
    if term_id:
        grades = grades.filter_by(term_id=term_id)
    grades = grades.order_by(Grade.date.desc()).all()

    fee_payments = FeePayment.query.filter_by(student_id=student_id).order_by(FeePayment.created_at.desc()).all()

    # Phase 5: Infrastructure & Library
    from app.models import TransportAllocation, HostelAllocation, BookIssue
    transport = TransportAllocation.query.filter_by(student_id=student.id).first()
    hostel = HostelAllocation.query.filter_by(student_id=student.id, status='Occupied').first()
    overdue_books = BookIssue.query.filter_by(user_id=student.user_id, status='Issued').filter(BookIssue.due_date < date.today()).all()

    return render_template('parent/child_detail.html', student=student,
                           grades=grades, by_subject=by_subject,
                           attendance=attendance, att_pct=att_pct,
                           terms=terms, active_term=active_term,
                           selected_term_id=term_id, fee_payments=fee_payments,
                           transport=transport, hostel=hostel, overdue_books=overdue_books)
