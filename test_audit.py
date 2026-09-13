import sys
from app import create_app, db
from app.models import User

def run_audit():
    app = create_app()
    client = app.test_client()

    accounts_to_test = [
        ("Super Admin (Original)", "superadmin@edtrack.com", "super123", [
            "/superadmin/dashboard",
            "/superadmin/colleges",
        ]),
        ("Admin (CJ)", "admin@admin.com", "cj", [
            "/admin/dashboard",
            "/admin/users",
            "/admin/students",
            "/admin/noticeboard",
            "/admissions/",
            "/fees/",
            "/messages/inbox",
        ]),
        ("Teacher (CJ)", "teacher@teacher.com", "cj", [
            "/faculty/dashboard",
            "/faculty/students",
            "/faculty/timetable",
            "/faculty/grades",
            "/faculty/attendance",
            "/messages/inbox",
        ]),
        ("Student (CJ)", "student@student.com", "cj", [
            "/student/dashboard",
            "/student/timetable",
            "/student/library",
            "/student/subjects",
            "/student/assignments",
            "/student/grades",
            "/messages/inbox",
        ]),
        ("Parent (CJ)", "parent@parent.com", "cj", [
            "/parent/dashboard",
            "/parent/children",
            "/messages/inbox",
        ]),
        ("Accountant (CJ)", "accountant@accountant.com", "cj", [
            "/accountant/dashboard",
            "/accountant/fees",
            "/accountant/payments",
            "/fees/",
            "/messages/inbox",
        ]),
        ("Librarian (CJ)", "librarian@librarian.com", "cj", [
            "/infra/library",
            "/messages/inbox",
        ]),
        ("Student (Demo)", "student@gmail.com", "student123", [
            "/student/dashboard",
            "/student/timetable",
            "/student/library",
        ]),
        ("Parent (Demo)", "parent@gmail.com", "parent123", [
            "/parent/dashboard",
        ]),
    ]

    all_passed = True
    print("\n" + "=" * 65)
    print("           EDTRACK ERP - ROLE & ROUTE AUDIT")
    print("=" * 65)

    for role_label, email, password, routes in accounts_to_test:
        print(f"\n[*] Testing {role_label} ({email})...")
        with client:
            # Login
            resp = client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)
            if resp.status_code != 200 or b'Invalid email or password' in resp.data:
                print(f"  [FAIL] Login failed for {email} (status: {resp.status_code})")
                all_passed = False
                continue
            print(f"  [OK] Login successful")

            # Check routes
            for route in routes:
                r_resp = client.get(route, follow_redirects=True)
                if r_resp.status_code == 200:
                    print(f"    [200 OK]  {route}")
                else:
                    print(f"    [FAIL {r_resp.status_code}] {route}")
                    all_passed = False

            # Logout
            client.get('/logout', follow_redirects=True)

    print("\n" + "=" * 65)
    if all_passed:
        print("  ALL AUDIT CHECKS PASSED! System is fully interconnected.")
    else:
        print("  SOME CHECKS FAILED. Review errors above.")
    print("=" * 65 + "\n")
    return all_passed

if __name__ == "__main__":
    success = run_audit()
    sys.exit(0 if success else 1)
