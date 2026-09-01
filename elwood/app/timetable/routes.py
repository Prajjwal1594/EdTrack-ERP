from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.timetable import bp
from app.models import db, TimetableSlot, Section, Subject, User, College, Semester
from datetime import datetime, time

@bp.route('/')
@login_required
def index():
    if current_user.role == 'student':
        section_id = current_user.student_profile.section_id
        return redirect(url_for('timetable.view_section', section_id=section_id))
    elif current_user.role == 'parent':
        # For simplicity, view first student's timetable
        link = current_user.student_links.first()
        if not link:
            flash('No students linked to your account.', 'warning')
            return redirect(url_for('auth.dashboard'))
        return redirect(url_for('timetable.view_section', section_id=link.student.section_id))
    elif current_user.role in ['admin', 'superadmin', 'it_admin', 'faculty', 'principal', 'registrar', 'hod', 'examination_officer', 'course_coordinator', 'academic_advisor', 'student_affairs', 'placement_officer', 'librarian', 'hostel_warden', 'transport_manager']:
        sections = Section.query.join(Semester).filter(Semester.college_id == current_user.college_id).all()
        return render_template('timetable/index.html', sections=sections)
    return abort(403)

@bp.route('/section/<int:section_id>')
@login_required
def view_section(section_id):
    section = Section.query.get_or_404(section_id)
    if section.semester_.college_id != current_user.college_id:
        abort(403)
    
    slots = TimetableSlot.query.filter_by(section_id=section_id).all()
    
    # Organize slots by day and time
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    timetable = {day: [] for day in days}
    for slot in slots:
        if slot.day_of_week in timetable:
            timetable[slot.day_of_week].append(slot)
            
    # Sort slots by start time
    for day in timetable:
        timetable[day].sort(key=lambda x: x.start_time)
        
    return render_template('timetable/view.html', section=section, timetable=timetable, days=days)

@bp.route('/manage/<int:section_id>', methods=['GET', 'POST'])
@login_required
def manage(section_id):
    if current_user.role not in ['admin', 'faculty']:
        abort(403)
        
    section = Section.query.get_or_404(section_id)
    if section.semester_.college_id != current_user.college_id:
        abort(403)
        
    if request.method == 'POST':
        day = request.form.get('day')
        subject_id = request.form.get('subject_id')
        faculty_id = request.form.get('faculty_id')
        start_str = request.form.get('start_time')
        end_str = request.form.get('end_time')
        room = request.form.get('room_number')
        
        try:
            start_time = datetime.strptime(start_str, '%H:%M').time()
            end_time = datetime.strptime(end_str, '%H:%M').time()

            # Phase 7: Collision Detection (Goal 25)
            # Check for overlaps for the same Section, Faculty, or Room
            collision = TimetableSlot.query.filter(
                TimetableSlot.college_id == current_user.college_id,
                TimetableSlot.day_of_week == day,
                TimetableSlot.start_time < end_time,
                TimetableSlot.end_time > start_time
            ).filter(db.or_(
                TimetableSlot.section_id == section_id,
                TimetableSlot.faculty_id == faculty_id,
                TimetableSlot.room_number == room
            )).first()
            
            if collision:
                conflict_reason = "Section" if collision.section_id == int(section_id) else "Faculty" if collision.faculty_id == int(faculty_id) else "Room"
                flash(f'Scheduling Conflict: {conflict_reason} is already booked at this time (Slot: {collision.subject.name}).', 'danger')
                return redirect(url_for('timetable.manage', section_id=section_id))

            new_slot = TimetableSlot(
                college_id=current_user.college_id,
                section_id=section_id,
                subject_id=subject_id,
                faculty_id=faculty_id,
                day_of_week=day,
                start_time=start_time,
                end_time=end_time,
                room_number=room
            )
            db.session.add(new_slot)
            db.session.commit()
            flash('Timetable slot added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding slot: {str(e)}', 'danger')
            
        return redirect(url_for('timetable.manage', section_id=section_id))
        
    slots = TimetableSlot.query.filter_by(section_id=section_id).order_by(TimetableSlot.start_time).all()
    subjects = Subject.query.filter_by(college_id=current_user.college_id).all()
    faculty = User.query.filter_by(college_id=current_user.college_id, role='faculty').all()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    return render_template('timetable/manage.html', 
                           section=section, 
                           slots=slots, 
                           subjects=subjects, 
                           faculty=faculty,
                           days=days)

@bp.route('/delete/<int:slot_id>', methods=['POST'])
@login_required
def delete_slot(slot_id):
    if current_user.role not in ['admin', 'faculty']:
        abort(403)
    slot = TimetableSlot.query.get_or_404(slot_id)
    if slot.college_id != current_user.college_id:
        abort(403)
    
    section_id = slot.section_id
    db.session.delete(slot)
    db.session.commit()
    flash('Slot deleted.', 'info')
    return redirect(url_for('timetable.manage', section_id=section_id))
