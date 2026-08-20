from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import json


@login_manager.user_loader
def load_user(user_id):
    try:
        u = User.query.get(int(user_id))
        if not u:
            # If user table is empty (e.g. fresh lambda /tmp SQLite), auto-seed demo users
            if not User.query.first():
                from seed import seed
                from flask import current_app
                seed(current_app, auto=True)
                u = User.query.get(int(user_id))
        return u
    except Exception:
        return None


class College(db.Model):
    __tablename__ = 'colleges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    logo_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('User', backref='college', lazy='dynamic', cascade='all, delete-orphan')
    semesters = db.relationship('Semester', backref='college', lazy='dynamic', cascade='all, delete-orphan')
    subjects = db.relationship('Subject', backref='college', lazy='dynamic', cascade='all, delete-orphan')
    terms = db.relationship('AcademicTerm', backref='college', lazy='dynamic', cascade='all, delete-orphan')
    fee_types = db.relationship('FeeType', backref='college', lazy='dynamic', cascade='all, delete-orphan')
    courses = db.relationship('Course', backref='college', lazy='dynamic', cascade='all, delete-orphan')
    streams = db.relationship('Stream', backref='college', lazy='dynamic', cascade='all, delete-orphan')
    batches = db.relationship('Batch', backref='college', lazy='dynamic', cascade='all, delete-orphan')


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(50), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    is_active = db.Column(db.Boolean, default=True)
    avatar = db.Column(db.String(300))
    phone = db.Column(db.String(30))
    wallet_balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
    student_profile = db.relationship('Student', foreign_keys='Student.user_id', backref='user', uselist=False)
    faculty_assignments = db.relationship('FacultyAssignment', foreign_keys='FacultyAssignment.faculty_id', backref='faculty')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    student_links = db.relationship('ParentStudentLink', foreign_keys='ParentStudentLink.parent_id', backref='parent', lazy='dynamic')

    ROLE_TITLES = {
        'superadmin': 'Super Admin',
        'admin': 'Institution Admin',
        'it_admin': 'IT Administrator',
        'principal': 'Principal',
        'registrar': 'Registrar',
        'hod': 'Head of Department (HOD)',
        'admission_officer': 'Admission Officer',
        'accountant': 'Accountant',
        'hr': 'HR Manager',
        'examination_officer': 'Examination Officer',
        'faculty': 'Faculty',
        'course_coordinator': 'Course Coordinator',
        'academic_advisor': 'Academic Advisor',
        'librarian': 'Librarian',
        'hostel_warden': 'Hostel Warden',
        'transport_manager': 'Transport Manager',
        'placement_officer': 'Placement Officer',
        'student_affairs': 'Student Affairs Officer',
        'student': 'Student',
        'parent': 'Parent',
        'alumni': 'Alumni',
        'employer': 'Employer',
    }

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role_display_name(self):
        return self.ROLE_TITLES.get(self.role, self.role.replace('_', ' ').title() if self.role else 'User')

    @property
    def unread_message_count(self):
        return Message.query.filter_by(recipient_id=self.id, read_at=None).count()

    @property
    def unread_notification_count(self):
        return self.notifications.filter_by(is_read=False).count()

    def __repr__(self):
        return f'<User {self.name} ({self.role})>'


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))
    description = db.Column(db.Text)
    chief_counselor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Chief Batch Counselor for Course
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    chief_counselor = db.relationship('User', foreign_keys=[chief_counselor_id])
    streams = db.relationship('Stream', backref='course', lazy='dynamic', cascade='all, delete-orphan')
    sections = db.relationship('Section', backref='course', lazy='dynamic')
    students = db.relationship('Student', backref='course', lazy='dynamic')

    def __repr__(self):
        return f'<Course {self.name}>'


class Stream(db.Model):
    __tablename__ = 'streams'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))
    head_counselor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Head Batch Counsellor for Stream
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    head_counselor = db.relationship('User', foreign_keys=[head_counselor_id])
    sections = db.relationship('Section', backref='stream', lazy='dynamic')
    students = db.relationship('Student', backref='stream', lazy='dynamic')

    def __repr__(self):
        return f'<Stream {self.name}>'


