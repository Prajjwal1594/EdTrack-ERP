from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.admissions import bp
from app.models import Enquiry, AdmissionApplication, Student, User
from app.utils.permissions import role_required
from datetime import datetime, timedelta


@bp.route('/')
@role_required('admission_officer', 'principal', 'registrar', 'admin', 'superadmin')
def index():
    """Admissions dashboard — overview of enquiries and applications."""
    college_id = current_user.college_id
    today = datetime.utcnow()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_enquiries = Enquiry.query.filter_by(college_id=college_id).count()
    new_enquiries = Enquiry.query.filter_by(college_id=college_id, status='New').count()
    followup_enquiries = Enquiry.query.filter_by(college_id=college_id, status='Follow-up').count()
    closed_enquiries = Enquiry.query.filter_by(college_id=college_id, status='Closed').count()

    total_applications = AdmissionApplication.query.filter_by(college_id=college_id).count()
    submitted = AdmissionApplication.query.filter_by(college_id=college_id, status='Submitted').count()
    under_review = AdmissionApplication.query.filter_by(college_id=college_id, status='Under Review').count()
    approved = AdmissionApplication.query.filter_by(college_id=college_id, status='Approved').count()
    enrolled = AdmissionApplication.query.filter_by(college_id=college_id, status='Enrolled').count()

    recent_enquiries = (Enquiry.query.filter_by(college_id=college_id)
                        .order_by(Enquiry.created_at.desc()).limit(8).all())
    recent_applications = (AdmissionApplication.query.filter_by(college_id=college_id)
                           .order_by(AdmissionApplication.submitted_at.desc()).limit(8).all())

    conversion_rate = round((enrolled / total_enquiries * 100) if total_enquiries > 0 else 0, 1)

    return render_template('admissions/index.html',
                           total_enquiries=total_enquiries,
                           new_enquiries=new_enquiries,
                           followup_enquiries=followup_enquiries,
                           closed_enquiries=closed_enquiries,
                           total_applications=total_applications,
                           submitted=submitted,
                           under_review=under_review,
                           approved=approved,
                           enrolled=enrolled,
                           recent_enquiries=recent_enquiries,
                           recent_applications=recent_applications,
                           conversion_rate=conversion_rate)


@bp.route('/enquiries')
@role_required('admission_officer', 'principal', 'registrar')
def enquiries():
    all_enquiries = Enquiry.query.filter_by(college_id=current_user.college_id).order_by(Enquiry.created_at.desc()).all()
    return render_template('admissions/enquiries.html', enquiries=all_enquiries)

@bp.route('/applications')
@role_required('admission_officer', 'principal', 'registrar')
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
@role_required('admission_officer', 'principal', 'registrar')
def update_enquiry_status(eid):
    enq = Enquiry.query.get_or_404(eid)
    if enq.college_id != current_user.college_id:
        return "Unauthorized", 403
    enq.status = request.form.get('status')
    db.session.commit()
    flash(f"Enquiry status updated to {enq.status}.", "success")
    return redirect(url_for('admissions.enquiries'))
