from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.models import User
from app import db
from datetime import datetime


@bp.route('/')
def index():
    return redirect(url_for('auth.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password) and user.is_active:
            login_user(user, remember=remember)
            try:
                user.last_login = datetime.utcnow()
                db.session.commit()
            except Exception:
                db.session.rollback()
            next_page = request.args.get('next')
            if next_page:
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
    elif role == 'parent':
        return redirect(url_for('parent.dashboard'))
    return redirect(url_for('auth.login'))


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