class Batch(db.Model):
    __tablename__ = 'batches'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    name = db.Column(db.String(50), nullable=False)
    start_year = db.Column(db.Integer)
    end_year = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sections = db.relationship('Section', backref='batch', lazy='dynamic')
    students = db.relationship('Student', backref='batch', lazy='dynamic')

    def __repr__(self):
        return f'<Batch {self.name}>'


class Semester(db.Model):
    __tablename__ = 'semesters'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    academic_year = db.Column(db.String(20), nullable=False)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sections = db.relationship('Section', backref='semester_', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Semester {self.name}>'


class Section(db.Model):
    __tablename__ = 'sections'
    id = db.Column(db.Integer, primary_key=True)
    semester_id = db.Column(db.Integer, db.ForeignKey('semesters.id'), nullable=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    stream_id = db.Column(db.Integer, db.ForeignKey('streams.id'), nullable=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    name = db.Column(db.String(10), nullable=False)
    room_number = db.Column(db.String(20))
    capacity = db.Column(db.Integer, default=40)
    batch_counselor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Batch Counsellor for Section
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    batch_counselor = db.relationship('User', foreign_keys=[batch_counselor_id])
    students = db.relationship('Student', backref='section', lazy='dynamic')
    faculty_assignments = db.relationship('FacultyAssignment', backref='section', cascade='all, delete-orphan')
    attendance_records = db.relationship('Attendance', backref='section', lazy='dynamic', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='section', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def full_name(self):
        sem_str = f"{self.semester_.name} - " if self.semester_ else ""
        c_str = f" [{self.course.name}]" if hasattr(self, 'course') and self.course else ""
        return f"{sem_str}{self.name}{c_str}"

    def __repr__(self):
        return f'<Section {self.full_name}>'


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    faculty_assignments = db.relationship('FacultyAssignment', backref='subject', cascade='all, delete-orphan')
    grades = db.relationship('Grade', backref='subject', lazy='dynamic', cascade='all, delete-orphan')
    assignments = db.relationship('Assignment', backref='subject', lazy='dynamic', cascade='all, delete-orphan')
    exams = db.relationship('Exam', backref='subject', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Subject {self.name}>'


class FacultyAssignment(db.Model):
    __tablename__ = 'faculty_assignments'
    id = db.Column(db.Integer, primary_key=True)
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    academic_year = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=True)
    stream_id = db.Column(db.Integer, db.ForeignKey('streams.id'), nullable=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('batches.id'), nullable=True)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=True)
    enrollment_number = db.Column(db.String(30), unique=True)
    roll_number = db.Column(db.String(30))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(10))
    address = db.Column(db.Text)
    state = db.Column(db.String(100))
    country = db.Column(db.String(100))
    enrollment_date = db.Column(db.Date, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Detailed ERP Personal/Enrollment Info
    blood_group = db.Column(db.String(10))
    religion = db.Column(db.String(50))
    caste = db.Column(db.String(50))
    aadhar_number = db.Column(db.String(20))
    admission_category = db.Column(db.String(50))
    session = db.Column(db.String(20))
    tc_date = db.Column(db.Date)
    biometric_card_no = db.Column(db.String(50))
    alternate_semester_group = db.Column(db.String(20))
    semester_group = db.Column(db.String(20))
    phone2 = db.Column(db.String(30))
    landline = db.Column(db.String(30))

    # Academic History (10th/12th)
    tenth_year = db.Column(db.Integer)
    tenth_roll = db.Column(db.String(50))
    tenth_board = db.Column(db.String(100))
    tenth_obtained = db.Column(db.Float)
    tenth_max = db.Column(db.Float)
    
    twelfth_year = db.Column(db.Integer)
    twelfth_roll = db.Column(db.String(50))
    twelfth_board = db.Column(db.String(100))
    twelfth_obtained = db.Column(db.Float)
    twelfth_max = db.Column(db.Float)

    # Guardian Info (Centralized on Student)
    father_name = db.Column(db.String(100))
    father_occupation = db.Column(db.String(100))
    father_mobile = db.Column(db.String(30))
    mother_name = db.Column(db.String(100))
    mother_mobile = db.Column(db.String(30))
    local_guardian_name = db.Column(db.String(100))
    local_guardian_mobile = db.Column(db.String(30))
    local_guardian_address = db.Column(db.Text)

    parent_links = db.relationship('ParentStudentLink', backref='student', lazy='dynamic')
    grades = db.relationship('Grade', backref='student', lazy='dynamic')
    attendance_records = db.relationship('Attendance', backref='student', lazy='dynamic')
    assignment_submissions = db.relationship('AssignmentSubmission', backref='student', lazy='dynamic')
    exam_submissions = db.relationship('ExamSubmission', backref='student', lazy='dynamic')
    fee_payments = db.relationship('FeePayment', backref='student', lazy='dynamic')
    report_comments = db.relationship('ReportComment', backref='student', lazy='dynamic')
    credentials = db.relationship('MicroCredential', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    soft_skills = db.relationship('SoftSkillMetric', backref='student', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def course_name(self):
        if self.course:
            return self.course.name
        if self.section and hasattr(self.section, 'course') and self.section.course:
            return self.section.course.name
        return 'N/A'

    @property
    def stream_name(self):
        if self.stream:
            return self.stream.name
        if self.section and hasattr(self.section, 'stream') and self.section.stream:
            return self.section.stream.name
        return 'N/A'

    @property
    def batch_name(self):
        if self.batch:
            return self.batch.name
        if self.section and hasattr(self.section, 'batch') and self.section.batch:
            return self.section.batch.name
        return 'N/A'

    @property
    def section_name(self):
        if self.section:
            return self.section.name
        return 'N/A'

    def holistic_growth_score(self):
        """
        Calculates a 0-100 Holistic Growth Score:
        40% Academic (Avg Grade % + Attendance %)
        35% Soft Skills (Avg of Leadership, Discipline, etc.)
        25% Co-Curricular (Micro-Credentials & Participation Hours)
        """
        # 1. Academic (40%)
        # Calculate avg grade percentage
        grade_records = self.grades.all()
        avg_grade = sum(g.percentage for g in grade_records) / len(grade_records) if grade_records else 75.0
        
        # Calculate attendance percentage
        att_total = self.attendance_records.count()
        att_present = self.attendance_records.filter(Attendance.status.in_(['present', 'late'])).count()
        attendance_pct = (att_present / att_total * 100) if att_total > 0 else 100.0
        
        academic_comp = (0.7 * avg_grade / 100.0) + (0.3 * attendance_pct / 100.0)

        # 2. Soft Skills (35%)
        latest_skills = self.soft_skills.order_by(SoftSkillMetric.week_ending.desc()).first()
        if latest_skills:
            skills_avg = (latest_skills.leadership + latest_skills.discipline + 
                          latest_skills.communication + latest_skills.teamwork) / 40.0 # 0-1 scale
            participation_hours = min(latest_skills.participation_hours / 15.0, 1.0)
        else:
            skills_avg = 0.5
            participation_hours = 0.0

        # 3. Co-Curricular (25%)
        # Each credential adds a bonus
        cred_count = self.credentials.count()
        cred_bonus = min(cred_count * 2.0, 10.0) # Max 10 points bonus

        raw_score = (0.40 * academic_comp + 0.35 * skills_avg + 0.25 * participation_hours) * 100.0
        final_score = min(raw_score + cred_bonus, 100.0)
        
        return round(final_score, 1)

    @property
    def holistic_rating(self):
        score = self.holistic_growth_score()
        if score >= 90: return 'Exceptional'
        if score >= 80: return 'Excellent'
        if score >= 70: return 'Good'
        if score >= 60: return 'Average'
        return 'Needs Focus'


class ParentStudentLink(db.Model):
    __tablename__ = 'parent_student_links'
    id = db.Column(db.Integer, primary_key=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    relationship_type = db.Column(db.String(30), default='parent')


class AcademicTerm(db.Model):
    __tablename__ = 'academic_terms'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    name = db.Column(db.String(50), nullable=False)
    term_type = db.Column(db.String(20), default='term')  # term, semester, quarter
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    academic_year = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    grades = db.relationship('Grade', backref='term', lazy='dynamic')
    report_comments = db.relationship('ReportComment', backref='term', lazy='dynamic')
    fee_payments = db.relationship('FeePayment', backref='term', lazy='dynamic')


class Grade(db.Model):
    __tablename__ = 'grades'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    term_id = db.Column(db.Integer, db.ForeignKey('academic_terms.id'))
    exam_name = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Float, nullable=False)  # 0-100
    max_score = db.Column(db.Float, default=100)
    date = db.Column(db.Date, default=datetime.utcnow)
    remarks = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def percentage(self):
        if self.max_score and self.max_score > 0:
            return round((self.score / self.max_score) * 100, 1)
        return 0.0

    @property
    def letter_grade(self):
        p = self.percentage
        if p >= 90: return 'A+'
        elif p >= 80: return 'A'
        elif p >= 70: return 'B+'
        elif p >= 60: return 'B'
        elif p >= 50: return 'C'
        elif p >= 40: return 'D'
        else: return 'F'


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime, nullable=False)
    max_score = db.Column(db.Float, default=100)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    submissions = db.relationship('AssignmentSubmission', backref='assignment', lazy='dynamic')
    creator = db.relationship('User', foreign_keys=[created_by])

    @property
    def is_overdue(self):
        return datetime.utcnow() > self.due_date


class AssignmentSubmission(db.Model):
    __tablename__ = 'assignment_submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    grade = db.Column(db.Float)
    feedback = db.Column(db.Text)
    content = db.Column(db.Text)  # submission text
    is_late = db.Column(db.Boolean, default=False)
    graded_at = db.Column(db.DateTime)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'))


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # present, absent, late, excused
    remarks = db.Column(db.String(200))
    marked_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    marked_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('student_id', 'date', name='uq_student_date'),)

    marker = db.relationship('User', foreign_keys=[marked_by])


class ReportComment(db.Model):
    __tablename__ = 'report_comments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    term_id = db.Column(db.Integer, db.ForeignKey('academic_terms.id'))
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    faculty = db.relationship('User', foreign_keys=[faculty_id])


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime)
    parent_id = db.Column(db.Integer, db.ForeignKey('messages.id'))
    message_type = db.Column(db.String(20), default='regular')  # regular, digest
    is_deleted_sender = db.Column(db.Boolean, default=False)
    is_deleted_recipient = db.Column(db.Boolean, default=False)

    replies = db.relationship('Message', backref=db.backref('parent', remote_side=[id]))


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    type = db.Column(db.String(50))  # low_grade, absent, missing_assignment, fee_due
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    link = db.Column(db.String(300))
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Exam(db.Model):
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    description = db.Column(db.Text)
    duration_minutes = db.Column(db.Integer, default=60)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    total_marks = db.Column(db.Float, default=100)
    is_published = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship('ExamQuestion', backref='exam', lazy='dynamic', cascade='all, delete-orphan')
    submissions = db.relationship('ExamSubmission', backref='exam', lazy='dynamic')
    creator = db.relationship('User', foreign_keys=[created_by])
    section = db.relationship('Section', foreign_keys=[section_id])

    @property
    def is_active(self):
        now = datetime.utcnow()
        if self.start_time and self.end_time:
            start = self.start_time.replace(tzinfo=None)
            end = self.end_time.replace(tzinfo=None)
            return start <= now <= end and self.is_published
        return self.is_published


class ExamQuestion(db.Model):
    __tablename__ = 'exam_questions'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'))
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='mcq')  # mcq, true_false, short_answer
    options_json = db.Column(db.Text)  # JSON list of options for MCQ
    correct_answer = db.Column(db.String(500))
    marks = db.Column(db.Float, default=1)
    order_num = db.Column(db.Integer, default=0)

    @property
    def options(self):
        if self.options_json:
            return json.loads(self.options_json)
        return []

    @options.setter
    def options(self, value):
        self.options_json = json.dumps(value)


class ExamSubmission(db.Model):
    __tablename__ = 'exam_submissions'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    score = db.Column(db.Float)
    answers_json = db.Column(db.Text)
    is_graded = db.Column(db.Boolean, default=False)

    @property
    def answers(self):
        if self.answers_json:
            return json.loads(self.answers_json)
        return {}

    @answers.setter
    def answers(self, value):
        self.answers_json = json.dumps(value)

    @property
    def percentage(self):
        if self.exam and self.exam.total_marks and self.score is not None:
            return round((self.score / self.exam.total_marks) * 100, 1)
        return None


class FeeType(db.Model):
    __tablename__ = 'fee_types'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    frequency = db.Column(db.String(20), default='term')  # monthly, term, annual
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payments = db.relationship('FeePayment', backref='fee_type', lazy='dynamic')


class FeePayment(db.Model):
    __tablename__ = 'fee_payments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    fee_type_id = db.Column(db.Integer, db.ForeignKey('fee_types.id'))
    term_id = db.Column(db.Integer, db.ForeignKey('academic_terms.id'))
    amount = db.Column(db.Float, nullable=False)
    paid_at = db.Column(db.DateTime)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # pending, paid, overdue, waived
    payment_method = db.Column(db.String(50))
    transaction_ref = db.Column(db.String(100))
    notes = db.Column(db.Text)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MicroCredential(db.Model):
    __tablename__ = 'micro_credentials'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='Skill')  # Leadership, Tech, Arts, etc.
    issued_date = db.Column(db.Date)
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    issuer = db.relationship('User', foreign_keys=[issued_by])


