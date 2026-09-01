from flask import render_template, redirect, url_for, flash, request
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
    db.session.delete(tr)
    db.session.commit()
    flash('Transport route deleted.', 'info')
    return redirect(url_for('infra.transport'))

@bp.route('/transport/allocate', methods=['POST'])
@role_required('transport_manager', 'principal')
def allocate_transport():
    student_id = request.form.get('student_id')
    route_id = request.form.get('route_id')
    pickup_point = request.form.get('pickup_point')
    
    if student_id and route_id:
        alloc = TransportAllocation(
            student_id=student_id,
            route_id=route_id,
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
    if room.college_id != current_user.college_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('infra.hostel'))
    
    HostelAllocation.query.filter_by(room_id=id).delete()
    db.session.delete(room)
    db.session.commit()
    flash('Hostel room deleted.', 'success')
    return redirect(url_for('infra.hostel'))

@bp.route('/hostel/allocate', methods=['POST'])
@role_required('hostel_warden', 'principal', 'student_affairs')
def allocate_hostel():
    room_id = request.form.get('room_id')
    student_id = request.form.get('student_id')
    
    # Check if room is full
    room = HostelRoom.query.get(room_id)
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
    if item.college_id != current_user.college_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('infra.inventory'))
    
    db.session.delete(item)
    db.session.commit()
    flash('Inventory item deleted.', 'success')
    return redirect(url_for('infra.inventory'))

@bp.route('/inventory/edit/<int:id>', methods=['POST'])
@role_required('librarian', 'hostel_warden', 'transport_manager', 'accountant', 'principal')
def edit_inventory(id):
    item = InventoryItem.query.get_or_404(id)
    if item.college_id != current_user.college_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('infra.inventory'))
    
    item.name = request.form.get('name')
    item.quantity = request.form.get('quantity', type=int)
    item.unit_price = request.form.get('unit_price', type=float)
    item.reorder_level = request.form.get('reorder_level', type=int)
    item.category_id = request.form.get('category_id')
    
    db.session.commit()
    flash('Inventory item updated.', 'success')
    return redirect(url_for('infra.inventory'))

