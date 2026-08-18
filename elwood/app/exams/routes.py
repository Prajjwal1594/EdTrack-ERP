from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.exams import bp
from app.models import (Exam, ExamQuestion, ExamSubmission, Student,
                         FacultyAssignment, Subject, Section, AcademicTerm, Grade)
from app import db
from datetime import datetime
import json


def faculty_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('faculty', 'admin'):
            flash('Faculty access required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated)


@bp.route('/')
@login_required
def index():
    if current_user.role in ('faculty', 'admin'):
        exams = Exam.query.filter_by(created_by=current_user.id).order_by(Exam.created_at.desc()).all()
        ta_list = FacultyAssignment.query.filter_by(faculty_id=current_user.id).all() if current_user.role == 'faculty' else []
        subjects = Subject.query.filter_by(college_id=current_user.college_id).all()
        sections = Section.query.join(
            __import__('app.models', fromlist=['Semester']).Semester
        ).filter(
            __import__('app.models', fromlist=['Semester']).Semester.college_id == current_user.college_id
        ).all()
        return render_template('exams/faculty_list.html', exams=exams, ta_list=ta_list,
                               subjects=subjects, sections=sections)
    else:
        student = Student.query.filter_by(user_id=current_user.id).first()
        if not student:
            flash('Student profile not found.', 'danger')
            return redirect(url_for('auth.dashboard'))
        exams = Exam.query.filter_by(section_id=student.section_id, is_published=True).order_by(Exam.start_time).all()
        submissions = {s.exam_id: s for s in ExamSubmission.query.filter_by(student_id=student.id).all()}
        return render_template('exams/student_list.html', exams=exams, submissions=submissions, student=student)


@bp.route('/create', methods=['GET', 'POST'])
@faculty_required
def create_exam():
    if request.method == 'POST':
        start_str = request.form.get('start_time')
        end_str = request.form.get('end_time')
        start = datetime.strptime(start_str, '%Y-%m-%dT%H:%M') if start_str else None
        end = datetime.strptime(end_str, '%Y-%m-%dT%H:%M') if end_str else None

        exam = Exam(
            title=request.form.get('title'),
            subject_id=request.form.get('subject_id', type=int),
            section_id=request.form.get('section_id', type=int),
            description=request.form.get('description', ''),
            duration_minutes=request.form.get('duration_minutes', 60, type=int),
            start_time=start,
            end_time=end,
            total_marks=request.form.get('total_marks', 100, type=float),
            created_by=current_user.id
        )
        db.session.add(exam)
        db.session.commit()
        flash('Exam created. Now add questions.', 'success')
        return redirect(url_for('exams.edit_exam', eid=exam.id))

    from app.models import Semester
    subjects = Subject.query.filter_by(college_id=current_user.college_id).all()
    sections = Section.query.join(Semester).filter(Semester.college_id == current_user.college_id).all()
    return render_template('exams/create.html', subjects=subjects, sections=sections)


@bp.route('/<int:eid>/edit', methods=['GET', 'POST'])
@faculty_required
def edit_exam(eid):
    exam = Exam.query.get_or_404(eid)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_question':
            options_raw = request.form.getlist('options[]')
            q = ExamQuestion(
                exam_id=eid,
                question_text=request.form.get('question_text'),
                question_type=request.form.get('question_type', 'mcq'),
                correct_answer=request.form.get('correct_answer', ''),
                marks=request.form.get('marks', 1, type=float),
                order_num=exam.questions.count() + 1
            )
            if options_raw:
                q.options = [o.strip() for o in options_raw if o.strip()]
            db.session.add(q)
            db.session.commit()
            flash('Question added.', 'success')
        elif action == 'publish':
            exam.is_published = True
            db.session.commit()
            flash('Exam published.', 'success')
        elif action == 'unpublish':
            exam.is_published = False
            db.session.commit()
            flash('Exam unpublished.', 'info')
        return redirect(url_for('exams.edit_exam', eid=eid))

    questions = exam.questions.order_by(ExamQuestion.order_num).all()
    return render_template('exams/edit.html', exam=exam, questions=questions)


@bp.route('/question/<int:qid>/delete', methods=['POST'])
@faculty_required
def delete_question(qid):
    q = ExamQuestion.query.get_or_404(qid)
    eid = q.exam_id
    db.session.delete(q)
    db.session.commit()
    flash('Question deleted.', 'info')
    return redirect(url_for('exams.edit_exam', eid=eid))


@bp.route('/<int:eid>/take')
@login_required
def take_exam(eid):
    if current_user.role != 'student':
        flash('Students only.', 'danger')
        return redirect(url_for('exams.index'))
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('exams.index'))
    exam = Exam.query.get_or_404(eid)

    if not exam.is_published:
        flash('This exam is not available yet.', 'warning')
        return redirect(url_for('exams.index'))

    existing = ExamSubmission.query.filter_by(exam_id=eid, student_id=student.id).first()
    if existing and existing.submitted_at:
        flash('You have already submitted this exam.', 'info')
        return redirect(url_for('exams.exam_result', eid=eid))

    if not existing:
        existing = ExamSubmission(exam_id=eid, student_id=student.id)
        db.session.add(existing)
        db.session.commit()

    questions = exam.questions.order_by(ExamQuestion.order_num).all()
    return render_template('exams/take.html', exam=exam, questions=questions,
                           submission=existing, student=student)