class SoftSkillMetric(db.Model):
    __tablename__ = 'soft_skill_metrics'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    week_ending = db.Column(db.Date, nullable=False)
    leadership = db.Column(db.Float, default=5.0)  # 0-10
    discipline = db.Column(db.Float, default=5.0)
    communication = db.Column(db.Float, default=5.0)
    teamwork = db.Column(db.Float, default=5.0)
    participation_hours = db.Column(db.Float, default=0.0)
    remarks = db.Column(db.Text)
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recorder = db.relationship('User', foreign_keys=[recorded_by])


class TimetableSlot(db.Model):
    __tablename__ = 'timetable_slots'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'))
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'))
    faculty_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    day_of_week = db.Column(db.String(10), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room_number = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    college = db.relationship('College')
    section = db.relationship('Section')
    subject = db.relationship('Subject')
    faculty = db.relationship('User', foreign_keys=[faculty_id])


# ─── ERP Feature Models ───────────────────────────────────────────────────────

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    title = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text)
    announcement_type = db.Column(db.String(20), nullable=False, default='notice')  # event, holiday, notice
    date = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    college = db.relationship('College', backref=db.backref('announcements', lazy='dynamic'))
    creator = db.relationship('User', foreign_keys=[created_by])


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String(200))
    max_capacity = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    requires_registration = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    college = db.relationship('College', backref=db.backref('events', lazy='dynamic'))
    creator = db.relationship('User', foreign_keys=[created_by])
    registrations = db.relationship('EventRegistration', backref='event', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def registered_count(self):
        return self.registrations.count()

    @property
    def is_full(self):
        if self.max_capacity:
            return self.registered_count >= self.max_capacity
        return False


class EventRegistration(db.Model):
    __tablename__ = 'event_registrations'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    qr_code = db.Column(db.String(500))  # QR code data/URL
    attended = db.Column(db.Boolean, default=False)

    student = db.relationship('Student', backref=db.backref('event_registrations', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('event_id', 'student_id', name='uq_event_student'),)


class Feedback(db.Model):
    __tablename__ = 'feedbacks'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    category = db.Column(db.String(50), default='general')  # general, academic, infrastructure, faculty, other
    subject = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, resolved
    admin_response = db.Column(db.Text)
    responded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    responded_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref=db.backref('feedbacks', lazy='dynamic'))
    college = db.relationship('College')
    responder = db.relationship('User', foreign_keys=[responded_by])


class Grievance(db.Model):
    __tablename__ = 'grievances'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    category = db.Column(db.String(50), default='general')  # academic, hostel, ragging, discrimination, other
    subject = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, resolved, closed
    priority = db.Column(db.String(10), default='medium')  # low, medium, high, urgent
    resolution = db.Column(db.Text)
    resolved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref=db.backref('grievances', lazy='dynamic'))
    college = db.relationship('College')
    resolver = db.relationship('User', foreign_keys=[resolved_by])


