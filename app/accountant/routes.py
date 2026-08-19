from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app.accountant import bp
from app.models import FeePayment, FinancialLedger, AssetRecord, Student, User
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
