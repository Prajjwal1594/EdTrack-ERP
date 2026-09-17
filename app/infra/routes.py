from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.infra import bp
from app.models import LibraryBook, BookIssue, TransportRoute, TransportAllocation, HostelRoom, HostelAllocation, InventoryCategory, InventoryItem, PurchaseOrder, Student, User
from app.utils.permissions import role_required

@bp.route('/library', methods=['GET', 'POST'])
@role_required('librarian', 'principal')
def library():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        publisher = request.form.get('publisher')
        category = request.form.get('category')
        copies = int(request.form.get('total_copies', 1))
        
        new_book = LibraryBook(
            college_id=current_user.college_id,
            title=title, author=author, isbn=isbn,
            publisher=publisher, category=category,
            total_copies=copies, available_copies=copies
        )
        db.session.add(new_book)
        db.session.commit()
        flash(f'Added book: {title}', 'success')
        return redirect(url_for('infra.library'))
        
    books = LibraryBook.query.filter_by(college_id=current_user.college_id).all()
    issues = BookIssue.query.filter_by(college_id=current_user.college_id, status='Issued').all()
    return render_template('infra/library.html', books=books, issues=issues)

@bp.route('/transport', methods=['GET', 'POST'])
@role_required('transport_manager', 'principal')
def transport():
    if request.method == 'POST':
        route_name = request.form.get('route_name')
        vehicle_no = request.form.get('vehicle_no')
        driver_name = request.form.get('driver_name')
        driver_phone = request.form.get('driver_phone')
        capacity = request.form.get('capacity', type=int)
        monthly_fee = request.form.get('monthly_fee', type=float)
        
        new_route = TransportRoute(
            college_id=current_user.college_id, route_name=route_name,
            vehicle_no=vehicle_no, driver_name=driver_name,
            driver_phone=driver_phone, capacity=capacity,
            monthly_fee=monthly_fee
        )
        db.session.add(new_route)
        db.session.commit()
        flash('Transport route added.', 'success')
        return redirect(url_for('infra.transport'))
        
    routes = TransportRoute.query.filter_by(college_id=current_user.college_id).all()
    students = Student.query.join(User).filter(User.college_id == current_user.college_id).all()
    return render_template('infra/transport.html', routes=routes, students=students)

@bp.route('/transport/delete/<int:id>')
@role_required('transport_manager', 'principal')
def delete_transport(id):
    tr = TransportRoute.query.get_or_404(id)
    if tr.college_id != current_user.college_id and current_user.role != 'superadmin':
        abort(404)
    db.session.delete(tr)
    db.session.commit()
    flash('Transport route deleted.', 'info')
    return redirect(url_for('infra.transport'))

@bp.route('/transport/allocate', methods=['POST'])
@role_required('transport_manager', 'principal')
def allocate_transport():
    student_id = request.form.get('student_id', type=int)
    route_id = request.form.get('route_id', type=int)
    pickup_point = request.form.get('pickup_point')
    
    if student_id and route_id:
        student = Student.query.get_or_404(student_id)
        route = TransportRoute.query.get_or_404(route_id)
        if current_user.role != 'superadmin':
            if student.user.college_id != current_user.college_id or route.college_id != current_user.college_id:
                abort(404)

        alloc = TransportAllocation(
            student_id=student_id,
            route_id=route_id,
            college_id=current_user.college_id,
            pickup_point=pickup_point,
            status='active'
        )
        db.session.add(alloc)
        db.session.commit()
        flash('Transport allocated to student.', 'success')
    return redirect(url_for('infra.transport'))

@bp.route('/hostel', methods=['GET', 'POST'])
@role_required('hostel_warden', 'principal', 'student_affairs')
def hostel():
    if request.method == 'POST':
        hostel_name = request.form.get('hostel_name')
        room_number = request.form.get('room_number')
        bed_capacity = request.form.get('bed_capacity', type=int)
        room_type = request.form.get('room_type')
        monthly_fee = request.form.get('monthly_fee', type=float)
        
        new_room = HostelRoom(
            college_id=current_user.college_id, hostel_name=hostel_name,
            room_number=room_number, bed_capacity=bed_capacity,
            room_type=room_type, monthly_fee=monthly_fee
        )
        db.session.add(new_room)
        db.session.commit()
        flash('Hostel room added.', 'success')
        return redirect(url_for('infra.hostel'))

    rooms = HostelRoom.query.filter_by(college_id=current_user.college_id).all()
    students = Student.query.join(User).filter(User.college_id == current_user.college_id).all()
    return render_template('infra/hostel.html', rooms=rooms, students=students)

@bp.route('/hostel/delete/<int:id>')
@role_required('hostel_warden', 'principal', 'student_affairs')
def delete_hostel(id):
    room = HostelRoom.query.get_or_404(id)
    if room.college_id != current_user.college_id and current_user.role != 'superadmin':
        abort(404)
    
    HostelAllocation.query.filter_by(room_id=id).delete()
    db.session.delete(room)
    db.session.commit()
    flash('Hostel room deleted.', 'success')
    return redirect(url_for('infra.hostel'))

@bp.route('/hostel/allocate', methods=['POST'])
@role_required('hostel_warden', 'principal', 'student_affairs')
def allocate_hostel():
    room_id = request.form.get('room_id', type=int)
    student_id = request.form.get('student_id', type=int)
    
    room = HostelRoom.query.get_or_404(room_id)
    student = Student.query.get_or_404(student_id)
    if current_user.role != 'superadmin':
        if room.college_id != current_user.college_id or student.user.college_id != current_user.college_id:
            abort(404)
    
    # Check if room is full
    current_occ = HostelAllocation.query.filter_by(room_id=room_id, status='Occupied').count()
    if current_occ >= room.bed_capacity:
        flash('Room is already at full capacity.', 'danger')
        return redirect(url_for('infra.hostel'))

    existing = HostelAllocation.query.filter_by(student_id=student_id, status='Occupied').first()
    if existing:
        existing.room_id = room_id
    else:
        new_alloc = HostelAllocation(
            room_id=room_id, student_id=student_id,
            college_id=current_user.college_id, status='Occupied'
        )
        db.session.add(new_alloc)
    
    db.session.commit()
    flash('Student allocated to hostel room.', 'success')
    return redirect(url_for('infra.hostel'))

