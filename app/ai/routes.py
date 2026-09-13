from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import os
import json
import requests as http_requests
from app.models import db, Student, Grade, Attendance, SoftSkillMetric, MicroCredential, ParentStudentLink, User, College, Semester, Section, Subject

bp = Blueprint('ai', __name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


@bp.before_request
def check_ai_feature_flag():
    from app.models import FeatureFlag
    cid = current_user.college_id if current_user and current_user.is_authenticated else 1
    flag = FeatureFlag.query.filter_by(college_id=cid, feature_key='ai_assistant').first()
    if flag and not flag.is_enabled:
        return jsonify({
            "error": "AI Academic Tutor has been disabled by your IT Administrator.",
            "disabled": True
        }), 403


@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    message = data.get('message')
    student_id = data.get('student_id')  # Optional

    if not message:
        return jsonify({"error": "No message provided"}), 400

    # ── Gather Context based on Role & student_id ───────────────────────────────
    context = {}
    if student_id:
        student = Student.query.get(student_id)
        if student:
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
            else:
                return jsonify({"error": "Unauthorized access to student data"}), 403

    if not context:
        if current_user.role == 'admin':
            context = gather_admin_context()
        elif current_user.role == 'faculty':
            context = gather_faculty_context(current_user)
        elif current_user.role == 'student' and current_user.student_profile:
            context = gather_student_context(current_user.student_profile)
        else:
            context = {"role": current_user.role, "user_name": current_user.name}

    # ── Gemini REST API call (no SDK needed) ────────────────────────────────────
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key:
        return jsonify({
            "response": (
                f"Hi {current_user.name}! I'm your Academic Assistant running in demo mode. "
                f"To enable full AI capabilities, please ask your IT Admin to add the GEMINI_API_KEY in the server environment. "
                f"You're logged in as **{current_user.role.replace('_', ' ').title()}**. "
                f"Get a free key at: aistudio.google.com"
            ),
            "context": context
        })

    college_name = "El'Wood International University"
    try:
        college = College.query.get(current_user.college_id) if current_user.college_id else None
        if college and college.name:
            college_name = college.name
    except Exception:
        pass

    system_prompt = (
        f"You are the Academic Assistant for {college_name}. "
        f"You are helping: {current_user.name} (Role: {current_user.role.replace('_', ' ').title()}). "
        f"Current data context: {json.dumps(context)}. "
        f"Instructions: Be supportive and professional. "
        f"Use the context data to give precise answers. "
        f"For students/parents give encouraging insights. "
        f"For admins/faculty give operational insights. "
        f"Keep replies under 150 words. Use bullet points when listing data. "
        f"Warm, premium university brand voice."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\nUser message: {message}"}
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 350,
            "temperature": 0.7
        }
    }

    try:
        resp = http_requests.post(
            f"{GEMINI_API_URL}?key={api_key}",
            json=payload,
            timeout=15
        )

        if resp.status_code == 429:
            return jsonify({
                "response": "I'm receiving a high volume of requests right now. Please try again in a moment! 🙏"
            }), 429

        if resp.status_code in (400, 403):
            return jsonify({
                "response": "The AI service key is invalid or not authorized. Please ask your IT Admin to check the GEMINI_API_KEY in Vercel settings."
            }), 503

        if resp.status_code != 200:
            return jsonify({
                "response": f"AI service returned an unexpected error (HTTP {resp.status_code}). Please try again shortly."
            }), 502

        result = resp.json()
        candidates = result.get("candidates", [])
        if not candidates:
            return jsonify({"response": "I couldn't generate a response right now. Please try again!"}), 200

        ai_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        if not ai_text:
            ai_text = "I couldn't generate a response. Please rephrase your question and try again."

        return jsonify({
            "response": ai_text,
            "context": context
        })

    except http_requests.exceptions.Timeout:
        return jsonify({"response": "The AI took too long to respond. Please try again in a moment."}), 504
    except Exception as e:
        return jsonify({
            "response": "I encountered an unexpected error. Please try again shortly.",
            "debug": str(e)
        }), 500


# ── Context Helpers ────────────────────────────────────────────────────────────

def gather_student_context(student):
    grades = student.grades.order_by(Grade.date.desc()).limit(10).all()
    avg_grade = sum(g.percentage for g in grades) / len(grades) if grades else 0
    latest_skills = student.soft_skills.order_by(SoftSkillMetric.week_ending.desc()).first()
    att_total = student.attendance_records.count()
    att_present = student.attendance_records.filter_by(status='present').count()

    return {
        "type": "student_deep_dive",
        "student_name": student.user.name,
        "holistic_score": student.holistic_growth_score(),
        "holistic_rating": student.holistic_rating,
        "avg_grade": round(avg_grade, 1),
        "attendance_pct": round((att_present / att_total * 100) if att_total > 0 else 100, 1),
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