class AntiRaggingUndertaking(db.Model):
    __tablename__ = 'anti_ragging_undertakings'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    reference_number = db.Column(db.String(100), unique=True)
    academic_year = db.Column(db.String(20))
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    parent_name = db.Column(db.String(200))
    parent_contact = db.Column(db.String(30))
    declaration_accepted = db.Column(db.Boolean, default=False)

    student = db.relationship('Student', backref=db.backref('anti_ragging_undertakings', lazy='dynamic'))
    college = db.relationship('College')


class LeaveApplication(db.Model):
    __tablename__ = 'leave_applications'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    leave_type = db.Column(db.String(30), nullable=False, default='od')  # od, sick, personal, family, other
    from_date = db.Column(db.Date, nullable=False)
    to_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    admin_remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref=db.backref('leave_applications', lazy='dynamic'))
    college = db.relationship('College')
    approver = db.relationship('User', foreign_keys=[approved_by])

    @property
    def duration_days(self):
        if self.from_date and self.to_date:
            return (self.to_date - self.from_date).days + 1
        return 0


class StudentDocument(db.Model):
    __tablename__ = 'student_documents'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    doc_type = db.Column(db.String(100), nullable=False)  # aadhar, marksheet_10, marksheet_12, tc, migration, photo, etc.
    doc_name = db.Column(db.String(300))
    file_url = db.Column(db.String(500))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    remarks = db.Column(db.Text)

    student = db.relationship('Student', backref=db.backref('documents', lazy='dynamic'))
    college = db.relationship('College')
    verifier = db.relationship('User', foreign_keys=[verified_by])


