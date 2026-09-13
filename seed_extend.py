"""
seed_extend.py  – Extends existing seeded data with all missing tables:
  - Courses, Streams, Batches (link to sections & students)
  - Library Books + Book Issues
  - Timetable Slots (Mon-Fri schedule)
  - Announcements (noticeboard)
  - Messages (internal)
  - Exams (midterm/final)
  - Parent-Student Links for all parents
  - Fee payments for more students

Run: python seed_extend.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db
from app.models import (
    College, User, Semester, Section, Subject, FacultyAssignment,
    Student, ParentStudentLink, AcademicTerm, Grade, Attendance,
    FeeType, FeePayment, TimetableSlot, Announcement, Event, Message,
    LibraryBook, BookIssue, Exam, ExamQuestion, Course, Stream, Batch
)
from datetime import date, datetime, timedelta, time
import random


def extend_seed():
    app = create_app()
    with app.app_context():
        random.seed(42)

        college1 = College.query.filter_by(code='EWIU').first()
        college2 = College.query.filter_by(code='SRA').first()

        if not college1:
            print("ERROR: College 1 (EWIU) not found. Run python seed.py first.")
            return

        admin1 = User.query.filter_by(email='admin@gmail.com').first()
        faculty1_list = User.query.filter_by(role='faculty', college_id=college1.id).all()
        librarian1 = User.query.filter_by(email='librarian@gmail.com').first()
        parent1 = User.query.filter_by(email='parent@gmail.com').first()

        # ── 1. COURSES ────────────────────────────────────────────────────────
        print("Seeding Courses...")
        if Course.query.filter_by(college_id=college1.id).count() == 0:
            courses_data = [
                ("Bachelor of Technology (Computer Science)", "BTECH-CS"),
                ("Bachelor of Technology (Electronics)", "BTECH-EC"),
                ("Bachelor of Computer Applications", "BCA"),
                ("Master of Business Administration", "MBA"),
                ("Bachelor of Science (Physics)", "BSC-PHY"),
            ]
            courses1 = []
            for name, code in courses_data:
                c = Course(college_id=college1.id, name=name, code=code)
                db.session.add(c)
                courses1.append(c)
            db.session.flush()

            # Streams under BTECH-CS
            streams_data = [
                ("AI & Machine Learning", "AIML", courses1[0].id),
                ("Cybersecurity", "CS-SEC", courses1[0].id),
                ("Data Science", "DS", courses1[0].id),
            ]
            streams1 = []
            for name, code, cid in streams_data:
                s = Stream(college_id=college1.id, course_id=cid, name=name, code=code)
                db.session.add(s)
                streams1.append(s)
            db.session.flush()

            # Batch 2024-2028
            batch1 = Batch(college_id=college1.id, name="Batch 2024-2028", start_year=2024, end_year=2028)
            db.session.add(batch1)
            batch2 = Batch(college_id=college1.id, name="Batch 2023-2027", start_year=2023, end_year=2027)
            db.session.add(batch2)
            db.session.flush()

            # Link sections to course/stream/batch
            sections1 = Section.query.join(Semester).filter(Semester.college_id == college1.id).all()
            for i, sec in enumerate(sections1):
                sec.course_id = courses1[i % len(courses1)].id
                sec.stream_id = streams1[i % len(streams1)].id
                sec.batch_id = batch1.id if i % 2 == 0 else batch2.id
                if faculty1_list:
                    sec.batch_counselor_id = faculty1_list[i % len(faculty1_list)].id

            # Link students to course/stream/batch
            students1 = Student.query.join(User).filter(User.college_id == college1.id).all()
            for i, s in enumerate(students1):
                s.course_id = courses1[i % len(courses1)].id
                s.stream_id = streams1[i % len(streams1)].id
                s.batch_id = batch1.id if i % 2 == 0 else batch2.id
                s.roll_number = f"EW{s.enrollment_number[-5:]}" if s.enrollment_number else f"EW{i+1:04d}"
                s.session = "2024-2025"
                s.father_name = f"Mr. {['Ramesh', 'Suresh', 'Rajesh', 'Mahesh', 'Ganesh'][i % 5]} {s.user.name.split()[-1]}"
                s.mother_name = f"Mrs. {['Rekha', 'Seema', 'Priya', 'Anita', 'Kavita'][i % 5]} {s.user.name.split()[-1]}"
                s.blood_group = random.choice(['A+', 'B+', 'O+', 'AB+', 'A-'])
                s.state = random.choice(['Maharashtra', 'Delhi', 'Gujarat', 'Karnataka', 'Punjab'])
                s.country = 'India'
                s.admission_category = random.choice(['General', 'OBC', 'SC', 'Management'])
                if not s.enrollment_date:
                    s.enrollment_date = date(2024, 7, 1)

            db.session.flush()
            print(f"  Created {len(courses1)} courses, {len(streams1)} streams, 2 batches")

        # ── 2. TIMETABLE ─────────────────────────────────────────────────────
        print("Seeding Timetable Slots...")
        if TimetableSlot.query.filter_by(college_id=college1.id).count() == 0:
            sections1 = Section.query.join(Semester).filter(Semester.college_id == college1.id).limit(8).all()
            subjects1 = Subject.query.filter_by(college_id=college1.id).all()
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            periods = [
                (time(9, 0), time(9, 55)),
                (time(10, 0), time(10, 55)),
                (time(11, 10), time(12, 5)),
                (time(12, 10), time(13, 5)),
                (time(14, 0), time(14, 55)),
                (time(15, 0), time(15, 55)),
            ]
            rooms = ['101', '102', '103', '104', '201', '202', 'Lab-A', 'Lab-B']

            count = 0
            for sec in sections1[:6]:
                fac_assignments = FacultyAssignment.query.filter_by(section_id=sec.id).all()
                if not fac_assignments:
                    continue
                for day in days:
                    for period_idx, (start, end) in enumerate(periods[:5]):
                        fa = fac_assignments[period_idx % len(fac_assignments)]
                        slot = TimetableSlot(
                            college_id=college1.id,
                            section_id=sec.id,
                            subject_id=fa.subject_id,
                            faculty_id=fa.faculty_id,
                            day_of_week=day,
                            start_time=start,
                            end_time=end,
                            room_number=rooms[count % len(rooms)]
                        )
                        db.session.add(slot)
                        count += 1
            db.session.flush()
            print(f"  Created {count} timetable slots")

            # College 2 timetable
            if college2:
                sections2 = Section.query.join(Semester).filter(Semester.college_id == college2.id).limit(4).all()
                subjects2 = Subject.query.filter_by(college_id=college2.id).all()
                faculty2_list = User.query.filter_by(role='faculty', college_id=college2.id).all()
                fac_assigns2 = FacultyAssignment.query.filter(
                    FacultyAssignment.faculty_id.in_([f.id for f in faculty2_list])
                ).all()
                c2 = 0
                for sec in sections2[:3]:
                    fa_list2 = [fa for fa in fac_assigns2 if fa.section_id == sec.id]
                    if not fa_list2:
                        continue
                    for day in days:
                        for period_idx, (start, end) in enumerate(periods[:4]):
                            fa = fa_list2[period_idx % len(fa_list2)]
                            db.session.add(TimetableSlot(
                                college_id=college2.id,
                                section_id=sec.id,
                                subject_id=fa.subject_id,
                                faculty_id=fa.faculty_id,
                                day_of_week=day,
                                start_time=start,
                                end_time=end,
                                room_number=f"R{100 + c2 % 10}"
                            ))
                            c2 += 1
                db.session.flush()
                print(f"  College 2: Created {c2} timetable slots")

        # ── 3. ANNOUNCEMENTS / NOTICEBOARD ───────────────────────────────────
        print("Seeding Announcements...")
        if Announcement.query.filter_by(college_id=college1.id).count() == 0:
            today = date.today()
            announcements = [
                (college1.id, "Mid-Term Examinations Schedule", "Mid-term examinations will be conducted from 15th to 22nd of this month. All students are requested to check the detailed schedule on the notice board. No leave will be granted during this period.", "notice", today + timedelta(days=5), admin1.id if admin1 else None),
                (college1.id, "Annual Sports Day 2024-25", "The Annual Sports Day will be held on 25th September in the main ground. Students interested in participating must register with the Sports Department by 18th September. Events include 100m sprint, long jump, shot put, and team sports.", "event", today + timedelta(days=12), admin1.id if admin1 else None),
                (college1.id, "Fee Payment Deadline — Term 2", "All students are reminded that the last date for Term 2 fee payment is 30th September. Students with pending fees will not be allowed to appear in examinations. Contact the accounts office for payment plans.", "notice", today + timedelta(days=3), admin1.id if admin1 else None),
                (college1.id, "National Holiday — Gandhi Jayanti", "The college will remain closed on 2nd October on account of Gandhi Jayanti. Regular classes will resume on 3rd October. A special lecture series on Gandhian values will be held on 1st October.", "holiday", today + timedelta(days=8), admin1.id if admin1 else None),
                (college1.id, "Library New Arrivals — October 2024", "The central library has added 50+ new titles in Computer Science, Business Management, and Engineering. Students can view the new arrivals at the library desk. Online reservation available through the ERP portal.", "notice", today, admin1.id if admin1 else None),
                (college1.id, "Placement Drive — TechCorp Solutions", "TechCorp Solutions is visiting campus on 10th October for placements. Eligible students (CGPA ≥ 7.0, no active backlogs) must register through the Placement Cell by 5th October. Package: 8.5 LPA.", "event", today + timedelta(days=15), admin1.id if admin1 else None),
                (college1.id, "Internal Assessment Marks Published", "Internal assessment marks for Term 1 have been published on the ERP portal. Students who wish to apply for re-checking must do so within 5 working days. Contact your subject teacher for details.", "notice", today - timedelta(days=2), admin1.id if admin1 else None),
                (college1.id, "Convocation Ceremony 2024", "The Annual Convocation Ceremony will be held on 15th November for the graduating batch of 2024. Final year students must collect their convocation forms from the Registrar's office.", "event", today + timedelta(days=45), admin1.id if admin1 else None),
            ]
            for college_id, title, body, atype, adate, creator in announcements:
                db.session.add(Announcement(
                    college_id=college_id, title=title, body=body,
                    announcement_type=atype, date=adate,
                    created_by=creator, is_active=True
                ))

            # College 2 announcements
            if college2:
                admin2 = User.query.filter_by(email='admin2@sunrise.edu').first()
                db.session.add(Announcement(
                    college_id=college2.id,
                    title="Welcome to Sunrise Academy — New Academic Year",
                    body="We warmly welcome all students to the new academic year 2024-2025. Classes begin from 1st August. Orientation programme scheduled for 29-30 July.",
                    announcement_type='notice', date=today - timedelta(days=5),
                    created_by=admin2.id if admin2 else None, is_active=True
                ))
                db.session.add(Announcement(
                    college_id=college2.id,
                    title="Sunrise Academy — Hackathon 2024",
                    body="Annual Hackathon on 20th October. Teams of 3-4 students. Prize pool: ₹50,000. Register by 10th October via the student portal.",
                    announcement_type='event', date=today + timedelta(days=20),
                    created_by=admin2.id if admin2 else None, is_active=True
                ))
            db.session.flush()
            print(f"  Created {len(announcements)} announcements")

        # ── 4. LIBRARY BOOKS ─────────────────────────────────────────────────
        print("Seeding Library Books...")
        if LibraryBook.query.filter_by(college_id=college1.id).count() == 0:
            books_data = [
                # Computer Science
                ("978-0262033848", "Introduction to Algorithms", "Thomas H. Cormen", "MIT Press", "Computer Science", 850.0, 5),
                ("978-0134685991", "Effective Java", "Joshua Bloch", "Addison-Wesley", "Computer Science", 620.0, 3),
                ("978-0596517748", "JavaScript: The Good Parts", "Douglas Crockford", "O'Reilly", "Computer Science", 480.0, 4),
                ("978-0201633610", "Design Patterns", "Gang of Four", "Addison-Wesley", "Computer Science", 720.0, 3),
                ("978-1491910771", "Python Data Science Handbook", "Jake VanderPlas", "O'Reilly", "Data Science", 750.0, 4),
                ("978-0135957059", "Clean Code", "Robert C. Martin", "Prentice Hall", "Computer Science", 550.0, 5),
                ("978-1119292333", "Machine Learning for Dummies", "John Paul Mueller", "Wiley", "AI/ML", 690.0, 3),
                # Mathematics
                ("978-0471321927", "Linear Algebra and Its Applications", "David Lay", "Pearson", "Mathematics", 890.0, 4),
                ("978-0131919631", "Discrete Mathematics", "Kenneth Rosen", "McGraw-Hill", "Mathematics", 780.0, 5),
                ("978-0321797056", "Calculus: Early Transcendentals", "James Stewart", "Cengage", "Mathematics", 920.0, 3),
                # Engineering
                ("978-0133919202", "Engineering Mechanics: Dynamics", "Russell Hibbeler", "Pearson", "Engineering", 845.0, 3),
                ("978-0073529554", "Fundamentals of Electric Circuits", "Charles Alexander", "McGraw-Hill", "Electrical Eng.", 760.0, 4),
                ("978-0131989313", "Digital Design", "M. Morris Mano", "Pearson", "Electronics", 680.0, 4),
                # Management
                ("978-0135210408", "Management: A Practical Introduction", "Angelo Kinicki", "McGraw-Hill", "Management", 640.0, 3),
                ("978-0134729329", "Marketing Management", "Philip Kotler", "Pearson", "Business", 870.0, 3),
                # General / Science
                ("978-0684801223", "A Brief History of Time", "Stephen Hawking", "Bantam Books", "Science", 350.0, 6),
                ("978-0385737951", "The Fault in Our Stars", "John Green", "Dutton", "Fiction", 280.0, 5),
                ("978-0743273565", "The Great Gatsby", "F. Scott Fitzgerald", "Scribner", "Literature", 320.0, 4),
                ("978-0061965012", "Rich Dad Poor Dad", "Robert Kiyosaki", "Plata Publishing", "Finance", 290.0, 7),
                ("978-0062316097", "Sapiens", "Yuval Noah Harari", "Harper Collins", "History", 420.0, 5),
                # Research
                ("978-0226543154", "The Chicago Manual of Style", "University of Chicago", "Univ. Chicago Press", "Reference", 950.0, 2),
                ("978-1462523450", "Research Methods in Education", "Louis Cohen", "Routledge", "Research", 780.0, 3),
                ("978-0205900404", "Publication Manual of APA", "APA", "APA Publishing", "Reference", 580.0, 4),
            ]

            shelf_locations = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2', 'D1', 'D2']
            books1 = []
            for i, (isbn, title, author, publisher, category, price, copies) in enumerate(books_data):
                b = LibraryBook(
                    college_id=college1.id, isbn=isbn, title=title, author=author,
                    publisher=publisher, category=category, price=price,
                    total_copies=copies, available_copies=copies - random.randint(0, min(2, copies - 1))
                )
                db.session.add(b)
                books1.append(b)

            db.session.flush()
            print(f"  Created {len(books1)} library books")

            # Book Issues — some books currently issued to students
            students1 = Student.query.join(User).filter(User.college_id == college1.id).all()
            issue_count = 0
            for i, student in enumerate(students1[:8]):
                if i < len(books1):
                    book = books1[i % len(books1)]
                    if book.available_copies > 0:
                        issue_date = date.today() - timedelta(days=random.randint(3, 14))
                        due_date = issue_date + timedelta(days=14)
                        status = 'issued' if due_date >= date.today() else 'overdue'
                        db.session.add(BookIssue(
                            book_id=book.id,
                            user_id=student.user_id,
                            college_id=college1.id,
                            issue_date=issue_date,
                            due_date=due_date,
                            status=status
                        ))
                        book.available_copies -= 1
                        issue_count += 1
            db.session.flush()
            print(f"  Created {issue_count} book issues")

        # ── 5. EXAMS ─────────────────────────────────────────────────────────
        print("Seeding Exams...")
        if Exam.query.count() == 0:
            subjects1 = Subject.query.filter_by(college_id=college1.id).all()
            sections1 = Section.query.join(Semester).filter(Semester.college_id == college1.id).limit(4).all()
            faculty1_user = User.query.filter_by(email='faculty@gmail.com').first()
            creator_id = faculty1_user.id if faculty1_user else (admin1.id if admin1 else 1)

            exam_count = 0
            for sec in sections1[:2]:
                for subj in subjects1[:3]:
                    # Mid-term exam
                    mid_exam = Exam(
                        title=f"Mid-Term — {subj.name}",
                        subject_id=subj.id,
                        section_id=sec.id,
                        description=f"Mid-term examination for {subj.name}. Covers Units 1-3.",
                        duration_minutes=90,
                        start_time=datetime.now() + timedelta(days=random.randint(7, 15)),
                        total_marks=50,
                        is_published=True,
                        created_by=creator_id
                    )
                    db.session.add(mid_exam)
                    db.session.flush()

                    # Add questions
                    questions = [
                        ("What is the time complexity of Binary Search?", "mcq",
                         ["O(n)", "O(log n)", "O(n²)", "O(1)"], "O(log n)", 5),
                        ("Explain the concept of recursion.", "short_answer", [], "recursion definition", 10),
                        ("Which data structure uses LIFO principle?", "mcq",
                         ["Queue", "Stack", "Tree", "Graph"], "Stack", 5),
                    ]
                    for qtext, qtype, options, correct, marks in questions:
                        import json
                        q = ExamQuestion(
                            exam_id=mid_exam.id,
                            question_text=qtext,
                            question_type=qtype,
                            options=options,
                            correct_answer=correct,
                            marks=marks
                        )
                        db.session.add(q)

                    # Final exam (upcoming)
                    final_exam = Exam(
                        title=f"Final Examination — {subj.name}",
                        subject_id=subj.id,
                        section_id=sec.id,
                        description=f"Final examination for {subj.name}. Covers entire syllabus.",
                        duration_minutes=180,
                        start_time=datetime.now() + timedelta(days=random.randint(45, 60)),
                        total_marks=100,
                        is_published=False,
                        created_by=creator_id
                    )
                    db.session.add(final_exam)
                    exam_count += 2

            db.session.flush()
            print(f"  Created {exam_count} exams")

        # ── 6. MESSAGES ──────────────────────────────────────────────────────
        print("Seeding Messages...")
        if Message.query.count() == 0:
            faculty1_user = User.query.filter_by(email='faculty@gmail.com').first()
            student_user = User.query.filter_by(email='student@gmail.com').first()
            parent_user = User.query.filter_by(email='parent@gmail.com').first()

            sample_messages = []
            if admin1 and faculty1_user:
                sample_messages.append(Message(
                    sender_id=admin1.id,
                    recipient_id=faculty1_user.id,
                    subject="Faculty Meeting — This Friday",
                    body="Dear Faculty,\n\nPlease be informed that there will be a faculty meeting this Friday at 4:00 PM in the Conference Room. Attendance is mandatory. Agenda: Mid-term results review and curriculum updates.\n\nRegards,\nDr. Margaret Wells\nInstitution Admin",
                    sent_at=datetime.now() - timedelta(hours=6)
                ))

            if faculty1_user and student_user:
                sample_messages.append(Message(
                    sender_id=faculty1_user.id,
                    recipient_id=student_user.id,
                    subject="Assignment Deadline Reminder",
                    body="Dear Alex,\n\nThis is a reminder that your Mathematics assignment is due this Friday. Please ensure you submit it via the ERP portal before 11:59 PM. Late submissions will incur a 10% penalty.\n\nBest regards,\nMr. James Harrison\nFaculty - Mathematics",
                    sent_at=datetime.now() - timedelta(hours=2)
                ))

            if admin1 and parent_user:
                sample_messages.append(Message(
                    sender_id=admin1.id,
                    recipient_id=parent_user.id,
                    subject="Parent-Teacher Meeting — 20th September",
                    body="Dear Parent/Guardian,\n\nYou are cordially invited to the Parent-Teacher Meeting scheduled for 20th September at 10:00 AM in the school auditorium.\n\nThis is an excellent opportunity to discuss your child's academic progress and address any concerns.\n\nRegards,\nDr. Margaret Wells",
                    sent_at=datetime.now() - timedelta(days=1)
                ))

            if student_user and faculty1_user:
                sample_messages.append(Message(
                    sender_id=student_user.id,
                    recipient_id=faculty1_user.id,
                    subject="Doubt Regarding Assignment Question 3",
                    body="Respected Sir,\n\nI have a doubt regarding Question 3 of the current assignment on Dynamic Programming. Could you please clarify whether we need to use memoization or tabulation approach?\n\nThank you,\nAlex Johnson",
                    sent_at=datetime.now() - timedelta(minutes=45)
                ))

            if parent_user and admin1:
                sample_messages.append(Message(
                    sender_id=parent_user.id,
                    recipient_id=admin1.id,
                    subject="Enquiry About Fee Payment Options",
                    body="Dear Administration,\n\nI would like to enquire about the fee payment options available for Term 2. Are there any installment plans available? Also, I noticed there's an option for online payment — is it safe and secure?\n\nThank you,\nRobert Johnson\n(Parent of Alex Johnson)",
                    sent_at=datetime.now() - timedelta(hours=3)
                ))

            for msg in sample_messages:
                db.session.add(msg)
            db.session.flush()
            print(f"  Created {len(sample_messages)} messages")

        # ── 7. PARENT–STUDENT LINKS ──────────────────────────────────────────
        print("Seeding Parent-Student Links...")
        all_parents = User.query.filter_by(role='parent', college_id=college1.id).all()
        all_students1 = Student.query.join(User).filter(User.college_id == college1.id).all()
        existing_links = {(l.parent_id, l.student_id) for l in ParentStudentLink.query.all()}

        new_links = 0
        if len(all_parents) > 0 and len(all_students1) > 1:
            for i, parent in enumerate(all_parents):
                # Assign 1-2 students to each parent
                for j in range(min(2, len(all_students1))):
                    student_idx = (i * 2 + j) % len(all_students1)
                    sid = all_students1[student_idx].id
                    if (parent.id, sid) not in existing_links:
                        rel = 'father' if j == 0 else 'mother'
                        db.session.add(ParentStudentLink(
                            parent_id=parent.id, student_id=sid, relationship_type=rel
                        ))
                        existing_links.add((parent.id, sid))
                        new_links += 1
        db.session.flush()
        print(f"  Created {new_links} parent-student links")

        # ── 8. MORE FEE PAYMENTS (more students) ────────────────────────────
        print("Seeding additional Fee Payments...")
        fee_types1 = FeeType.query.filter_by(college_id=college1.id).all()
        terms1 = AcademicTerm.query.filter_by(college_id=college1.id).all()
        students1 = Student.query.join(User).filter(User.college_id == college1.id).all()

        existing_payments = set(
            (p.student_id, p.fee_type_id, p.term_id)
            for p in FeePayment.query.all()
        )

        pay_count = 0
        if fee_types1 and terms1:
            for student in students1:
                for ft in fee_types1[:3]:
                    for term in terms1[:2]:
                        if (student.id, ft.id, term.id) not in existing_payments:
                            status = random.choices(['paid', 'paid', 'pending', 'overdue'], weights=[60, 20, 15, 5])[0]
                            db.session.add(FeePayment(
                                student_id=student.id,
                                fee_type_id=ft.id,
                                term_id=term.id,
                                amount=ft.amount,
                                due_date=term.start_date + timedelta(days=15),
                                status=status,
                                paid_at=datetime.utcnow() - timedelta(days=random.randint(1, 60)) if status == 'paid' else None,
                                payment_method=random.choice(['cash', 'online', 'bank_transfer']) if status == 'paid' else None,
                                recorded_by=admin1.id if admin1 else None
                            ))
                            existing_payments.add((student.id, ft.id, term.id))
                            pay_count += 1
        db.session.flush()
        print(f"  Created {pay_count} additional fee payment records")

        # ── 9. STANDARD DEMO ACCOUNTS (cj / cj credentials) ───────────────────
        print("Seeding requested standard user accounts (cj / cj)...")
        demo_accounts = [
            ("College Admin", "admin@admin.com", "admin", college1.id),
            ("Lead Teacher", "teacher@teacher.com", "faculty", college1.id),
            ("Chief Accountant", "accountant@accountant.com", "accountant", college1.id),
            ("Head Librarian", "librarian@librarian.com", "librarian", college1.id),
            ("Alex Student", "student@student.com", "student", college1.id),
            ("Robert Parent", "parent@parent.com", "parent", college1.id),
        ]
        created_users = {}
        for name, email, role, cid in demo_accounts:
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(name=name, email=email, role=role, college_id=cid)
                u.set_password("cj")
                db.session.add(u)
                db.session.flush()
            created_users[role] = u

        # Ensure student profile for student@student.com
        std_user = created_users.get('student')
        if std_user and not Student.query.filter_by(user_id=std_user.id).first():
            sec = Section.query.join(Semester).filter(Semester.college_id == college1.id).first()
            crs = Course.query.filter_by(college_id=college1.id).first()
            s_obj = Student(
                user_id=std_user.id,
                section_id=sec.id if sec else None,
                course_id=crs.id if crs else None,
                roll_number="CJ202401",
                enrollment_number="ENR-CJ001",
                date_of_birth=date(2005, 5, 15),
                gender="Male",
                enrollment_date=date(2024, 7, 1)
            )
            db.session.add(s_obj)
            db.session.flush()

            # Link parent@parent.com to this student
            p_user = created_users.get('parent')
            if p_user:
                if not ParentStudentLink.query.filter_by(parent_id=p_user.id, student_id=s_obj.id).first():
                    db.session.add(ParentStudentLink(parent_id=p_user.id, student_id=s_obj.id, relationship_type='father'))

            # Also link parent to student 1 (Alex Johnson) for richer data
            alex = Student.query.filter_by(id=1).first()
            if p_user and alex and not ParentStudentLink.query.filter_by(parent_id=p_user.id, student_id=alex.id).first():
                db.session.add(ParentStudentLink(parent_id=p_user.id, student_id=alex.id, relationship_type='guardian'))

            # Give student attendance records
            t_user = created_users.get('faculty')
            for d_off in range(20):
                att_d = date.today() - timedelta(days=d_off)
                if att_d.weekday() < 5 and not Attendance.query.filter_by(student_id=s_obj.id, date=att_d).first():
                    db.session.add(Attendance(
                        student_id=s_obj.id, section_id=s_obj.section_id,
                        date=att_d, status='present' if d_off % 7 != 0 else 'absent',
                        marked_by=t_user.id if t_user else admin1.id
                    ))

            # Give student fee payments
            fts = FeeType.query.filter_by(college_id=college1.id).limit(2).all()
            tms = AcademicTerm.query.filter_by(college_id=college1.id).limit(1).all()
            if fts and tms:
                for ft in fts:
                    db.session.add(FeePayment(
                        student_id=s_obj.id, fee_type_id=ft.id, term_id=tms[0].id,
                        amount=ft.amount, due_date=date.today() + timedelta(days=10),
                        status='paid', paid_at=datetime.utcnow() - timedelta(days=3),
                        payment_method='online'
                    ))

        # Ensure teacher has FacultyAssignment
        t_user = created_users.get('faculty')
        if t_user and not FacultyAssignment.query.filter_by(faculty_id=t_user.id).first():
            sec = Section.query.join(Semester).filter(Semester.college_id == college1.id).first()
            subj = Subject.query.filter_by(college_id=college1.id).first()
            if sec and subj:
                db.session.add(FacultyAssignment(
                    faculty_id=t_user.id, subject_id=subj.id, section_id=sec.id, academic_year="2024-2025"
                ))

        db.session.commit()
        print("\n[SUCCESS] Extension seeding complete!")
        print("-" * 50)

        # Verify counts
        from app.models import TimetableSlot as TS, LibraryBook as LB, Announcement as AN, Exam as EX
        print(f"  Courses       : {Course.query.count()}")
        print(f"  Timetable     : {TS.query.count()} slots")
        print(f"  Announcements : {AN.query.count()}")
        print(f"  Library Books : {LB.query.count()}")
        print(f"  Exams         : {EX.query.count()}")
        print(f"  Messages      : {Message.query.count()}")
        print(f"  Parent Links  : {ParentStudentLink.query.count()}")
        print(f"  Fee Payments  : {FeePayment.query.count()}")


if __name__ == "__main__":
    extend_seed()
