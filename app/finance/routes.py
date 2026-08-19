from flask import render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from datetime import datetime
from app import db
from functools import wraps
from app.finance import bp
from app.models import FinancialLedger, AssetRecord

def finance_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('admin', 'accountant', 'superadmin'):
            flash('Finance / Accountant access required.', 'danger')
            return redirect(url_for('auth.dashboard'))
        return f(*args, **kwargs)
    return login_required(decorated)

@bp.route('/assets', methods=['GET', 'POST'])
@finance_required
def assets():
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category = request.form.get('category', 'Furniture & Fixtures')
        quantity = int(request.form.get('quantity', 1))
        unit_cost = float(request.form.get('unit_cost', 0))
        total_cost = unit_cost * quantity
        vendor_name = request.form.get('vendor_name', '').strip()
        invoice_no = request.form.get('invoice_no', '').strip()
        
        purchase_date_str = request.form.get('purchase_date')
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else datetime.utcnow().date()
        
        warranty_str = request.form.get('warranty_expiry')
        warranty_expiry = datetime.strptime(warranty_str, '%Y-%m-%d').date() if warranty_str else None
        
        block_name = request.form.get('block_name', '').strip()
        floor_level = request.form.get('floor_level', '').strip()
        corridor_wing = request.form.get('corridor_wing', '').strip()
        room_number = request.form.get('room_number', '').strip()
        department = request.form.get('department', '').strip()
        status = request.form.get('status', 'In Use')
        notes = request.form.get('notes', '').strip()

        new_asset = AssetRecord(
            college_id=current_user.college_id,
            item_name=item_name,
            category=category,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            purchase_date=purchase_date,
            vendor_name=vendor_name,
            invoice_no=invoice_no,
            warranty_expiry=warranty_expiry,
            block_name=block_name,
            floor_level=floor_level,
            corridor_wing=corridor_wing,
            room_number=room_number,
            department=department,
            status=status,
            notes=notes
        )
        db.session.add(new_asset)

        # Optional: Auto-create ledger expense entry if requested
        if request.form.get('auto_ledger') == '1':
            ledger_entry = FinancialLedger(
                college_id=current_user.college_id,
                transaction_type='EXPENSE',
                amount=total_cost,
                party_name=vendor_name or party_name or 'Asset Vendor',
                category='Asset & Inventory Purchase',
                description=f"Purchased {quantity}x {item_name} for {block_name} ({room_number})",
                payment_method='Bank Transfer',
                reference_no=invoice_no
            )
            db.session.add(ledger_entry)

        db.session.commit()
        flash(f'Asset "{item_name}" recorded & location assigned to {block_name} - {room_number} successfully!', 'success')
        return redirect(url_for('finance.assets'))

    # Search and Filtering
    query = AssetRecord.query.filter_by(college_id=current_user.college_id)
    search = request.args.get('search', '').strip()
    block_filter = request.args.get('block', '').strip()
    category_filter = request.args.get('category', '').strip()
    status_filter = request.args.get('status', '').strip()

    if search:
        query = query.filter((AssetRecord.item_name.ilike(f'%{search}%')) |
                             (AssetRecord.room_number.ilike(f'%{search}%')) |
                             (AssetRecord.vendor_name.ilike(f'%{search}%')) |
                             (AssetRecord.invoice_no.ilike(f'%{search}%')))
    if block_filter:
        query = query.filter_by(block_name=block_filter)
    if category_filter:
        query = query.filter_by(category=category_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)

    assets_list = query.order_by(AssetRecord.created_at.desc()).all()

    # Calculate Summary Stats
    all_assets = AssetRecord.query.filter_by(college_id=current_user.college_id).all()
    total_items = sum(a.quantity for a in all_assets)
    total_investment = sum(a.total_cost for a in all_assets)
    in_use_count = sum(a.quantity for a in all_assets if a.status == 'In Use')
    in_storage_count = sum(a.quantity for a in all_assets if a.status == 'In Storage')
    under_repair_count = sum(a.quantity for a in all_assets if a.status == 'Under Repair')

    # Unique Blocks & Categories for Filters
    unique_blocks = sorted(list(set(a.block_name for a in all_assets if a.block_name)))
    unique_categories = sorted(list(set(a.category for a in all_assets if a.category)))

    return render_template('finance/assets.html',
                           assets=assets_list,
                           total_items=total_items,
                           total_investment=total_investment,
                           in_use_count=in_use_count,
                           in_storage_count=in_storage_count,
                           under_repair_count=under_repair_count,
                           unique_blocks=unique_blocks,
                           unique_categories=unique_categories)