class CautionMoney(db.Model):
    __tablename__ = 'caution_money'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, paid, refunded, forfeited
    paid_at = db.Column(db.DateTime)
    refunded_at = db.Column(db.DateTime)
    refund_amount = db.Column(db.Float)
    transaction_ref = db.Column(db.String(100))
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    student = db.relationship('Student', backref=db.backref('caution_money_records', lazy='dynamic'))
    college = db.relationship('College')


# ==============================================================================
# ADMISSIONS & CRM MODULE
# ==============================================================================

class Enquiry(db.Model):
    __tablename__ = 'enquiries'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    student_name = db.Column(db.String(150), nullable=False)
    parent_name = db.Column(db.String(150))
    phone = db.Column(db.String(30), nullable=False)
    email = db.Column(db.String(120))
    target_class = db.Column(db.String(50))
    status = db.Column(db.String(20), default='New') # New, Follow-up, Closed, Registered
    source = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    follow_up_date = db.Column(db.DateTime)

    college = db.relationship('College')


class AdmissionApplication(db.Model):
    __tablename__ = 'admission_applications'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    enquiry_id = db.Column(db.Integer, db.ForeignKey('enquiries.id'), nullable=True)
    applicant_name = db.Column(db.String(150), nullable=False)
    target_class = db.Column(db.String(50))
    application_fee_status = db.Column(db.String(20), default='Pending') # Pending, Paid
    status = db.Column(db.String(20), default='Submitted') # Submitted, Under Review, Approved, Rejected, Enrolled
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    json_data = db.Column(db.Text) # For storing extensive application form data

    college = db.relationship('College')
    enquiry = db.relationship('Enquiry')


