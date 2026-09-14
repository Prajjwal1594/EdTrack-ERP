from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
import os
import json
import requests as http_requests
from app.models import db, Student, Grade, Attendance, SoftSkillMetric, MicroCredential, ParentStudentLink, User, College, Semester, Section, Subject

bp = Blueprint('ai', __name__)

GEMINI_BASE = "https://generativelanguage.googleapis.com"

# Primary model confirmed working for this project
PRIMARY_MODEL = "gemini-2.5-flash"
# Fallbacks if primary fails
FALLBACK_MODELS = [
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-pro-latest",
]


def _gemini_headers(api_key):
    return {"x-goog-api-key": api_key, "Content-Type": "application/json"}


def _discover_model(api_key):
    """Fallback: call ListModels to dynamically find a working model."""
    try:
        r = http_requests.get(
            f"{GEMINI_BASE}/v1beta/models",
            headers=_gemini_headers(api_key),
            params={"pageSize": 50},
            timeout=8
        )
        if r.status_code == 200:
            models = r.json().get("models", [])
            supported = [
                m["name"].split("/")[-1] for m in models
                if "generateContent" in m.get("supportedGenerationMethods", [])
                and "embedding" not in m.get("name", "").lower()
            ]
            for pref in ["flash", "pro", ""]:
                for name in supported:
                    if pref in name.lower():
                        return name
    except Exception:
        pass
    return None


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
    student_id = data.get('student_id')

    if not message:
        return jsonify({"error": "No message provided"}), 400

    # ── Gather Context ──────────────────────────────────────────────────────────
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

    # ── API Key Check ───────────────────────────────────────────────────────────
    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if api_key in ('your-gemini-key-here', 'your_gemini_key', 'REPLACE_ME', ''):
        api_key = ''

    if not api_key:
        return jsonify({
            "response": (
                f"Hi {current_user.name}! I'm in demo mode — no GEMINI_API_KEY set. "
                "Ask IT Admin to add it in Vercel Environment Variables."
            ),
            "context": context
        })

    # ── Build system prompt ─────────────────────────────────────────────────────
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
        f"Be supportive and professional. Use the context data to give precise answers. "
        f"For students/parents give encouraging insights. For admins/faculty give operational insights. "
        f"Keep replies under 150 words. Use bullet points when listing data. "
        f"Warm, premium university brand voice."
    )

    payload = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\nUser message: {message}"}]}],
        "generationConfig": {"maxOutputTokens": 350, "temperature": 0.7}
    }

    # ── Call Gemini ──────────────────────────────────────────────────
    try:
        resp = None
        models_to_try = [PRIMARY_MODEL] + FALLBACK_MODELS
        for model_name in models_to_try:
            url = f"{GEMINI_BASE}/v1beta/models/{model_name}:generateContent"
            try:
                resp = http_requests.post(
                    url, json=payload,
                    headers=_gemini_headers(api_key),
                    timeout=12
                )
                if resp.status_code == 404:
                    continue  # try next
                break  # got a real response
            except http_requests.exceptions.Timeout:
                continue  # try next on timeout too

        if resp is None or resp.status_code == 404:
            return jsonify({
                "response": "AI service temporarily unavailable. Please try again in a moment."
            }), 503

        if resp.status_code == 429:
            return jsonify({"response": "High request volume — please try again in a moment! 🙏"}), 429

        if resp.status_code in (400, 401, 403):
            try:
                body = resp.json()
                err_msg = body.get('error', {}).get('message', 'Auth error')
            except Exception:
                err_msg = resp.text[:200]
            return jsonify({"response": f"API key error: {err_msg}"}), 503

        if resp.status_code != 200:
            try:
                body = resp.json()
            except Exception:
                body = {"raw": resp.text[:200]}
            return jsonify({"response": f"Gemini error (HTTP {resp.status_code})", "debug": body}), 502

        result = resp.json()
        candidates = result.get("candidates", [])
        if not candidates:
            return jsonify({"response": "No response generated. Please try again!"}), 200

        ai_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
        if not ai_text:
            ai_text = "I couldn't generate a response. Please rephrase and try again."

        return jsonify({"response": ai_text, "context": context})

    except http_requests.exceptions.Timeout:
        return jsonify({"response": "AI took too long to respond. Please try again."}), 504
    except Exception as e:
        return jsonify({"response": "Unexpected error. Please try again.", "debug": str(e)}), 500


# ── Context Helpers ─────────────────────────────────────────────────────────────

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


@bp.route('/test-key')
@login_required
def test_key():
    """IT Admin: diagnose GEMINI_API_KEY and show available models."""
    if current_user.role not in ['it_admin', 'admin', 'superadmin']:
        return jsonify({"error": "Unauthorized"}), 403

    api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY not set in Vercel environment"})

    try:
        r = http_requests.get(
            f"{GEMINI_BASE}/v1beta/models",
            headers=_gemini_headers(api_key),
            params={"pageSize": 50},
            timeout=10
        )
        if r.status_code == 200:
            models = r.json().get("models", [])
            generatable = [
                m["name"] for m in models
                if "generateContent" in m.get("supportedGenerationMethods", [])
            ]
            discovered = _discover_model(api_key)
            return jsonify({
                "key_prefix": api_key[:12] + "...",
                "key_length": len(api_key),
                "status": "KEY VALID ✓",
                "available_generative_models": generatable,
                "will_use_model": discovered,
                "configured_model_list": GEMINI_MODELS
            })
        else:
            return jsonify({
                "key_prefix": api_key[:12] + "...",
                "status": f"LIST MODELS FAILED (HTTP {r.status_code})",
                "body": r.json()
            })
    except Exception as e:
        return jsonify({"error": str(e)})