@bp.route('/assets/add', methods=['GET', 'POST'])
@finance_required
def add_asset():
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category = request.form.get('category', 'Furniture & Fixtures')
        quantity = int(request.form.get('quantity', 1))
        unit_cost = float(request.form.get('unit_cost', 0))
        total_cost = unit_cost * quantity
        vendor_name = request.form.get('vendor_name', '').strip()
        invoice_no = request.form.get('invoice_no', '').strip()
        
        purchase_date_str = request.form.get('purchase_date')
        purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date() if purchase_date_str else datetime.utcnow().date()
        
        warranty_str = request.form.get('warranty_expiry')
        warranty_expiry = datetime.strptime(warranty_str, '%Y-%m-%d').date() if warranty_str else None
        
        block_name = request.form.get('block_name', '').strip()
        floor_level = request.form.get('floor_level', '').strip()
        corridor_wing = request.form.get('corridor_wing', '').strip()
        room_number = request.form.get('room_number', '').strip()
        department = request.form.get('department', '').strip()
        status = request.form.get('status', 'In Use')
        notes = request.form.get('notes', '').strip()

        new_asset = AssetRecord(
            college_id=current_user.college_id,
            item_name=item_name,
            category=category,
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=total_cost,
            purchase_date=purchase_date,
            vendor_name=vendor_name,
            invoice_no=invoice_no,
            warranty_expiry=warranty_expiry,
            block_name=block_name,
            floor_level=floor_level,
            corridor_wing=corridor_wing,
            room_number=room_number,
            department=department,
            status=status,
            notes=notes
        )
        db.session.add(new_asset)

        if request.form.get('auto_ledger') == '1':
            ledger_entry = FinancialLedger(
                college_id=current_user.college_id,
                transaction_type='EXPENSE',
                amount=total_cost,
                party_name=vendor_name or 'Asset Vendor',
                category='Asset & Inventory Purchase',
                description=f"Purchased {quantity}x {item_name} for {block_name} ({room_number})",
                payment_method='Bank Transfer',
                reference_no=invoice_no
            )
            db.session.add(ledger_entry)

        db.session.commit()
        flash(f'Asset "{item_name}" recorded & assigned to {block_name} - {room_number} successfully!', 'success')
        return redirect(url_for('finance.assets'))

    return render_template('finance/add_asset.html')


@bp.route('/assets/edit/<int:id>', methods=['GET', 'POST'])
@finance_required
def edit_asset(id):
    asset = AssetRecord.query.get_or_404(id)
    if asset.college_id != current_user.college_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('finance.assets'))

    if request.method == 'POST':
        asset.item_name = request.form.get('item_name', asset.item_name).strip()
        asset.category = request.form.get('category', asset.category)
        asset.quantity = int(request.form.get('quantity', asset.quantity))
        asset.unit_cost = float(request.form.get('unit_cost', asset.unit_cost))
        asset.total_cost = asset.unit_cost * asset.quantity
        asset.vendor_name = request.form.get('vendor_name', asset.vendor_name).strip()
        asset.invoice_no = request.form.get('invoice_no', asset.invoice_no).strip()

        purchase_date_str = request.form.get('purchase_date')
        if purchase_date_str:
            asset.purchase_date = datetime.strptime(purchase_date_str, '%Y-%m-%d').date()

        warranty_str = request.form.get('warranty_expiry')
        if warranty_str:
            asset.warranty_expiry = datetime.strptime(warranty_str, '%Y-%m-%d').date()

        asset.block_name = request.form.get('block_name', asset.block_name).strip()
        asset.floor_level = request.form.get('floor_level', asset.floor_level).strip()
        asset.corridor_wing = request.form.get('corridor_wing', asset.corridor_wing).strip()
        asset.room_number = request.form.get('room_number', asset.room_number).strip()
        asset.department = request.form.get('department', asset.department).strip()
        asset.status = request.form.get('status', asset.status)
        asset.notes = request.form.get('notes', asset.notes).strip()

        db.session.commit()
        flash(f'Asset "{asset.item_name}" location & record updated successfully.', 'success')
        return redirect(url_for('finance.assets'))

    return render_template('finance/edit_asset.html', asset=asset)


@bp.route('/assets/delete/<int:id>', methods=['POST', 'GET'])
@finance_required
def delete_asset(id):
    asset = AssetRecord.query.get_or_404(id)
    if asset.college_id != current_user.college_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('finance.assets'))

    db.session.delete(asset)
    db.session.commit()
    flash('Asset record deleted.', 'success')
    return redirect(url_for('finance.assets'))

@bp.route('/ledger', methods=['GET', 'POST'])
@finance_required
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
@finance_required
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
@finance_required
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
        flash(f'PDF generation note: {e}. Showing HTML version instead.', 'warning')
        return html