# ==============================================================================
# HR & STAFF MODULE
# ==============================================================================

class StaffProfile(db.Model):
    __tablename__ = 'staff_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    employee_code = db.Column(db.String(50), unique=True)
    department = db.Column(db.String(100))
    designation = db.Column(db.String(100))
    join_date = db.Column(db.Date)
    qualification = db.Column(db.String(200))
    experience_years = db.Column(db.Integer)
    base_salary = db.Column(db.Float)
    bank_account = db.Column(db.String(50))
    ifsc_code = db.Column(db.String(20))
    pan_number = db.Column(db.String(20))
    pf_number = db.Column(db.String(50))
    
    user = db.relationship('User', backref=db.backref('staff_profile', uselist=False))
    college = db.relationship('College')


class StaffAttendance(db.Model):
    __tablename__ = 'staff_attendance'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff_profiles.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(10)) # Present, Absent, Half-day, Leave
    clock_in = db.Column(db.Time)
    clock_out = db.Column(db.Time)
    remarks = db.Column(db.String(200))

    staff = db.relationship('StaffProfile', backref='attendance_records')
    college = db.relationship('College')


class PayrollTransaction(db.Model):
    __tablename__ = 'payroll_transactions'
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey('staff_profiles.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    month = db.Column(db.Integer) # 1-12
    year = db.Column(db.Integer)
    basic_pay = db.Column(db.Float)
    allowances = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    net_pay = db.Column(db.Float)
    status = db.Column(db.String(20), default='Pending') # Pending, Paid
    paid_at = db.Column(db.DateTime)
    
    staff = db.relationship('StaffProfile', backref='payroll_records')
    college = db.relationship('College')


# ==============================================================================
# INFRASTRUCTURE (LIBRARY, TRANSPORT, HOSTEL, INVENTORY)
# ==============================================================================

class LibraryBook(db.Model):
    __tablename__ = 'library_books'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    isbn = db.Column(db.String(20))
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(150))
    publisher = db.Column(db.String(150))
    category = db.Column(db.String(100))
    price = db.Column(db.Float)
    total_copies = db.Column(db.Integer, default=1)
    available_copies = db.Column(db.Integer, default=1)

    college = db.relationship('College')

