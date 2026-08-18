from flask import render_template, redirect, url_for, flash, request, make_response, abort
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from app import db
from app.hr import bp
from app.models import StaffProfile, StaffAttendance, PayrollTransaction, User

def hr_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or (current_user.role != 'hr' and current_user.role != 'superadmin'):
            flash('HR access required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated)

@bp.route('/dashboard')
@hr_required
def dashboard():
    staff_count = User.query.filter_by(college_id=current_user.college_id, role='faculty').count()
    pending_payroll = PayrollTransaction.query.filter_by(college_id=current_user.college_id, status='Pending').count()
    return render_template('hr/dashboard.html', staff_count=staff_count, pending_payroll=pending_payroll)

@bp.route('/directory', methods=['GET', 'POST'])
@hr_required
def directory():
    if request.method == 'POST':
        staff_id = request.form.get('staff_id')
        staff = StaffProfile.query.get_or_404(staff_id)
        if staff.college_id != current_user.college_id:
            abort(403)
        staff.base_salary = float(request.form.get('base_salary', 0))
        staff.bank_account = request.form.get('bank_account')
        staff.pan_number = request.form.get('pan_number')
        db.session.commit()
        flash(f'Profile updated for {staff.user.name}', 'success')
        return redirect(url_for('hr.directory'))

    faculty = User.query.filter_by(college_id=current_user.college_id, role='faculty').all()
    # Ensure StaffProfile exists for all faculty
    for t in faculty:
        if not t.staff_profile:
            profile = StaffProfile(user_id=t.id, college_id=t.college_id)
            db.session.add(profile)
    db.session.commit()
    
    staff = StaffProfile.query.join(User).filter(User.college_id == current_user.college_id, User.role == 'faculty').all()
    return render_template('hr/directory.html', staff=staff)

@bp.route('/attendance', methods=['GET', 'POST'])
@hr_required
def attendance():
    from datetime import date
    selected_date = request.args.get('date', date.today().isoformat())
    selected_date_obj = date.fromisoformat(selected_date)
    
    if request.method == 'POST':
        for key, value in request.form.items():
            if key.startswith('status_'):
                staff_id = key.split('_')[1]
                # Verify this staff member is a faculty
                staff_check = StaffProfile.query.join(User).filter(StaffProfile.id == staff_id, User.role == 'faculty').first()
                if not staff_check: continue

                # Check if record exists for this date
                existing = StaffAttendance.query.filter_by(staff_id=staff_id, date=selected_date_obj).first()
                if existing:
                    existing.status = value
                else:
                    new_att = StaffAttendance(
                        staff_id=staff_id, college_id=current_user.college_id,
                        date=selected_date_obj, status=value
                    )
                    db.session.add(new_att)
        db.session.commit()
        flash('Attendance marked successfully.', 'success')
        return redirect(url_for('hr.attendance', date=selected_date))

    # Ensure StaffProfile exists for all faculty before listing
    faculty = User.query.filter_by(college_id=current_user.college_id, role='faculty').all()
    for t in faculty:
        if not t.staff_profile:
            profile = StaffProfile(user_id=t.id, college_id=t.college_id)
            db.session.add(profile)
    db.session.commit()

    staff = StaffProfile.query.join(User).filter(User.college_id == current_user.college_id, User.role == 'faculty').all()
    attendance_records = {a.staff_id: a.status for a in StaffAttendance.query.filter_by(college_id=current_user.college_id, date=selected_date_obj).all()}
    
    return render_template('hr/attendance.html', staff=staff, attendance_records=attendance_records, selected_date=selected_date)

@bp.route('/payroll', methods=['GET', 'POST'])
@hr_required
def payroll():
    from datetime import date
    if request.method == 'POST' and request.form.get('action') == 'generate':
        month = int(request.form.get('month'))
        year = int(request.form.get('year'))
        
        # Check if already generated
        existing = PayrollTransaction.query.filter_by(college_id=current_user.college_id, month=month, year=year).first()
        if existing:
            flash(f'Payroll for {month}/{year} has already been generated.', 'warning')
            return redirect(url_for('hr.payroll'))
            
        staff_list = StaffProfile.query.join(User).filter(User.college_id == current_user.college_id, User.role == 'faculty').all()
        for staff in staff_list:
            if not staff.base_salary: continue
            
            # Phase 4 Refined: Deduction logic based on attendance
            total_days = 30 # Simplified month length
            absent_count = StaffAttendance.query.filter_by(
                staff_id=staff.id, 
                status='Absent'
            ).filter(db.extract('month', StaffAttendance.date) == month, 
                     db.extract('year', StaffAttendance.date) == year).count()
            
            per_day = staff.base_salary / total_days
            deductions = round(absent_count * per_day, 2)
            net_pay = staff.base_salary - deductions
            
            new_payroll = PayrollTransaction(
                staff_id=staff.id, college_id=current_user.college_id,
                month=month, year=year, basic_pay=staff.base_salary,
                deductions=deductions, net_pay=net_pay, status='Pending'
            )
            db.session.add(new_payroll)
            
        db.session.commit()
        flash(f'Payroll generated for {month}/{year}.', 'success')
        return redirect(url_for('hr.payroll'))

    transactions = PayrollTransaction.query.filter_by(college_id=current_user.college_id).order_by(PayrollTransaction.year.desc(), PayrollTransaction.month.desc()).all()
    return render_template('hr/payroll.html', transactions=transactions)

@bp.route('/payroll/mark-paid/<int:tid>', methods=['POST'])
@hr_required
def mark_paid(tid):
    transaction = PayrollTransaction.query.get_or_404(tid)
    if transaction.college_id != current_user.college_id:
        abort(403)
    
    transaction.status = 'Paid'
    transaction.paid_at = datetime.utcnow()
    db.session.commit()
    flash(f'Payroll marked as Paid for {transaction.staff.user.name}.', 'success')
    return redirect(url_for('hr.payroll'))

@bp.route('/payroll/slip/<int:tid>')
@hr_required
def salary_slip(tid):
    transaction = PayrollTransaction.query.get_or_404(tid)
    if transaction.college_id != current_user.college_id:
        abort(403)
    
    html = render_template('hr/salary_slip_pdf.html', t=transaction)
    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=salary_slip_{transaction.staff.user.name}_{transaction.month}_{transaction.year}.pdf'
        return response
    except Exception as e:
        flash(f'PDF generation failed: {e}. Showing HTML version.', 'warning')
        return html
