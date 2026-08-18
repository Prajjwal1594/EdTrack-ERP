from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
import os
import json
from google import genai
from app.models import db, Student, Grade, Attendance, SoftSkillMetric, MicroCredential, ParentStudentLink, User, College, Semester, Section, Subject

bp = Blueprint('ai', __name__)

@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    message = data.get('message')
    student_id = data.get('student_id') # Now optional
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    # Gather Context based on Role & student_id
    context = {}
    if student_id:
        student = Student.query.get(student_id)
        if student:
            # Authorization check for student specific data
            authorized = False
            if current_user.role == 'student':
                if current_user.student_profile and current_user.student_profile.id == student.id:
                    authorized = True
            elif current_user.role == 'parent':
                link = ParentStudentLink.query.filter_by(parent_id=current_user.id, student_id=student.id).first()
                if link:
                    authorized = True
            elif current_user.role in ['admin', 'faculty']:
                authorized = True
            
            if authorized:
                context = gather_student_context(student)
                target_name = student.user.name
            else:
                return jsonify({"error": "Unauthorized access to student data"}), 403
    
    # If no student_id context, or general query, gather role context
    if not context:
        if current_user.role == 'admin':
            context = gather_admin_context()
        elif current_user.role == 'faculty':
            context = gather_faculty_context(current_user)
        else:
            # General student/user context if they just ask about themselves
            if current_user.role == 'student' and current_user.student_profile:
                context = gather_student_context(current_user.student_profile)
            else:
                context = {"role": current_user.role, "user_name": current_user.name}

    # Real AI call (Gemini)
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        api_key = api_key.strip()
        
    if not api_key or api_key == 'your-gemini-key-here':
        return jsonify({
            "response": f"Hello {current_user.name}! I am currently in simulation mode (No GEMINI_API_KEY). I see you are a {current_user.role}.",
            "context": context
        })

    try:
        client = genai.Client(api_key=api_key)
        
        system_prompt = f"""
        You are 'El'Wood Academic Assistant', the college-wide AI companion for El'Wood International University.
        You are helping: {current_user.name} (Role: {current_user.role}).
        
        CURRENT CONTEXT:
        {json.dumps(context, indent=2)}
        
        INSTRUCTIONS:
        1. Be supportive, knowledgeable, and helpful about all college matters.
        2. If you have data in the context, use it to answer precisely.
        3. For Admins: Help with scheduling, fees, and general college overview.
        4. For Faculty: Help with section management, grading, and student performance.
        5. For Students/Parents: Provide encouraging academic insights and performance tips.
        6. Keep responses under 150 words. Use bullet points for data.
        7. Maintain the premium El'Wood brand voice.
        """
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[system_prompt, f"User says: {message}"]
        )
        
        ai_text = response.text if response and response.text else "I'm sorry, I couldn't generate a response."
        
        return jsonify({
            "response": ai_text,
            "context": context
        })
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            return jsonify({
                "error": "Quota Exceeded", 
                "response": "I'm currently busy with many requests. Please wait a minute and try again!"
            }), 429
        return jsonify({"error": error_msg, "response": f"Sorry, I encountered an issue: {error_msg}"}), 500

def gather_student_context(student):
    # Academic
    grades = student.grades.order_by(Grade.date.desc()).limit(10).all()
    avg_grade = sum(g.percentage for g in grades) / len(grades) if grades else 0
    # Soft Skills
    latest_skills = student.soft_skills.order_by(SoftSkillMetric.week_ending.desc()).first()
    
    return {
        "type": "student_deep_dive",
        "student_name": student.user.name,
        "holistic_score": student.holistic_growth_score(),
        "holistic_rating": student.holistic_rating,
        "avg_grade": round(avg_grade, 1),
        "attendance_pct": round(((student.attendance_records.filter_by(status='present').count() / student.attendance_records.count() * 100) if student.attendance_records.count() > 0 else 100), 1),
        "soft_skills": {
            "leadership": latest_skills.leadership if latest_skills else 5.0,
            "discipline": latest_skills.discipline if latest_skills else 5.0
        },
        "credentials": student.credentials.count()
    }

def gather_faculty_context(user):
    assignments = user.faculty_assignments
    semesters = [f"{a.section.semester_.name} {a.section.name} ({a.subject.name})" for a in assignments]
    return {
        "type": "faculty_overview",
        "taught_semesters": list(set(semesters)),
        "total_assignments_given": sum(a.section.assignments.count() for a in assignments)
    }

def gather_admin_context():
    return {
        "type": "admin_overview",
        "total_students": Student.query.count(),
        "total_faculty": User.query.filter_by(role='faculty').count(),
        "total_semesters": Semester.query.count()
    }

@bp.route('/insights/<int:student_id>')
@login_required
def get_insights(student_id):
    student = Student.query.get_or_404(student_id)
    context = gather_student_context(student)
    return jsonify(context)