class BookIssue(db.Model):
    __tablename__ = 'book_issues'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('library_books.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id')) # Student or Staff
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    return_date = db.Column(db.Date)
    fine_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Issued') # Issued, Returned, Overdue, Lost

    book = db.relationship('LibraryBook', backref='issues')
    user = db.relationship('User', backref='library_issues')
    college = db.relationship('College')


class TransportRoute(db.Model):
    __tablename__ = 'transport_routes'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    route_name = db.Column(db.String(100), nullable=False)
    vehicle_no = db.Column(db.String(50))
    driver_name = db.Column(db.String(100))
    driver_phone = db.Column(db.String(30))
    capacity = db.Column(db.Integer)
    monthly_fee = db.Column(db.Float)

    college = db.relationship('College')

class TransportAllocation(db.Model):
    __tablename__ = 'transport_allocations'
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('transport_routes.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    pickup_point = db.Column(db.String(150))
    allocated_at = db.Column(db.DateTime, default=datetime.utcnow)

    route = db.relationship('TransportRoute', backref='allocations')
    student = db.relationship('Student', backref='transport')
    college = db.relationship('College')


class HostelRoom(db.Model):
    __tablename__ = 'hostel_rooms'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    hostel_name = db.Column(db.String(100))
    room_number = db.Column(db.String(20), nullable=False)
    bed_capacity = db.Column(db.Integer, default=2)
    room_type = db.Column(db.String(50)) # AC, Non-AC
    monthly_fee = db.Column(db.Float)

    college = db.relationship('College')

class HostelAllocation(db.Model):
    __tablename__ = 'hostel_allocations'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('hostel_rooms.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    date_joined = db.Column(db.Date)
    date_vacated = db.Column(db.Date)
    status = db.Column(db.String(20), default='Occupied') # Occupied, Vacated

    room = db.relationship('HostelRoom', backref='allocations')
    student = db.relationship('Student', backref='hostel')
    college = db.relationship('College')


class InventoryCategory(db.Model):
    __tablename__ = 'inventory_categories'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    name = db.Column(db.String(100), nullable=False)

    college = db.relationship('College')

class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('inventory_categories.id'))
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    unit_price = db.Column(db.Float, default=0.0)
    reorder_level = db.Column(db.Integer, default=5)

    category = db.relationship('InventoryCategory', backref='items')
    college = db.relationship('College')

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    vendor_name = db.Column(db.String(150))
    total_amount = db.Column(db.Float)
    status = db.Column(db.String(30), default='Pending') # Pending, Received, Cancelled
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    items_json = db.Column(db.Text) # Storing item breakdown in JSON

    college = db.relationship('College')


# ==============================================================================
# ADVANCED FINANCE
# ==============================================================================

class FinancialLedger(db.Model):
    """General unified college ledger for income/expense outside of student fees."""
    __tablename__ = 'financial_ledger'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'))
    transaction_type = db.Column(db.String(10)) # INCOME, EXPENSE
    amount = db.Column(db.Float, nullable=False)
    party_name = db.Column(db.String(150))
    category = db.Column(db.String(100)) # e.g. Utility, Vendor Payment, Donation
    description = db.Column(db.Text)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_method = db.Column(db.String(50)) # Cash, Bank Transfer, Cheque
    reference_no = db.Column(db.String(100))

    college = db.relationship('College')


class AssetRecord(db.Model):
    """Purchased item record with physical location (Block, Floor, Corridor, Room, Dept)."""
    __tablename__ = 'asset_records'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), default='Furniture & Fixtures') # Furniture, IT, Lab, Electrical, Stationary, Plumbing, Maintenance
    quantity = db.Column(db.Integer, default=1)
    unit_cost = db.Column(db.Float, default=0.0)
    total_cost = db.Column(db.Float, default=0.0)
    purchase_date = db.Column(db.Date)
    vendor_name = db.Column(db.String(150))
    invoice_no = db.Column(db.String(100))
    warranty_expiry = db.Column(db.Date)

    # Physical Location Allocation Details
    block_name = db.Column(db.String(100))   # Block / Building name
    floor_level = db.Column(db.String(50))    # Floor level
    corridor_wing = db.Column(db.String(100)) # Corridor / Wing
    room_number = db.Column(db.String(100))   # Room / Lab / Hall No.
    department = db.Column(db.String(100))    # Department allocated to
    status = db.Column(db.String(50), default='In Use') # In Use, In Storage, Under Repair, Disposed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    college = db.relationship('College')

    def to_dict(self):
        return {
            'id': self.id,
            'item_name': self.item_name,
            'category': self.category,
            'quantity': self.quantity,
            'unit_cost': self.unit_cost,
            'total_cost': self.total_cost,
            'purchase_date': self.purchase_date.strftime('%Y-%m-%d') if self.purchase_date else '',
            'vendor_name': self.vendor_name or '',
            'invoice_no': self.invoice_no or '',
            'warranty_expiry': self.warranty_expiry.strftime('%Y-%m-%d') if self.warranty_expiry else '',
            'block_name': self.block_name or '',
            'floor_level': self.floor_level or '',
            'corridor_wing': self.corridor_wing or '',
            'room_number': self.room_number or '',
            'department': self.department or '',
            'status': self.status or 'In Use',
            'notes': self.notes or ''
        }


# ==============================================================================
# IT ADMINISTRATOR & OPERATIONS
# ==============================================================================

class AuditLog(db.Model):
    """Centralized security & system audit log for tracking access and modifications."""
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False) # e.g. LOGIN_SUCCESS, USER_CREATED, ROLE_UPDATED, FEATURE_FLAG_TOGGLED
    module = db.Column(db.String(50), default='System') # Security, Auth, Finance, Academics, Admin
    ip_address = db.Column(db.String(45))
    details = db.Column(db.Text)
    severity = db.Column(db.String(20), default='info') # info, warning, danger
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    college = db.relationship('College')
    user = db.relationship('User', foreign_keys=[user_id])


class FeatureFlag(db.Model):
    """Configuration-driven feature toggles per institution/college."""
    __tablename__ = 'feature_flags'
    id = db.Column(db.Integer, primary_key=True)
    college_id = db.Column(db.Integer, db.ForeignKey('colleges.id'), nullable=False)
    feature_key = db.Column(db.String(100), nullable=False) # e.g. ai_assistant, digital_wallet, lms_sync, early_warning, pwa_offline
    name = db.Column(db.String(150), nullable=False)
    is_enabled = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    college = db.relationship('College')



