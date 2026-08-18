from flask import render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from app.finance import bp
from app.models import FinancialLedger
from app.admin.routes import admin_required

@bp.route('/ledger', methods=['GET', 'POST'])
@admin_required
def ledger():
    if request.method == 'POST':
        transaction_type = request.form.get('transaction_type')
        amount = float(request.form.get('amount', 0))
        party_name = request.form.get('party_name')
        category = request.form.get('category')
        description = request.form.get('description')
        payment_method = request.form.get('payment_method')
        reference_no = request.form.get('reference_no')
        
        new_transaction = FinancialLedger(
            college_id=current_user.college_id,
            transaction_type=transaction_type,
            amount=amount,
            party_name=party_name,
            category=category,
            description=description,
            payment_method=payment_method,
            reference_no=reference_no
        )
        db.session.add(new_transaction)
        db.session.commit()
        flash('Transaction recorded successfully.', 'success')
        return redirect(url_for('finance.ledger'))

    transactions = FinancialLedger.query.filter_by(college_id=current_user.college_id).order_by(FinancialLedger.transaction_date.desc()).all()
    total_income = sum(t.amount for t in transactions if t.transaction_type == 'INCOME')
    total_expense = sum(t.amount for t in transactions if t.transaction_type == 'EXPENSE')
    net_balance = total_income - total_expense
    
    return render_template('finance/ledger.html', 
                           transactions=transactions, 
                           total_income=total_income, 
                           total_expense=total_expense,
                           net_balance=net_balance)

@bp.route('/ledger/delete/<int:id>')
@admin_required
def delete_transaction(id):
    transaction = FinancialLedger.query.get_or_404(id)
    if transaction.college_id != current_user.college_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('finance.ledger'))
        
    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted.', 'success')
    return redirect(url_for('finance.ledger'))
@bp.route('/ledger/report')
@admin_required
def ledger_report():
    transactions = FinancialLedger.query.filter_by(college_id=current_user.college_id).order_by(FinancialLedger.transaction_date.desc()).all()
    total_income = sum(t.amount for t in transactions if t.transaction_type == 'INCOME')
    total_expense = sum(t.amount for t in transactions if t.transaction_type == 'EXPENSE')
    net_balance = total_income - total_expense
    
    html = render_template('finance/ledger_pdf.html', 
                           transactions=transactions, 
                           total_income=total_income, 
                           total_expense=total_expense,
                           net_balance=net_balance,
                           today=datetime.now())
    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=financial_ledger_{datetime.now().strftime("%Y-%m-%d")}.pdf'
        return response
    except Exception as e:
        flash(f'PDF generation failed: {e}.', 'danger')
        return redirect(url_for('finance.ledger'))