@bp.route('/<int:eid>/submit', methods=['POST'])
@login_required
def submit_exam(eid):
    if current_user.role != 'student':
        return redirect(url_for('exams.index'))
    student = Student.query.filter_by(user_id=current_user.id).first()
    if not student:
        flash('Student profile not found.', 'danger')
        return redirect(url_for('exams.index'))
    exam = Exam.query.get_or_404(eid)
    sub = ExamSubmission.query.filter_by(exam_id=eid, student_id=student.id).first()

    if not sub or sub.submitted_at:
        flash('Submission error.', 'danger')
        return redirect(url_for('exams.index'))

    # Collect and grade answers
    answers = {}
    score = 0
    questions = exam.questions.all()
    for q in questions:
        answer = request.form.get(f'q_{q.id}', '').strip()
        answers[str(q.id)] = answer
        if q.question_type in ('mcq', 'true_false'):
            if answer.lower() == q.correct_answer.lower():
                score += q.marks

    sub.answers = answers
    sub.submitted_at = datetime.utcnow()
    sub.score = score
    sub.is_graded = True

    # Also record as a Grade
    active_term = AcademicTerm.query.filter_by(college_id=current_user.college_id, is_active=True).first()
    grade = Grade(
        student_id=student.id,
        subject_id=exam.subject_id,
        term_id=active_term.id if active_term else None,
        exam_name=exam.title,
        score=score,
        max_score=exam.total_marks,
        date=datetime.utcnow().date(),
        created_by=exam.created_by
    )
    db.session.add(grade)
    db.session.commit()
    flash(f'Exam submitted! Score: {score}/{exam.total_marks}', 'success')
    return redirect(url_for('exams.exam_result', eid=eid))


@bp.route('/<int:eid>/result')
@login_required
def exam_result(eid):
    student = Student.query.filter_by(user_id=current_user.id).first()
    exam = Exam.query.get_or_404(eid)
    sub = ExamSubmission.query.filter_by(exam_id=eid, student_id=student.id).first() if student else None
    questions = exam.questions.order_by(ExamQuestion.order_num).all()
    return render_template('exams/result.html', exam=exam, sub=sub, questions=questions, student=student)


@bp.route('/<int:eid>/results')
@faculty_required
def exam_results(eid):
    exam = Exam.query.get_or_404(eid)
    submissions = (ExamSubmission.query.filter_by(exam_id=eid)
                   .filter(ExamSubmission.submitted_at != None).all())
    students_no_sub = (Student.query.filter_by(section_id=exam.section_id)
                       .filter(Student.id.notin_([s.student_id for s in submissions])).all())
    return render_template('exams/results.html', exam=exam, submissions=submissions,
                           students_no_sub=students_no_sub)


@bp.route('/<int:eid>/delete', methods=['POST'])
@faculty_required
def delete_exam(eid):
    exam = Exam.query.get_or_404(eid)
    db.session.delete(exam)
    db.session.commit()
    flash('Exam deleted.', 'info')
    return redirect(url_for('exams.index'))

@bp.route('/run-seed-once-delete-me')
def run_seed():
    import subprocess
    result = subprocess.run(['python', 'seed.py'], capture_output=True, text=True)
    return f"<pre>{result.stdout}\n{result.stderr}</pre>"