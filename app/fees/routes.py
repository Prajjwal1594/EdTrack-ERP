from flask import render_template, redirect, url_for, flash, request, jsonify, make_response, current_app
from flask_login import login_required, current_user
import razorpay
from functools import wraps
from app.fees import bp
from app.models import FeePayment, FeeType, Student, AcademicTerm, User, ParentStudentLink
from app import db
from datetime import datetime, date


def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('admin', 'faculty', 'accountant', 'superadmin'):
            flash('Staff/Accountant access required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated)


@bp.route('/')
@staff_required
def index():
    term_id = request.args.get('term_id', type=int)
    status_filter = request.args.get('status', '')
    terms = AcademicTerm.query.filter_by(college_id=current_user.college_id).order_by(AcademicTerm.start_date.desc()).all()
    active_term = AcademicTerm.query.filter_by(college_id=current_user.college_id, is_active=True).first()

    query = (FeePayment.query.join(Student).join(User, Student.user_id == User.id)
             .filter(User.college_id == current_user.college_id))
    if term_id:
        query = query.filter(FeePayment.term_id == term_id)
    if status_filter:
        query = query.filter(FeePayment.status == status_filter)

    payments = query.order_by(FeePayment.created_at.desc()).limit(100).all()

    # Summary stats
    total_due = sum(p.amount for p in payments if p.status in ('pending', 'overdue', 'paid'))
    total_paid = sum(p.amount for p in payments if p.status == 'paid')
    total_pending = sum(p.amount for p in payments if p.status == 'pending')

    students = Student.query.join(User).filter(User.college_id == current_user.college_id).all()
    fee_types = FeeType.query.filter_by(college_id=current_user.college_id, is_active=True).all()

    return render_template('fees/index.html', payments=payments,
                           terms=terms, active_term=active_term,
                           selected_term_id=term_id, status_filter=status_filter,
                           total_due=total_due, total_paid=total_paid, total_pending=total_pending,
                           students=students, fee_types=fee_types)


@bp.route('/add', methods=['POST'])
@staff_required
def add_payment():
    due_str = request.form.get('due_date')
    payment = FeePayment(
        student_id=request.form.get('student_id', type=int),
        fee_type_id=request.form.get('fee_type_id', type=int),
        term_id=request.form.get('term_id', type=int) or None,
        amount=request.form.get('amount', type=float),
        due_date=datetime.strptime(due_str, '%Y-%m-%d').date() if due_str else None,
        status='pending',
        notes=request.form.get('notes', ''),
        recorded_by=current_user.id
    )
    db.session.add(payment)
    db.session.commit()
    flash('Fee record added.', 'success')
    return redirect(url_for('fees.index'))


@bp.route('/<int:pid>/mark-paid', methods=['POST'])
@staff_required
def mark_paid(pid):
    payment = FeePayment.query.get_or_404(pid)
    payment.status = 'paid'
    payment.paid_at = datetime.utcnow()
    payment.payment_method = request.form.get('payment_method', 'cash')
    payment.transaction_ref = request.form.get('transaction_ref', '')
    db.session.commit()
    flash('Payment recorded.', 'success')
    return redirect(request.referrer or url_for('fees.index'))


@bp.route('/<int:pid>/waive', methods=['POST'])
@staff_required
def waive_payment(pid):
    payment = FeePayment.query.get_or_404(pid)
    payment.status = 'waived'
    payment.notes = request.form.get('reason', '') + ' [WAIVED]'
    db.session.commit()
    flash('Fee waived.', 'info')
    return redirect(request.referrer or url_for('fees.index'))


@bp.route('/<int:pid>/delete', methods=['POST'])
@staff_required
def delete_payment(pid):
    payment = FeePayment.query.get_or_404(pid)
    db.session.delete(payment)
    db.session.commit()
    flash('Record deleted.', 'info')
    return redirect(url_for('fees.index'))


@bp.route('/student/<int:student_id>')
@login_required
def student_fees(student_id):
    # Check access
    if current_user.role == 'parent':
        link = ParentStudentLink.query.filter_by(parent_id=current_user.id, student_id=student_id).first()
        if not link:
            flash('Access denied.', 'danger')
            return redirect(url_for('parent.dashboard'))
    elif current_user.role == 'student':
        student = Student.query.filter_by(user_id=current_user.id, id=student_id).first()
        if not student:
            flash('Access denied.', 'danger')
            return redirect(url_for('student.dashboard'))
    elif current_user.role not in ('admin', 'faculty', 'accountant', 'superadmin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('auth.dashboard'))

    student = Student.query.get_or_404(student_id)
    payments = FeePayment.query.filter_by(student_id=student_id).order_by(FeePayment.created_at.desc()).all()
    total_paid = sum(p.amount for p in payments if p.status == 'paid')
    total_pending = sum(p.amount for p in payments if p.status == 'pending')

    return render_template('fees/student_fees.html', student=student, payments=payments,
                           total_paid=total_paid, total_pending=total_pending)


@bp.route('/<int:pid>/receipt')
@login_required
def download_receipt(pid):
    payment = FeePayment.query.get_or_404(pid)
    
    # Check access permission
    if current_user.role == 'parent':
        link = ParentStudentLink.query.filter_by(parent_id=current_user.id, student_id=payment.student_id).first()
        if not link:
            flash('Access denied.', 'danger')
            return redirect(url_for('parent.dashboard'))
    elif current_user.role == 'student':
        if payment.student.user_id != current_user.id:
            flash('Access denied.', 'danger')
            return redirect(url_for('student.dashboard'))
            
    if payment.status != 'paid':
        flash('Receipts are only available for paid fees.', 'warning')
        return redirect(request.referrer or url_for('auth.dashboard'))

    html = render_template('fees/receipt_pdf.html', payment=payment, today=date.today())
    
    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=receipt_{payment.id}_{payment.student.enrollment_number}.pdf'
        return response
    except Exception as e:
        flash(f'PDF generation failed: {e}. Showing HTML version instead.', 'warning')
        return html


# ─── Digital Wallet ──────────────────────────────────────────────────────────
@bp.route('/wallet/topup', methods=['POST'])
@login_required
def wallet_topup():
    if current_user.role != 'parent':
        return jsonify({'error': 'Only parents can top-up.'}), 403
    
    amount = request.form.get('amount', type=float)
    if not amount or amount <= 0:
        return jsonify({'error': 'Invalid amount.'}), 400
    
    try:
        client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], 
                                       current_app.config['RAZORPAY_KEY_SECRET']))
        
        # Razorpay expects amount in paise (1 INR = 100 paise)
        order_data = {
            'amount': int(amount * 100),
            'currency': 'INR',
            'payment_capture': '1'
        }
        razorpay_order = client.order.create(data=order_data)
        
        return jsonify({
            'order_id': razorpay_order['id'],
            'amount': razorpay_order['amount'],
            'currency': razorpay_order['currency'],
            'key_id': current_app.config['RAZORPAY_KEY_ID'],
            'user_name': current_user.name,
            'user_email': current_user.email,
            'user_phone': current_user.phone or ''
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/wallet/verify', methods=['POST'])
@login_required
def wallet_verify():
    data = request.json
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_signature = data.get('razorpay_signature')
    
    client = razorpay.Client(auth=(current_app.config['RAZORPAY_KEY_ID'], 
                                   current_app.config['RAZORPAY_KEY_SECRET']))
    
    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    
    try:
        # Verify the cryptographic signature
        client.utility.verify_payment_signature(params_dict)
        
        # Fetch the order details to get the actual amount paid
        order_info = client.order.fetch(razorpay_order_id)
        credit_amount = order_info['amount'] / 100.0
        
        # Update user balance
        current_user.wallet_balance += credit_amount
        db.session.commit()
        
        # Flash message for the frontend to handle or next page
        flash(f'Payment Successful! ${credit_amount:.2f} added to your wallet.', 'success')
        return jsonify({'status': 'success', 'new_balance': current_user.wallet_balance})
    except Exception as e:
        return jsonify({'status': 'failure', 'error': str(e)}), 400


@bp.route('/wallet/deduct', methods=['POST'])
@staff_required
def wallet_deduct():
    student_id = request.form.get('student_id', type=int)
    amount = request.form.get('amount', type=float)
    reason = request.form.get('reason', 'Micro-fee Deduction')
    
    student = Student.query.get_or_404(student_id)
    # Find a linked parent to deduct from
    link = student.parent_links.first()
    if not link:
        flash('Student has no linked parent to deduct from.', 'danger')
        return redirect(request.referrer)
        
    parent = link.parent
    if parent.wallet_balance is None:
        parent.wallet_balance = 0.0
        
    if parent.wallet_balance < amount:
        flash(f'Insufficient wallet balance for {parent.name}. Requires ${amount:.2f}.', 'danger')
        return redirect(request.referrer)
        
    # Deduct funds
    parent.wallet_balance -= amount
    
    # Create an invisible "paid" fee record for accounting
    payment = FeePayment(
        student_id=student.id,
        amount=amount,
        status='paid',
        payment_method='digital_wallet',
        notes=f"Wallet Deduction: {reason}",
        paid_at=datetime.utcnow(),
        recorded_by=current_user.id
    )
    db.session.add(payment)
    db.session.commit()
    
    # Automatically email the instantaneous receipt
    from app.email import send_email
    send_email('Digital Wallet Deduction Receipt',
               [parent.email],
               f"Dear {parent.name},\n\n${amount:.2f} has been smoothly deducted from your Digital Wallet for: '{reason}'.\nYour new wallet balance is ${parent.wallet_balance:.2f}.\n\nThank you for using the cashless system,\nEl'Wood Accounts")
               
    flash(f"Successfully deducted ${amount:.2f} from {parent.name}'s wallet.", 'success')
    return redirect(request.referrer or url_for('fees.index'))

