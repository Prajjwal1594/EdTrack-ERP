from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.admissions import bp
from app.models import Enquiry, AdmissionApplication, Student, User
from app.admin.routes import admin_required
from datetime import datetime

@bp.route('/enquiries')
@admin_required
def enquiries():
    all_enquiries = Enquiry.query.filter_by(college_id=current_user.college_id).order_by(Enquiry.created_at.desc()).all()
    return render_template('admissions/enquiries.html', enquiries=all_enquiries)

@bp.route('/applications')
@admin_required
def applications():
    apps = AdmissionApplication.query.filter_by(college_id=current_user.college_id).order_by(AdmissionApplication.submitted_at.desc()).all()
    return render_template('admissions/applications.html', applications=apps)

@bp.route('/public/<int:college_id>/inquire', methods=['GET', 'POST'])
def public_inquire(college_id):
    from app.models import College
    college = College.query.get_or_404(college_id)
    if request.method == 'POST':
        student_name = request.form.get('student_name')
        parent_name = request.form.get('parent_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        target_class = request.form.get('target_class')
        source = request.form.get('source')
        notes = request.form.get('notes')
        
        new_enq = Enquiry(
            college_id=college_id, student_name=student_name, parent_name=parent_name,
            phone=phone, email=email, target_class=target_class,
            source=source, notes=notes, status='New'
        )
        db.session.add(new_enq)
        db.session.commit()
        flash('Your enquiry has been successfully submitted! Our team will contact you shortly.', 'success')
        return redirect(url_for('admissions.public_inquire', college_id=college_id))
        
    return render_template('admissions/public_inquire.html', college=college)

@bp.route('/enquiries/<int:eid>/status', methods=['POST'])
@admin_required
def update_enquiry_status(eid):
    enq = Enquiry.query.get_or_404(eid)
    if enq.college_id != current_user.college_id:
        return "Unauthorized", 403
    enq.status = request.form.get('status')
    db.session.commit()
    flash(f"Enquiry status updated to {enq.status}.", "success")
    return redirect(url_for('admissions.enquiries'))
