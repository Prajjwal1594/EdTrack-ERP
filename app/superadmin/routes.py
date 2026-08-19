from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app.superadmin import bp
from app.models import College, User, Semester, Section, Subject, AcademicTerm, Student, Grade, Attendance
from app import db
from datetime import datetime
from sqlalchemy import func


# ── Guard decorator ──────────────────────────────────────────────────────────

def superadmin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'superadmin':
            flash('Super-admin access required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated)


# ── Dashboard ────────────────────────────────────────────────────────────────

@bp.route('/dashboard')
@superadmin_required
def dashboard():
    colleges = College.query.order_by(College.created_at.desc()).all()

    # Cross-college aggregate stats
    totals = {
        'colleges': len(colleges),
        'students': User.query.filter_by(role='student').count(),
        'faculty': User.query.filter_by(role='faculty').count(),
        'admins':   User.query.filter_by(role='admin').count(),
        'accountants': User.query.filter_by(role='accountant').count(),
        'hr': User.query.filter_by(role='hr').count(),
    }

    # Per-college summary cards
    college_summaries = []
    for s in colleges:
        college_summaries.append({
            'college': s,
            'students': User.query.filter_by(college_id=s.id, role='student').count(),
            'faculty': User.query.filter_by(college_id=s.id, role='faculty').count(),
            'semesters':  Semester.query.filter_by(college_id=s.id).count(),
            'active_term': AcademicTerm.query.filter_by(college_id=s.id, is_active=True).first(),
        })

    # Recently registered users across all colleges
    recent_users = (User.query
                    .filter(User.role != 'superadmin')
                    .order_by(User.created_at.desc())
                    .limit(10).all())

    return render_template('superadmin/dashboard.html',
                           totals=totals,
                           college_summaries=college_summaries,
                           recent_users=recent_users)


# ── College list ───────────────────────────────────────────────────────────────

@bp.route('/colleges')
@superadmin_required
def colleges():
    all_colleges = College.query.order_by(College.name).all()
    summaries = []
    for s in all_colleges:
        summaries.append({
            'college': s,
            'users':    User.query.filter_by(college_id=s.id).filter(User.role != 'superadmin').count(),
            'students': User.query.filter_by(college_id=s.id, role='student').count(),
            'faculty': User.query.filter_by(college_id=s.id, role='faculty').count(),
        })
    return render_template('superadmin/colleges.html', summaries=summaries)


# ── Create college ─────────────────────────────────────────────────────────────

@bp.route('/colleges/new', methods=['GET', 'POST'])
@superadmin_required
def new_college():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        if College.query.filter_by(code=code).first():
            flash(f'College code "{code}" is already in use.', 'danger')
            return redirect(url_for('superadmin.new_college'))

        college = College(
            name    = request.form.get('name', '').strip(),
            code    = code,
            address = request.form.get('address', '').strip(),
            phone   = request.form.get('phone', '').strip(),
            email   = request.form.get('email', '').strip().lower(),
        )
        db.session.add(college)
        db.session.flush()

        # Optionally create the first admin user for this college
        admin_email = request.form.get('admin_email', '').strip().lower()
        admin_name  = request.form.get('admin_name', '').strip()
        admin_pwd   = request.form.get('admin_password', 'ChangeMe123!')
        if admin_email and admin_name:
            if User.query.filter_by(email=admin_email).first():
                flash(f'Admin email "{admin_email}" already exists — college created without an admin user.', 'warning')
            else:
                admin_user = User(
                    name      = admin_name,
                    email     = admin_email,
                    role      = 'admin',
                    college_id = college.id,
                )
                admin_user.set_password(admin_pwd)
                db.session.add(admin_user)

        db.session.commit()
        flash(f'College "{college.name}" created successfully.', 'success')
        return redirect(url_for('superadmin.college_detail', college_id=college.id))

    return render_template('superadmin/college_form.html', college=None, action='create')


# ── College detail ──────────────────────────────────────────────────────────────

@bp.route('/colleges/<int:college_id>')
@superadmin_required
def college_detail(college_id):
    college = College.query.get_or_404(college_id)

    stats = {
        'students': User.query.filter_by(college_id=college.id, role='student').count(),
        'faculty': User.query.filter_by(college_id=college.id, role='faculty').count(),
        'parents':  User.query.filter_by(college_id=college.id, role='parent').count(),
        'admins':   User.query.filter_by(college_id=college.id, role='admin').count(),
        'accountants': User.query.filter_by(college_id=college.id, role='accountant').count(),
        'hr': User.query.filter_by(college_id=college.id, role='hr').count(),
        'semesters':  Semester.query.filter_by(college_id=college.id).count(),
        'subjects': Subject.query.filter_by(college_id=college.id).count(),
    }

    terms   = AcademicTerm.query.filter_by(college_id=college.id).order_by(AcademicTerm.start_date.desc()).all()
    admins  = User.query.filter_by(college_id=college.id, role='admin').all()
    recent  = (User.query.filter_by(college_id=college.id)
               .filter(User.role != 'superadmin')
               .order_by(User.created_at.desc()).limit(8).all())

    # Grade distribution for this college
    grade_dist = (db.session.query(Grade.score)
                  .join(Student, Grade.student_id == Student.id)
                  .join(User, Student.user_id == User.id)
                  .filter(User.college_id == college.id)
                  .all())
    buckets = {'A+ (90-100)': 0, 'A (80-89)': 0, 'B+ (70-79)': 0,
               'B (60-69)': 0, 'C (50-59)': 0, 'Below 50': 0}
    for (score,) in grade_dist:
        if score >= 90:   buckets['A+ (90-100)'] += 1
        elif score >= 80: buckets['A (80-89)'] += 1
        elif score >= 70: buckets['B+ (70-79)'] += 1
        elif score >= 60: buckets['B (60-69)'] += 1
        elif score >= 50: buckets['C (50-59)'] += 1
        else:             buckets['Below 50'] += 1

    return render_template('superadmin/college_detail.html',
                           college=college, stats=stats, terms=terms,
                           admins=admins, recent_users=recent,
                           grade_dist=buckets)


# ── Edit college ────────────────────────────────────────────────────────────────

@bp.route('/colleges/<int:college_id>/edit', methods=['GET', 'POST'])
@superadmin_required
def edit_college(college_id):
    college = College.query.get_or_404(college_id)
    if request.method == 'POST':
        new_code = request.form.get('code', '').strip().upper()
        existing = College.query.filter_by(code=new_code).first()
        if existing and existing.id != college.id:
            flash(f'College code "{new_code}" is already taken.', 'danger')
            return redirect(url_for('superadmin.edit_college', college_id=college.id))

        college.name    = request.form.get('name', college.name).strip()
        college.code    = new_code
        college.address = request.form.get('address', college.address).strip()
        college.phone   = request.form.get('phone', college.phone).strip()
        college.email   = request.form.get('email', college.email).strip().lower()
        db.session.commit()
        flash('College updated.', 'success')
        return redirect(url_for('superadmin.college_detail', college_id=college.id))

    return render_template('superadmin/college_form.html', college=college, action='edit')


# ── Add admin user to a college ─────────────────────────────────────────────────

@bp.route('/colleges/<int:college_id>/add-admin', methods=['POST'])
@superadmin_required
def add_college_admin(college_id):
    college = College.query.get_or_404(college_id)
    email  = request.form.get('email', '').strip().lower()
    name   = request.form.get('name', '').strip()
    pwd    = request.form.get('password', 'ChangeMe123!')
    role   = request.form.get('role', 'admin')

    if not email or not name:
        flash('Name and email are required.', 'danger')
        return redirect(url_for('superadmin.college_detail', college_id=college_id))

    if User.query.filter_by(email=email).first():
        flash(f'Email "{email}" is already registered.', 'danger')
        return redirect(url_for('superadmin.college_detail', college_id=college_id))

    user = User(name=name, email=email, role=role, college_id=college.id)
    user.set_password(pwd)
    db.session.add(user)
    db.session.commit()
    flash(f'{role.title()} user "{name}" added to {college.name}.', 'success')
    return redirect(url_for('superadmin.college_detail', college_id=college_id))


# ── Delete / deactivate college ─────────────────────────────────────────────────

@bp.route('/colleges/<int:college_id>/delete', methods=['POST'])
@superadmin_required
def delete_college(college_id):
    college = College.query.get_or_404(college_id)
    # Safety: only allow deletion if college has no users
    user_count = User.query.filter_by(college_id=college.id).count()
    if user_count > 0:
        flash(f'Cannot delete "{college.name}" — it still has {user_count} user(s). '
              'Remove all users first or deactivate instead.', 'danger')
        return redirect(url_for('superadmin.college_detail', college_id=college_id))
    db.session.delete(college)
    db.session.commit()
    flash(f'College "{college.name}" deleted.', 'success')
    return redirect(url_for('superadmin.colleges'))


# ── Cross-college analytics (JSON for charts) ───────────────────────────────────

@bp.route('/api/stats')
@superadmin_required
def api_stats():
    colleges = College.query.order_by(College.name).all()
    data = []
    for s in colleges:
        data.append({
            'name':     s.name,
            'students': User.query.filter_by(college_id=s.id, role='student').count(),
            'faculty': User.query.filter_by(college_id=s.id, role='faculty').count(),
        })
    return jsonify(data)