@bp.route('/inventory', methods=['GET', 'POST'])
@role_required('librarian', 'hostel_warden', 'transport_manager', 'accountant', 'principal')
def inventory():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_category':
            cat_name = request.form.get('category_name')
            new_cat = InventoryCategory(college_id=current_user.college_id, name=cat_name)
            db.session.add(new_cat)
            db.session.commit()
            flash('Category added.', 'success')
        else:
            name = request.form.get('name')
            category_id = request.form.get('category_id')
            quantity = request.form.get('quantity', type=int)
            unit_price = request.form.get('unit_price', type=float)
            reorder_level = request.form.get('reorder_level', type=int)
            
            new_item = InventoryItem(
                college_id=current_user.college_id, name=name,
                category_id=category_id,
                quantity=quantity, unit_price=unit_price,
                reorder_level=reorder_level
            )
            db.session.add(new_item)
            db.session.commit()
            flash('Inventory item added.', 'success')
        return redirect(url_for('infra.inventory'))

    items = InventoryItem.query.filter_by(college_id=current_user.college_id).all()
    categories = InventoryCategory.query.filter_by(college_id=current_user.college_id).all()
    return render_template('infra/inventory.html', items=items, categories=categories)

@bp.route('/inventory/delete/<int:id>')
@role_required('librarian', 'hostel_warden', 'transport_manager', 'accountant', 'principal')
def delete_inventory(id):
    item = InventoryItem.query.get_or_404(id)
    if item.college_id != current_user.college_id and current_user.role != 'superadmin':
        abort(404)
    
    db.session.delete(item)
    db.session.commit()
    flash('Inventory item deleted.', 'success')
    return redirect(url_for('infra.inventory'))

@bp.route('/inventory/edit/<int:id>', methods=['POST'])
@role_required('librarian', 'hostel_warden', 'transport_manager', 'accountant', 'principal')
def edit_inventory(id):
    item = InventoryItem.query.get_or_404(id)
    if item.college_id != current_user.college_id and current_user.role != 'superadmin':
        abort(404)
    
    item.name = request.form.get('name')
    item.quantity = request.form.get('quantity', type=int)
    item.unit_price = request.form.get('unit_price', type=float)
    item.reorder_level = request.form.get('reorder_level', type=int)
    item.category_id = request.form.get('category_id')
    
    db.session.commit()
    flash('Inventory item updated.', 'success')
    return redirect(url_for('infra.inventory'))



@bp.route('/library/issue', methods=['POST'])
@role_required('librarian', 'principal')
def issue_book():
    book_id = request.form.get('book_id', type=int)
    user_id = request.form.get('user_id', type=int)
    due_days = request.form.get('due_days', default=14, type=int)
    book = LibraryBook.query.get_or_404(book_id)
    user = User.query.get_or_404(user_id)
    if current_user.role != 'superadmin':
        if book.college_id != current_user.college_id or user.college_id != current_user.college_id:
            abort(404)
    if book.available_copies <= 0:
        flash(f'No available copies of "{book.title}" remaining.', 'danger')
        return redirect(url_for('infra.library'))
    
    from datetime import date, timedelta
    due_date = date.today() + timedelta(days=due_days)
    issue = BookIssue(
        book_id=book.id,
        user_id=user_id,
        college_id=current_user.college_id,
        issue_date=date.today(),
        due_date=due_date,
        status='Issued'
    )
    book.available_copies = max(0, book.available_copies - 1)
    db.session.add(issue)
    db.session.commit()
    flash(f'Book "{book.title}" successfully issued.', 'success')
    return redirect(url_for('infra.library'))


@bp.route('/library/return/<int:issue_id>', methods=['POST'])
@role_required('librarian', 'principal')
def return_book(issue_id):
    issue = BookIssue.query.get_or_404(issue_id)
    if issue.college_id != current_user.college_id and current_user.role != 'superadmin':
        abort(404)
    from datetime import date
    issue.return_date = date.today()
    issue.status = 'Returned'
    if issue.book:
        issue.book.available_copies = min(issue.book.total_copies, issue.book.available_copies + 1)
    if issue.due_date and date.today() > issue.due_date:
        overdue_days = (date.today() - issue.due_date).days
        issue.fine_amount = float(overdue_days * 5.0)
    db.session.commit()
    fine_str = f" Fine: ₹{issue.fine_amount:.2f}" if getattr(issue, 'fine_amount', 0) else ""
    flash(f'Book returned successfully.{fine_str}', 'success')
    return redirect(url_for('infra.library'))


@bp.route('/library/delete/<int:id>', methods=['POST', 'GET'])
@role_required('librarian', 'principal')
def delete_book(id):
    book = LibraryBook.query.get_or_404(id)
    if book.college_id != current_user.college_id and current_user.role != 'superadmin':
        abort(404)
    active_issues = BookIssue.query.filter_by(book_id=id, status='Issued').count()
    if active_issues > 0:
        flash(f'Cannot delete book "{book.title}" because {active_issues} copy is currently checked out.', 'danger')
        return redirect(url_for('infra.library'))
    db.session.delete(book)
    db.session.commit()
    flash(f'Book "{book.title}" removed from catalog.', 'info')
    return redirect(url_for('infra.library'))
