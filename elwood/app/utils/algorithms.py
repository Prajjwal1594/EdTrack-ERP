from app.models import Student, Attendance, Grade, ParentStudentLink, User, FeePayment
from app.email import send_email
from datetime import datetime, timedelta

def evaluate_student_risk(student_id):
    """
    Evaluates if a student is at risk using the new Holistic Growth Score.
    Triggered by: Holistic Score < 60 OR Attendance < 75% OR Academic Avg < 50%.
    """
    student = Student.query.get(student_id)
    if not student:
        return
    
    holistic_score = student.holistic_growth_score()
    rating = student.holistic_rating
    
    # Check absences in last 30 days
    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
    recent_absences = Attendance.query.filter(
        Attendance.student_id == student_id,
        Attendance.date >= thirty_days_ago,
        Attendance.status == 'absent'
    ).count()

    # Check overall academic average
    grades = Grade.query.filter_by(student_id=student_id).all()
    avg_academic = sum(g.percentage for g in grades) / len(grades) if grades else 100.0

    # Risk Triggers
    is_at_risk = (holistic_score < 60) or (avg_academic < 50) or (recent_absences >= 3)
    
    if is_at_risk:
        parents = [link.parent for link in student.parent_links]
        recipients = [p.email for p in parents]
        if student.user.email:
            recipients.append(student.user.email)
            
        body = f"""
URGENT: Holistic Performance Warning
        
Dear Parent/Guardian,
Our Advanced Progress Tracking algorithm has identified that {student.user.name} 
is currently demonstrating at-risk holistic indicators.
        
Current Holistic Status:
- Holistic Growth Score: {holistic_score}/100
- Performance Rating: {rating}
- Academic Average: {avg_academic:.1f}%
- 30-Day Absences: {recent_absences}
        
A holistic score below 60 indicates a significant imbalance in academic, 
soft-skills, or participation metrics. Please contact the college's 
Academic Counselor immediately to discuss an intervention strategy.
        
Regards,
El'Wood Administration
Advanced Tracking Division
"""
        
        if recipients:
            send_email("🚨 URGENT: Holistic Intervention Required", recipients, body)
            print(f"[ALGO] Holistic Risk Alert dispatched for {student.user.name}")


def generate_parent_digest(college_id, sender_id=None):
    """
    Mines data from the last 7 days and compiles it into a seamless Friday Digest 
    for every parent in the college. Records as a Message in the DB for persistence.
    """
    from app.models import Message, db
    parents = User.query.filter_by(role='parent', college_id=college_id).all()
    
    digests_sent = 0
    for parent in parents:
        # Prepare data for HTML template
        reports = []
        links = ParentStudentLink.query.filter_by(parent_id=parent.id).all()
        seven_days_ago = datetime.utcnow().date() - timedelta(days=7)
        
        for link in links:
            student = link.student
            # Attendance
            recent_att = Attendance.query.filter(Attendance.student_id == student.id, Attendance.date >= seven_days_ago).all()
            absences = sum(1 for a in recent_att if a.status == 'absent')
            # Grades
            recent_grades = Grade.query.filter(Grade.student_id == student.id, Grade.date >= seven_days_ago).all()
            grades_data = [{'subject': g.subject.name, 'percentage': g.percentage, 'exam': g.exam_name} for g in recent_grades]
            # Fees
            pending_fees = sum(f.amount for f in FeePayment.query.filter_by(student_id=student.id, status='pending').all())
            
            reports.append({
                'student_name': student.user.name,
                'absences': absences,
                'grades': grades_data,
                'pending_fees': pending_fees
            })
            
        if not reports:
            continue

        from flask import render_template, url_for
        html_body = render_template('emails/weekly_digest.html', 
                                    parent=parent, 
                                    reports=reports, 
                                    today=datetime.utcnow(),
                                    dashboard_url=url_for('auth.login', _external=True))
        
        # Send Email
        send_email(f"Your El'Wood Weekly Digest: {datetime.utcnow().strftime('%d %b')}",
                   [parent.email],
                   "Please view the HTML version of this email.",
                   html_body=html_body)
        
        # Save as In-App Message
        if sender_id:
            msg = Message(
                sender_id=sender_id,
                recipient_id=parent.id,
                subject=f"Weekly Digest: {datetime.utcnow().strftime('%d %b %Y')}",
                body="HTML Digest sent to your email. Check your inbox for the full report.",
                message_type='digest'
            )
            db.session.add(msg)
            
        digests_sent += 1
    
    if sender_id:
        db.session.commit()
    print(f"[ALGO] Generated, sent, and recorded {digests_sent} parental digests.")


def get_parent_digest_preview(parent_id):
    """
    Generates the text for a single parent's weekly digest without sending it.
    """
    from app.models import ParentStudentLink, Attendance, Grade, FeePayment
    parent = User.query.get(parent_id)
    if not parent: return None
    
    links = ParentStudentLink.query.filter_by(parent_id=parent.id).all()
    if not links: return None
    
    seven_days_ago = datetime.utcnow().date() - timedelta(days=7)
    digest_body = f"Hello {parent.name},\n\nHere is your Weekly Parental Digest from El'Wood International:\n\n"
    
    for link in links:
        student = link.student
        digest_body += f"--- {student.user.name} ---\n"
        
        # Get recent attendance
        recent_att = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.date >= seven_days_ago
        ).all()
        absences = sum(1 for a in recent_att if a.status == 'absent')
        digest_body += f"* Absences this week: {absences}\n"
        
        # Get recent grades
        recent_grades = Grade.query.filter(
            Grade.student_id == student.id,
            Grade.date >= seven_days_ago
        ).all()
        if recent_grades:
            digest_body += "* New Assessment Grades:\n"
            for g in recent_grades:
                digest_body += f"  - {g.subject.name} ({g.exam_name}): {g.percentage}%\n"
        else:
            digest_body += "* No new formal grades recorded this week.\n"
            
        # Get pending fees
        pending_fees = FeePayment.query.filter_by(student_id=student.id, status='pending').all()
        if pending_fees:
            total_due = sum(f.amount for f in pending_fees)
            digest_body += f"* PENDING FEES: ₹{total_due:.2f} (Please check the Digital Wallet!)\n"
        else:
            digest_body += "* Pending Fees: ₹0.00\n"
        
        digest_body += "\n"
        
    digest_body += "\nHave a great weekend!\nEl'Wood Automated System\n(Algorithms Division)"
    return digest_body
