from app import create_app, db
from app.models import User
import sys

app = create_app()

def run_tests():
    client = app.test_client()
    
    with app.app_context():
        db.create_all()
        
        users_count = User.query.count()
        if users_count == 0:
            print("[INFO] Seeding database for tests...")
            import seed
            seed.main() if hasattr(seed, 'main') else None

        print("\n==================================================")
        print("  EDTRACK ERP ROUTE & DASHBOARD INTEGRATION TEST")
        print("==================================================")

        test_roles = [
            ("superadmin", "superadmin@edtrack.com", "super123"),
            ("admin", "admin@gmail.com", "admin123"),
            ("faculty", "faculty@gmail.com", "faculty123"),
            ("student", "student@gmail.com", "student123"),
            ("parent", "parent@gmail.com", "parent123")
        ]

        role_routes = {
            "admin": [
                "/admin/dashboard",
                "/admin/users",
                "/admin/users/add",
                "/admin/users/upload",
                "/admin/counselors",
                "/admin/students",
                "/admin/courses",
                "/admin/semesters",
                "/admin/sections",
                "/admin/subjects",
                "/admin/assignments",
                "/admin/parent-links",
                "/admin/terms",
                "/admin/fee-types",
                "/admin/announcements",
                "/admin/events",
                "/admin/feedback",
                "/admin/grievances",
                "/admin/leave-applications",
                "/admin/at-risk",
                "/admin/attendance/export-csv",
                "/admin/college",
                "/fees/",
                "/timetable/"
            ],
            "faculty": [
                "/faculty/dashboard",
                "/faculty/attendance",
                "/faculty/grades",
                "/faculty/assignments"
            ],
            "student": [
                "/student/dashboard",
                "/student/grades",
                "/student/attendance",
                "/student/assignments"
            ],
            "parent": [
                "/parent/dashboard"
            ],
            "superadmin": [
                "/superadmin/dashboard",
                "/superadmin/colleges"
            ]
        }

        passed = 0
        failed = 0
        failures = []

        for role_name, email, password in test_roles:
            print(f"\n--- Testing Role: {role_name.upper()} ({email}) ---")
            
            # Login via /login
            login_resp = client.post("/login", data={"email": email, "password": password}, follow_redirects=True)
            if login_resp.status_code != 200:
                print(f"[FAIL] Login failed for {email} with status {login_resp.status_code}")
                failed += 1
                failures.append((role_name, "/login", login_resp.status_code, "Login failed"))
                continue
            else:
                print(f"[OK] Login successful for {email}")
                passed += 1

            # Test routes for this role
            routes = role_routes.get(role_name, [])
            for route in routes:
                resp = client.get(route, follow_redirects=True)
                if resp.status_code == 200:
                    print(f"  [PASS 200] {route}")
                    passed += 1
                else:
                    print(f"  [FAIL {resp.status_code}] {route}")
                    failed += 1
                    failures.append((role_name, route, resp.status_code, f"HTTP {resp.status_code}"))

            # Logout via /logout
            client.get("/logout", follow_redirects=True)

        print("\n==================================================")
        print(f"TEST SUMMARY: {passed} Passed, {failed} Failed")
        print("==================================================")
        
        if failures:
            print("\nFAILURES:")
            for f_role, f_route, f_code, f_err in failures:
                print(f"- [{f_role.upper()}] {f_route} -> Status {f_code}: {f_err}")
            sys.exit(1)
        else:
            print("\nALL DASHBOARDS, ROUTES & LOGINS PASSED INTEGRATION TESTS!")
            sys.exit(0)

if __name__ == "__main__":
    run_tests()
