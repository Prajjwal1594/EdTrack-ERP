from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app.accountant import bp
from app.models import FeePayment, FinancialLedger, AssetRecord, Student, User
from app.finance.routes import sync_all_fees_to_ledger
from app import db


def accountant_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('admin', 'accountant', 'superadmin'):
            flash('Accountant access required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated)


@bp.route('/dashboard')
@accountant_required
def dashboard():
    college_id = current_user.college_id

    # Automatically sync fee collections to general ledger income
    sync_all_fees_to_ledger(college_id)

    # 1. Fee Payments Data
    fee_payments = (FeePayment.query.join(Student).join(User, Student.user_id == User.id)
                    .filter(User.college_id == college_id).all())
    
    total_fee_collected = sum(p.amount for p in fee_payments if p.status == 'paid')
    total_fee_pending = sum(p.amount for p in fee_payments if p.status in ('pending', 'overdue'))
    recent_fee_payments = (FeePayment.query.join(Student).join(User, Student.user_id == User.id)
                           .filter(User.college_id == college_id)
                           .order_by(FeePayment.created_at.desc()).limit(5).all())

    # 2. General Ledger & Buy/Sell Data
    ledger_entries = FinancialLedger.query.filter_by(college_id=college_id).all()
    total_ledger_income = sum(l.amount for l in ledger_entries if l.transaction_type == 'INCOME')
    total_ledger_expense = sum(l.amount for l in ledger_entries if l.transaction_type == 'EXPENSE')
    recent_ledger = FinancialLedger.query.filter_by(college_id=college_id).order_by(FinancialLedger.transaction_date.desc()).limit(5).all()

    # 3. Asset & Location Records
    asset_records = AssetRecord.query.filter_by(college_id=college_id).all()
    total_assets_count = sum(a.quantity for a in asset_records)
    total_assets_value = sum(a.total_cost for a in asset_records)
    recent_assets = AssetRecord.query.filter_by(college_id=college_id).order_by(AssetRecord.created_at.desc()).limit(5).all()

    return render_template('accountant/dashboard.html',
                           total_fee_collected=total_fee_collected,
                           total_fee_pending=total_fee_pending,
                           total_ledger_income=total_ledger_income,
                           total_ledger_expense=total_ledger_expense,
                           total_assets_count=total_assets_count,
                           total_assets_value=total_assets_value,
                           recent_fee_payments=recent_fee_payments,
                           recent_ledger=recent_ledger,
                           recent_assets=recent_assets)


@bp.route('/fees')
@accountant_required
def fees():
    """Fee overview - all students with their fee status summary."""
    from app.models import Student, FeeType, AcademicTerm
    college_id = current_user.college_id
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    term_id = request.args.get('term_id', type=int)

    terms = AcademicTerm.query.filter_by(college_id=college_id).order_by(AcademicTerm.start_date.desc()).all()
    fee_types = FeeType.query.filter_by(college_id=college_id, is_active=True).all()
    active_term = next((t for t in terms if t.is_active), terms[0] if terms else None)
    selected_term = next((t for t in terms if t.id == term_id), active_term)

    # Build student fee summary
    student_query = (Student.query.join(User, Student.user_id == User.id)
                     .filter(User.college_id == college_id, Student.is_active == True))
    if search:
        student_query = student_query.filter(
            db.or_(
                User.name.ilike(f'%{search}%'),
                Student.enrollment_number.ilike(f'%{search}%'),
                Student.roll_number.ilike(f'%{search}%')
            )
        )

    students = student_query.order_by(User.name).all()
    student_summaries = []

    for student in students:
        payments = student.fee_payments.all()
        if selected_term:
            payments = student.fee_payments.filter_by(term_id=selected_term.id).all()

        total_due = sum(p.amount for p in payments)
        total_paid = sum(p.amount for p in payments if p.status == 'paid')
        total_pending = sum(p.amount for p in payments if p.status in ('pending', 'overdue'))
        clearance_pct = round((total_paid / total_due * 100) if total_due > 0 else 0)

        summary_status = 'cleared' if total_pending == 0 and total_due > 0 else (
            'partial' if total_paid > 0 else 'pending'
        )

        if status_filter and summary_status != status_filter:
            continue

        student_summaries.append({
            'student': student,
            'total_due': total_due,
            'total_paid': total_paid,
            'total_pending': total_pending,
            'clearance_pct': clearance_pct,
            'status': summary_status,
            'payment_count': len(payments)
        })

    # Overall stats
    overall_collected = sum(s['total_paid'] for s in student_summaries)
    overall_pending = sum(s['total_pending'] for s in student_summaries)
    cleared_count = sum(1 for s in student_summaries if s['status'] == 'cleared')

    return render_template('accountant/fees.html',
                           student_summaries=student_summaries,
                           terms=terms,
                           fee_types=fee_types,
                           selected_term=selected_term,
                           overall_collected=overall_collected,
                           overall_pending=overall_pending,
                           cleared_count=cleared_count,
                           total_students=len(student_summaries),
                           search=search,
                           status_filter=status_filter)


@bp.route('/payments')
@accountant_required
def payments():
    """All fee payment transactions with filtering and search."""
    from app.models import FeeType, AcademicTerm
    college_id = current_user.college_id
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()
    method_filter = request.args.get('method', '').strip()
    page = request.args.get('page', 1, type=int)

    query = (FeePayment.query
             .join(Student, FeePayment.student_id == Student.id)
             .join(User, Student.user_id == User.id)
             .filter(User.college_id == college_id))

    if search:
        query = query.filter(
            db.or_(
                User.name.ilike(f'%{search}%'),
                Student.enrollment_number.ilike(f'%{search}%'),
                FeePayment.transaction_ref.ilike(f'%{search}%')
            )
        )
    if status_filter:
        query = query.filter(FeePayment.status == status_filter)
    if method_filter:
        query = query.filter(FeePayment.payment_method == method_filter)

    total_count = query.count()
    payments_list = query.order_by(FeePayment.created_at.desc()).paginate(page=page, per_page=25, error_out=False)

    # Summary stats (unfiltered)
    all_payments = (FeePayment.query
                    .join(Student).join(User, Student.user_id == User.id)
                    .filter(User.college_id == college_id).all())
    total_collected = sum(p.amount for p in all_payments if p.status == 'paid')
    total_pending = sum(p.amount for p in all_payments if p.status in ('pending', 'overdue'))
    total_overdue = sum(p.amount for p in all_payments if p.status == 'overdue')

    fee_types = FeeType.query.filter_by(college_id=college_id).all()
    methods = ['cash', 'online', 'bank_transfer', 'cheque', 'dd']

    return render_template('accountant/payments.html',
                           payments=payments_list,
                           total_count=total_count,
                           total_collected=total_collected,
                           total_pending=total_pending,
                           total_overdue=total_overdue,
                           fee_types=fee_types,
                           methods=methods,
                           search=search,
                           status_filter=status_filter,
                           method_filter=method_filter)
