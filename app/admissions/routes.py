from flask import render_template, redirect, url_for, flash, request, jsonify, make_response
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.admissions import bp
from app.models import Enquiry, AdmissionApplication, Student, User, College
from app.utils.permissions import role_required
from datetime import datetime, timedelta


def make_cors_response(data, status_code=200):
    if isinstance(data, dict):
        resp = jsonify(data)
    else:
        resp = make_response(data)
    resp.status_code = status_code
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    return resp


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
@role_required('admission_officer', 'principal', 'registrar', 'admin', 'superadmin')
def enquiries():
    all_enquiries = Enquiry.query.filter_by(college_id=current_user.college_id).order_by(Enquiry.created_at.desc()).all()
    return render_template('admissions/enquiries.html', enquiries=all_enquiries)


@bp.route('/applications')
@role_required('admission_officer', 'principal', 'registrar', 'admin', 'superadmin')
def applications():
    apps = AdmissionApplication.query.filter_by(college_id=current_user.college_id).order_by(AdmissionApplication.submitted_at.desc()).all()
    return render_template('admissions/applications.html', applications=apps)


@bp.route('/public/<int:college_id>/inquire', methods=['GET', 'POST'])
def public_inquire(college_id):
    college = College.query.get_or_404(college_id)
    if request.method == 'POST':
        student_name = request.form.get('student_name')
        parent_name = request.form.get('parent_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        target_class = request.form.get('target_class')
        source = request.form.get('source') or 'Public Form'
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


@bp.route('/api/inquire', methods=['POST', 'OPTIONS'])
def api_inquire():
    """Universal Admission / Enquiry API endpoint for external school/college websites."""
    if request.method == 'OPTIONS':
        return make_cors_response({'status': 'ok'}, 200)

    # 1. Parse JSON, form-data, or url-encoded data
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict() if request.form else {}
        if not data and request.data:
            import json
            try:
                data = json.loads(request.data.decode('utf-8'))
            except Exception:
                pass

    # 2. Identify target institution
    school_identifier = (
        data.get('school_code') or 
        data.get('school') or 
        data.get('code') or 
        request.args.get('school_code') or 
        request.args.get('school') or
        request.args.get('code')
    )
    college_id = data.get('college_id') or request.args.get('college_id')

    college = None
    if college_id:
        try:
            college = College.query.get(int(college_id))
        except (ValueError, TypeError):
            pass

    if not college and school_identifier:
        code_str = str(school_identifier).strip().lower()
        college = College.query.filter(func.lower(College.code) == code_str).first()
        if not college:
            college = College.query.filter(College.name.ilike(f"%{school_identifier.strip()}%")).first()

    if not college:
        error_msg = f"School not found. Please provide a valid 'school_code' (e.g., EWIU, SRA) or 'college_id'."
        if request.is_json or 'application/json' in (request.headers.get('Accept') or ''):
            return make_cors_response({'success': False, 'error': error_msg}, 404)
        flash(error_msg, 'danger')
        return redirect(request.referrer or url_for('auth.login'))

    # 3. Extract & validate inquiry fields
    student_name = (data.get('student_name') or data.get('name') or data.get('applicant_name') or '').strip()
    parent_name = (data.get('parent_name') or data.get('guardian_name') or data.get('father_name') or '').strip()
    phone = (data.get('phone') or data.get('mobile') or data.get('contact') or data.get('telephone') or '').strip()
    email = (data.get('email') or data.get('parent_email') or '').strip()
    target_class = (data.get('target_class') or data.get('grade') or data.get('class') or data.get('course') or '').strip()
    notes = (data.get('notes') or data.get('message') or data.get('remarks') or data.get('comments') or data.get('query') or '').strip()
    source = (data.get('source') or 'School Website').strip()

    if not student_name:
        error_msg = "Field 'student_name' is required."
        if request.is_json or 'application/json' in (request.headers.get('Accept') or ''):
            return make_cors_response({'success': False, 'error': error_msg}, 400)
        flash(error_msg, 'danger')
        return redirect(request.referrer or url_for('auth.login'))

    # 4. Create and persist Enquiry
    new_enq = Enquiry(
        college_id=college.id,
        student_name=student_name,
        parent_name=parent_name or None,
        phone=phone or None,
        email=email or None,
        target_class=target_class or None,
        source=source,
        notes=notes or None,
        status='New'
    )
    db.session.add(new_enq)
    db.session.commit()

    # 5. Handle response based on client expectations
    redirect_url = data.get('redirect_url') or request.args.get('redirect_url')
    if redirect_url:
        sep = '&' if '?' in redirect_url else '?'
        return redirect(f"{redirect_url}{sep}enquiry_status=success&enquiry_id={new_enq.id}")

    if request.is_json or 'application/json' in (request.headers.get('Accept') or ''):
        return make_cors_response({
            'success': True,
            'message': f"Admission enquiry submitted successfully to {college.name}.",
            'enquiry_id': new_enq.id,
            'school': {
                'id': college.id,
                'name': college.name,
                'code': college.code
            }
        }, 201)

    return render_template('admissions/enquiry_success.html', college=college, enquiry=new_enq)


@bp.route('/api/school-info', methods=['GET', 'OPTIONS'])
def api_school_info():
    """Returns basic school information for embeddable widgets."""
    if request.method == 'OPTIONS':
        return make_cors_response({'status': 'ok'}, 200)

    school_identifier = request.args.get('school') or request.args.get('code') or request.args.get('school_code')
    college_id = request.args.get('college_id')

    college = None
    if college_id:
        try:
            college = College.query.get(int(college_id))
        except (ValueError, TypeError):
            pass

    if not college and school_identifier:
        code_str = str(school_identifier).strip().lower()
        college = College.query.filter(func.lower(College.code) == code_str).first()
        if not college:
            college = College.query.filter(College.name.ilike(f"%{school_identifier.strip()}%")).first()

    if not college:
        return make_cors_response({'success': False, 'error': 'School not found.'}, 404)

    return make_cors_response({
        'success': True,
        'school': {
            'id': college.id,
            'name': college.name,
            'code': college.code,
            'institution_type': college.institution_type or 'school',
            'is_school': college.is_school,
            'phone': college.phone,
            'email': college.email,
            'address': college.address
        }
    })


@bp.route('/enquiries/<int:eid>/status', methods=['POST'])
@role_required('admission_officer', 'principal', 'registrar', 'admin', 'superadmin')
def update_enquiry_status(eid):
    enq = Enquiry.query.get_or_404(eid)
    if enq.college_id != current_user.college_id and current_user.role != 'superadmin':
        return "Unauthorized", 403
    enq.status = request.form.get('status')
    db.session.commit()
    flash(f"Enquiry status updated to {enq.status}.", "success")
    return redirect(url_for('admissions.enquiries'))
