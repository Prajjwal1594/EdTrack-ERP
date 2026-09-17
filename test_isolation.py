import sys
import os

base_dir = os.path.abspath(os.path.dirname(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app import create_app, db
from app.models import User, College, Student, Exam, FeePayment, TransportRoute, HostelRoom, LibraryBook, BookIssue, AuditLog, Subject

app = create_app()
app.config['WTF_CSRF_ENABLED'] = False
app.config['TESTING'] = True

passed = 0
failed = 0

def test_assert(name, condition, extra=None):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name} | Extra: {extra}")
        failed += 1

with app.app_context():
    client = app.test_client()
    
    college1 = College.query.filter_by(code='EWIU').first()
    college2 = College.query.filter_by(code='SRA').first()
    
    print(f"\n--- Testing Colleges: College 1 ({college1.name if college1 else None}) | College 2 ({college2.name if college2 else None}) ---")
    
    # 1. Test IT Admin Sessions & Logs Isolation
    itadmin1 = User.query.filter_by(email='itadmin@gmail.com').first()
    if itadmin1:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(itadmin1.id)
            sess['_fresh'] = True
        
        resp = client.get('/it-admin/sessions')
        test_assert("IT Admin 1 cannot see College 2 users in sessions", 
                    b'admin2@sunrise.edu' not in resp.data and b'student2@sunrise.edu' not in resp.data)
        test_assert("IT Admin 1 sees College 1 users in sessions",
                    b'admin@gmail.com' in resp.data or b'itadmin@gmail.com' in resp.data)
        
        resp_logs = client.get('/it-admin/audit-logs')
        test_assert("IT Admin 1 audit logs status code 200", resp_logs.status_code == 200)

    # 2. Test Admin Cross-Tenant User Editing / Deleting
    admin1 = User.query.filter_by(email='admin@gmail.com').first()
    user2 = User.query.filter_by(email='admin2@sunrise.edu').first()
    if admin1 and user2:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin1.id)
            sess['_fresh'] = True
        
        resp = client.get(f'/admin/users/{user2.id}/edit')
        test_assert("Admin 1 GET edit user of College 2 returns 404", resp.status_code == 404)
        
        resp_post = client.post(f'/admin/users/{user2.id}/delete')
        test_assert("Admin 1 POST delete user of College 2 returns 404", resp_post.status_code == 404)

    # 3. Test Fee Cross-Tenant Access
    accountant1 = User.query.filter_by(email='accountant@gmail.com').first()
    # Find a payment for college 2
    student2 = Student.query.join(User).filter(User.college_id == college2.id).first() if college2 else None
    payment2 = FeePayment.query.filter_by(student_id=student2.id).first() if student2 else None
    if accountant1 and payment2:
        with client.session_transaction() as sess:
            sess['_user_id'] = str(accountant1.id)
            sess['_fresh'] = True
            
        resp = client.get(f'/fees/receipt/{payment2.id}')
        test_assert("Accountant 1 GET receipt of College 2 student returns 404", resp.status_code == 404)
        
        resp = client.post(f'/fees/pay/{payment2.id}')
        test_assert("Accountant 1 POST pay fee of College 2 returns 404", resp.status_code == 404)

    # 4. Test Infrastructure Isolation
    route2 = TransportRoute.query.filter_by(college_id=college2.id).first() if college2 else None
    if not route2 and college2:
        route2 = TransportRoute(college_id=college2.id, route_name="Sunrise Express", vehicle_no="SRA-1", capacity=30, monthly_fee=100)
        db.session.add(route2)
        db.session.commit()
        
    client.post('/login', data={'email': 'transport@gmail.com', 'password': 'transport123'})
    resp = client.get(f'/infra/transport/delete/{route2.id}')
    test_assert("Transport Manager 1 delete College 2 route returns 404", resp.status_code == 404, extra=(resp.status_code, resp.headers))

    # 5. Test Library Isolation
    book2 = LibraryBook.query.filter_by(college_id=college2.id).first()
    if not book2 and college2:
        book2 = LibraryBook(college_id=college2.id, title="Sunrise Physics", author="Sunrise Author", total_copies=5, available_copies=5)
        db.session.add(book2)
        db.session.commit()
    
    client.post('/login', data={'email': 'librarian@gmail.com', 'password': 'librarian123'})
    resp = client.post(f'/infra/library/delete/{book2.id}')
    test_assert("Librarian 1 delete College 2 book returns 404", resp.status_code == 404, extra=(resp.status_code, resp.headers))

    # 6. Test Messaging Isolation
    client.post('/login', data={'email': 'student@gmail.com', 'password': 'student123'})
    resp = client.post('/messages/compose', data={
        'recipient_id': user2.id,
        'subject': 'Cross tenant test',
        'body': 'Hello other school'
    }, follow_redirects=True)
    test_assert("Student 1 composing message to College 2 user rejected", 
                b'Recipient not found' in resp.data or b'Invalid recipient' in resp.data or b'Access denied' in resp.data,
                extra=(resp.status_code, resp.data[:150]))

    # 7. Test Exam Isolation
    subj2 = Subject.query.filter_by(college_id=college2.id).first() if college2 else None
    exam2 = None
    if subj2:
        exam2 = Exam.query.filter_by(subject_id=subj2.id).first()
        if not exam2:
            exam2 = Exam(subject_id=subj2.id, title="Sunrise Final Exam", total_marks=100, duration_minutes=60, is_published=True)
            db.session.add(exam2)
            db.session.commit()
        
    if exam2:
        client.post('/login', data={'email': 'student@gmail.com', 'password': 'student123'})
        resp = client.get(f'/exams/{exam2.id}/take')
        test_assert("Student 1 accessing College 2 exam returns 404", resp.status_code == 404, extra=resp.status_code)

    # 8. Test Quick Role Views
    client.post('/login', data={'email': 'hod@gmail.com', 'password': 'hod123'})
    resp = client.get('/hod/department-workload')
    test_assert("HOD workload returns 200 and no Sunrise data", resp.status_code == 200 and b'Sunrise' not in resp.data)

    client.post('/login', data={'email': 'admissions@gmail.com', 'password': 'admissions123'})
    resp = client.get('/admissions/merit-list')
    test_assert("Admissions merit-list returns 200 and no Sunrise data", resp.status_code == 200 and b'Sunrise' not in resp.data)

print(f"\n==========================================")
print(f"Results: {passed} PASSED, {failed} FAILED")
print(f"==========================================")
if failed > 0:
    sys.exit(1)

