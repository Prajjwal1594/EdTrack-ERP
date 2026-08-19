"""
Seed the database with demo data for two colleges + a superadmin.
Run: python seed.py

Demo Accounts
─────────────────────────────────────────────────────────────────────────────
  Superadmin : superadmin@edtrack.com     / super123
  ─ College 1: El'Wood International University (EWIU) ─
  Admin      : admin@gmail.com            / admin123
  Faculty    : faculty@gmail.com          / faculty123
  Student    : student@gmail.com          / student123
  Parent     : parent@gmail.com           / parent123
  ─ College 2: Sunrise Academy (SRA) ─
  Admin      : admin2@sunrise.edu         / admin123
  Faculty    : faculty2@sunrise.edu       / faculty123
  Student    : student2@sunrise.edu       / student123
─────────────────────────────────────────────────────────────────────────────
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import (College, User, Semester, Section, Subject, FacultyAssignment,
                         Student, ParentStudentLink, AcademicTerm, Grade, Attendance,
                         Assignment, AssignmentSubmission, ReportComment, FeeType, FeePayment,
                         MicroCredential)
from datetime import date, datetime, timedelta
import random


# ── Helper: seed a single college's academic data ─────────────────────────────

def seed_college_data(college, admin, faculty, term_offset_months=0):
    """Populate semesters, subjects, students, grades, and attendance for one college."""
    random.seed(college.id * 42)

    # Academic Terms
    base = date(2024, 4, 1) + timedelta(days=term_offset_months * 30)
    terms = [
        AcademicTerm(college_id=college.id, name=f"Term 1 {college.code}", term_type="term",
                     start_date=base, end_date=base + timedelta(days=119),
                     academic_year="2024-2025"),
        AcademicTerm(college_id=college.id, name=f"Term 2 {college.code}", term_type="term",
                     start_date=base + timedelta(days=120), end_date=base + timedelta(days=239),
                     academic_year="2024-2025", is_active=True),
        AcademicTerm(college_id=college.id, name=f"Term 3 {college.code}", term_type="term",
                     start_date=base + timedelta(days=240), end_date=base + timedelta(days=364),
                     academic_year="2024-2025"),
    ]
    for t in terms:
        db.session.add(t)
    db.session.flush()
    active_term = terms[1]

    # Semesters & Sections
    semesters = []
    for i in range(1, 7):  # 6 semesters per college
        c = Semester(name=f"Semester {i}", academic_year="2024-2025", college_id=college.id)
        db.session.add(c)
        semesters.append(c)
    db.session.flush()

    sections = []
    for cls in semesters:
        for sec_name in ["A", "B"]:
            s = Section(semester_id=cls.id, name=sec_name, capacity=35)
            db.session.add(s)
            sections.append(s)
    db.session.flush()

    # Subjects
    subject_names = ["Mathematics", "English", "Science", "History", "Computer Science"]
    subjects = []
    for name in subject_names:
        s = Subject(name=name, code=name[:3].upper(), college_id=college.id)
        db.session.add(s)
        subjects.append(s)
    db.session.flush()

    # Faculty assignments
    for fac in faculty:
        for subj in subjects[:3]:
            for sec in sections[:4]:
                ta = FacultyAssignment(faculty_id=fac.id, subject_id=subj.id,
                                       section_id=sec.id, academic_year="2024-2025")
                db.session.add(ta)
    db.session.flush()

    # Fee types
    fee_data = [("Tuition Fee", 12000, "term"), ("Library Fee", 400, "annual"), ("Sports Fee", 800, "term")]
    fee_types = []
    for name, amount, freq in fee_data:
        ft = FeeType(college_id=college.id, name=name, amount=amount, frequency=freq)
        db.session.add(ft)
        fee_types.append(ft)
    db.session.flush()

    return sections, subjects, terms, active_term, fee_types


# ── Main seed function ─────────────────────────────────────────────────────────

def seed(app=None, auto=False):
    if app is None:
        app = create_app()
    
    with app.app_context():
        if not auto:
            print("Dropping all tables...")
            db.drop_all()
            print("Creating tables...")
            db.create_all()

        # ══════════════════════════════════════════════════════════════════════
        # SUPER ADMIN  (belongs to no college, college_id=None)
        # ══════════════════════════════════════════════════════════════════════
        superadmin = User(
            name="EdTrack Platform Admin",
            email="superadmin@edtrack.com",
            role="superadmin",
            college_id=None,
        )
        superadmin.set_password("super123")
        db.session.add(superadmin)
        db.session.flush()

        # ══════════════════════════════════════════════════════════════════════
        # COLLEGE 1 — El'Wood International University
        # ══════════════════════════════════════════════════════════════════════
        college1 = College(
            name="El'Wood International University",
            code="EWIU",
            address="14 Greenwood Avenue, Education City",
            phone="+1 (555) 0142",
            email="info@elwood.edu"
        )
        db.session.add(college1)
        db.session.flush()

        admin1 = User(name="Dr. Margaret Wells", email="admin@gmail.com",
                      role="admin", college_id=college1.id, phone="+1 555-0001")
        admin1.set_password("admin123")
        db.session.add(admin1)

        accountant1 = User(name="Robert Vance", email="accountant@gmail.com",
                           role="accountant", college_id=college1.id, phone="+1 555-0004")
        accountant1.set_password("accountant123")
        db.session.add(accountant1)

        faculty_data_1 = [
            ("Mr. James Harrison", "faculty@gmail.com", "faculty123"),
            ("Ms. Priya Sharma",   "priya@gmail.com",   "faculty123"),
            ("Mr. David Chen",     "dchen@gmail.com",   "faculty123"),
        ]
        faculty1 = []
        for name, email, pwd in faculty_data_1:
            t = User(name=name, email=email, role="faculty", college_id=college1.id)
            t.set_password(pwd)
            db.session.add(t)
            faculty1.append(t)
        db.session.flush()

        sections1, subjects1, terms1, active_term1, fee_types1 = seed_college_data(college1, admin1, faculty1)

        # Demo student (College 1)
        student_user1 = User(name="Alex Johnson", email="student@gmail.com",
                             role="student", college_id=college1.id)
        student_user1.set_password("student123")
        db.session.add(student_user1)
        db.session.flush()

        demo_student1 = Student(user_id=student_user1.id, section_id=sections1[0].id,
                                enrollment_number="EW00001",
                                date_of_birth=date(2009, 5, 15), gender="Male",
                                enrollment_date=date(2022, 4, 1))
        db.session.add(demo_student1)

        # Extra students (College 1)
        extra_names = ["Aarav Patel","Zara Ahmed","Liam Johnson","Sofia Martinez",
                       "Noah Williams","Aisha Khan","Ethan Brown","Mia Davis",
                       "Oliver Wilson","Emma Thompson","Lucas Garcia","Isabella Moore"]
        extra_students1 = [demo_student1]
        for i, name in enumerate(extra_names):
            email = name.lower().replace(' ', '.') + f"{i+10}@college1.edu"
            u = User(name=name, email=email, role="student", college_id=college1.id)
            u.set_password("student123")
            db.session.add(u)
            db.session.flush()
            s = Student(user_id=u.id, section_id=sections1[i % len(sections1)].id,
                        enrollment_number=f"EW{i+2:05d}",
                        date_of_birth=date(2008, random.randint(1, 12), random.randint(1, 28)),
                        gender=random.choice(["Male", "Female"]))
            db.session.add(s)
            extra_students1.append(s)
        db.session.flush()

        # Parent (College 1)
        parent1 = User(name="Robert Johnson", email="parent@gmail.com",
                       role="parent", college_id=college1.id, phone="+1 555-0099", wallet_balance=250.0)
        parent1.set_password("parent123")
        db.session.add(parent1)
        db.session.flush()
        db.session.add(ParentStudentLink(parent_id=parent1.id, student_id=demo_student1.id,
                                         relationship_type="father"))

        # Grades for College 1
        exam_names = ["Unit Test 1", "Mid-Term", "Unit Test 2", "Final Exam"]
        for student in extra_students1[:8]:
            for subj in subjects1[:4]:
                for term in terms1[:2]:
                    for exam in exam_names[:2]:
                        score = max(10, min(100, random.gauss(72, 15)))
                        db.session.add(Grade(
                            student_id=student.id, subject_id=subj.id, term_id=term.id,
                            exam_name=exam, score=round(score, 1), max_score=100,
                            date=term.start_date + timedelta(days=random.randint(20, 60)),
                            created_by=faculty1[0].id
                        ))

        # Attendance for College 1
        today = date.today()
        for student in extra_students1[:5]:
            for offset in range(45):
                d = today - timedelta(days=offset)
                if d.weekday() < 5:
                    status = random.choices(['present', 'absent', 'late'], weights=[85, 10, 5])[0]
                    db.session.add(Attendance(
                        student_id=student.id, section_id=student.section_id,
                        date=d, status=status, marked_by=faculty1[0].id
                    ))

        # Micro credentials
        db.session.add(MicroCredential(
            student_id=demo_student1.id, title="Debate Club Champion 2024",
            category="Leadership", issued_date=date(2024, 11, 15), issued_by=faculty1[0].id
        ))
        db.session.add(MicroCredential(
            student_id=demo_student1.id, title="Python Coding Bootcamp",
            category="Technology", issued_date=date(2024, 10, 5), issued_by=faculty1[1].id
        ))

        # Fee payments
        for student in extra_students1[:4]:
            for ft in fee_types1[:2]:
                for term in terms1[:2]:
                    status = random.choice(['paid', 'paid', 'pending'])
                    db.session.add(FeePayment(
                        student_id=student.id, fee_type_id=ft.id, term_id=term.id,
                        amount=ft.amount, due_date=term.start_date + timedelta(days=15),
                        status=status,
                        paid_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)) if status == 'paid' else None,
                        payment_method='cash' if status == 'paid' else None,
                        recorded_by=admin1.id
                    ))

        # ══════════════════════════════════════════════════════════════════════
        # COLLEGE 2 — Sunrise Academy
        # ══════════════════════════════════════════════════════════════════════
        college2 = College(
            name="Sunrise Academy",
            code="SRA",
            address="88 Sunrise Boulevard, Metro District",
            phone="+44 20 7946 0000",
            email="info@sunrise.edu"
        )
        db.session.add(college2)
        db.session.flush()

        admin2 = User(name="Ms. Diana Clarke", email="admin2@sunrise.edu",
                      role="admin", college_id=college2.id)
        admin2.set_password("admin123")
        db.session.add(admin2)

        accountant2 = User(name="Sarah Jenkins", email="accountant2@sunrise.edu",
                           role="accountant", college_id=college2.id)
        accountant2.set_password("accountant123")
        db.session.add(accountant2)

        faculty_data_2 = [
            ("Mr. Ahmed Malik",    "faculty2@sunrise.edu", "faculty123"),
            ("Ms. Clara Hernandez","clara@sunrise.edu",    "faculty123"),
        ]
        faculty2 = []
        for name, email, pwd in faculty_data_2:
            t = User(name=name, email=email, role="faculty", college_id=college2.id)
            t.set_password(pwd)
            db.session.add(t)
            faculty2.append(t)
        db.session.flush()

        sections2, subjects2, terms2, active_term2, fee_types2 = seed_college_data(college2, admin2, faculty2, term_offset_months=2)

        # Demo student (College 2)
        student_user2 = User(name="Maya Patel", email="student2@sunrise.edu",
                             role="student", college_id=college2.id)
        student_user2.set_password("student123")
        db.session.add(student_user2)
        db.session.flush()

        demo_student2 = Student(user_id=student_user2.id, section_id=sections2[0].id,
                                enrollment_number="SR00001",
                                date_of_birth=date(2010, 3, 22), gender="Female",
                                enrollment_date=date(2023, 6, 1))
        db.session.add(demo_student2)

        # Extra students (College 2)
        extra_names2 = ["Tom Baker", "Lily Chen", "Omar Hassan", "Grace Kim",
                        "Carlos Rivera", "Nina Popov", "Sam O'Brien"]
        extra_students2 = [demo_student2]
        for i, name in enumerate(extra_names2):
            email = name.lower().replace(' ', '.') + f"{i+5}@college2.edu"
            u = User(name=name, email=email, role="student", college_id=college2.id)
            u.set_password("student123")
            db.session.add(u)
            db.session.flush()
            s = Student(user_id=u.id, section_id=sections2[i % len(sections2)].id,
                        enrollment_number=f"SR{i+2:05d}",
                        date_of_birth=date(2009, random.randint(1, 12), random.randint(1, 28)),
                        gender=random.choice(["Male", "Female"]))
            db.session.add(s)
            extra_students2.append(s)
        db.session.flush()

        # Grades for College 2
        for student in extra_students2[:5]:
            for subj in subjects2[:3]:
                for term in terms2[:2]:
                    score = max(10, min(100, random.gauss(75, 12)))
                    db.session.add(Grade(
                        student_id=student.id, subject_id=subj.id, term_id=term.id,
                        exam_name="Mid-Term", score=round(score, 1), max_score=100,
                        date=term.start_date + timedelta(days=40),
                        created_by=faculty2[0].id
                    ))

        # Attendance for College 2
        for student in extra_students2[:4]:
            for offset in range(30):
                d = today - timedelta(days=offset)
                if d.weekday() < 5:
                    status = random.choices(['present', 'absent', 'late'], weights=[88, 8, 4])[0]
                    db.session.add(Attendance(
                        student_id=student.id, section_id=student.section_id,
                        date=d, status=status, marked_by=faculty2[0].id
                    ))

        db.session.commit()
        print("\nDatabase seeded successfully!\n")
        print("=" * 56)
        print("  DEMO LOGIN CREDENTIALS")
        print("=" * 56)
        print("  [Platform Super Admin]")
        print("  superadmin@edtrack.com     / super123")
        print()
        print(f"  [College 1: {college1.name}]")
        print("  admin@gmail.com            / admin123")
        print("  accountant@gmail.com       / accountant123")
        print("  faculty@gmail.com          / faculty123")
        print("  student@gmail.com          / student123")
        print("  parent@gmail.com           / parent123")
        print()
        print(f"  [College 2: {college2.name}]")
        print("  admin2@sunrise.edu         / admin123")
        print("  accountant2@sunrise.edu    / accountant123")
        print("  faculty2@sunrise.edu       / faculty123")
        print("  student2@sunrise.edu       / student123")
        print("=" * 56 + "\n")
        db.session.commit()
        print("Seeding completed successfully!")


if __name__ == "__main__":
    seed()
