import requests
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

BASE_URL = "https://ed-track-erp.vercel.app"

TEST_ROLES = [
    ("superadmin", "superadmin@edtrack.com", "super123"),
    ("admin", "admin@gmail.com", "admin123"),
    ("it_admin", "itadmin@gmail.com", "itadmin123"),
    ("principal", "principal@gmail.com", "principal123"),
    ("registrar", "registrar@gmail.com", "registrar123"),
    ("hod", "hod@gmail.com", "hod123"),
    ("admission_officer", "admissions@gmail.com", "admissions123"),
    ("accountant", "accountant@gmail.com", "accountant123"),
    ("hr", "hr@gmail.com", "hr123"),
    ("examination_officer", "exam_officer@gmail.com", "exam123"),
    ("faculty", "faculty@gmail.com", "faculty123"),
    ("course_coordinator", "coordinator@gmail.com", "coordinator123"),
    ("academic_advisor", "advisor@gmail.com", "advisor123"),
    ("librarian", "librarian@gmail.com", "librarian123"),
    ("hostel_warden", "warden@gmail.com", "warden123"),
    ("transport_manager", "transport@gmail.com", "transport123"),
    ("placement_officer", "placement@gmail.com", "placement123"),
    ("student_affairs", "affairs@gmail.com", "affairs123"),
    ("student", "student@gmail.com", "student123"),
    ("parent", "parent@gmail.com", "parent123"),
    ("alumni", "alumni@gmail.com", "alumni123"),
    ("employer", "employer@gmail.com", "employer123")
]

ROLE_ROUTES = {
    "superadmin": [
        "/superadmin/dashboard",
        "/superadmin/colleges"
    ],
    "admin": [
        "/admin/dashboard",
        "/admin/users",
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
        "/fees/",
        "/timetable/"
    ],
    "it_admin": [
        "/it-admin/dashboard",
        "/it-admin/audit-logs",
        "/it-admin/sessions",
        "/it-admin/backup"
    ],
    "principal": [
        "/dashboard",
        "/academic-calendar",
        "/principal/academic-delivery",
        "/principal/admissions-growth",
        "/principal/accreditation-audit",
        "/admin/students",
        "/admin/courses",
        "/admin/at-risk"
    ],
    "registrar": [
        "/dashboard",
        "/academic-calendar",
        "/registrar/transcripts",
        "/admin/students",
        "/admin/attendance/export-csv"
    ],
    "hod": [
        "/dashboard",
        "/academic-calendar",
        "/hod/department-workload",
        "/admin/subjects",
        "/admin/assignments",
        "/admin/at-risk"
    ],
    "admission_officer": [
        "/dashboard",
        "/admissions/enquiries",
        "/admissions/applications",
        "/admissions/merit-list",
        "/admin/students"
    ],
    "accountant": [
        "/accountant/dashboard",
        "/accountant/fees",
        "/accountant/payments",
        "/fees/"
    ],
    "hr": [
        "/hr/dashboard",
        "/hr/staff",
        "/hr/attendance",
        "/hr/payroll",
        "/hr/leave-requests"
    ],
    "examination_officer": [
        "/dashboard",
        "/academic-calendar",
        "/exam-officer/hall-tickets",
        "/faculty/grades",
        "/timetable/"
    ],
    "faculty": [
        "/faculty/dashboard",
        "/faculty/attendance",
        "/faculty/grades",
        "/faculty/assignments"
    ],
    "course_coordinator": [
        "/dashboard",
        "/academic-calendar",
        "/course-coordinator/co-po",
        "/faculty/assignments",
        "/admin/subjects",
        "/admin/courses"
    ],
    "academic_advisor": [
        "/dashboard",
        "/academic-advisor/counseling-logs",
        "/admin/at-risk",
        "/admin/counselors",
        "/admin/students"
    ],
    "librarian": [
        "/dashboard",
        "/librarian/fines-e-resources",
        "/infra/library",
        "/infra/inventory"
    ],
    "hostel_warden": [
        "/dashboard",
        "/warden/mess-inspections",
        "/infra/hostel",
        "/admin/leave-applications",
        "/admin/grievances"
    ],
    "transport_manager": [
        "/dashboard",
        "/transport/fleet-maintenance",
        "/infra/transport",
        "/infra/inventory"
    ],
    "placement_officer": [
        "/dashboard",
        "/placement/drive-manager",
        "/admin/students",
        "/admin/events"
    ],
    "student_affairs": [
        "/dashboard",
        "/student-affairs/clubs-antiragging",
        "/admin/events",
        "/admin/grievances",
        "/admin/feedback"
    ],
    "student": [
        "/student/dashboard",
        "/student/grades",
        "/student/attendance",
        "/student/assignments",
        "/student/timetable",
        "/student/library"
    ],
    "parent": [
        "/parent/dashboard",
        "/parent/children"
    ],
    "alumni": [
        "/dashboard",
        "/alumni/job-referrals",
        "/admin/events"
    ],
    "employer": [
        "/dashboard",
        "/employer/recruitment-portal",
        "/admin/students"
    ]
}

def audit_role(role_key, email, password):
    session = requests.Session()
    print(f"\n==================================================")
    print(f"  AUDITING ROLE: {role_key.upper()} ({email})")
    print(f"==================================================")

    # 1. Login
    login_url = f"{BASE_URL}/login"
    login_resp = session.post(login_url, data={"email": email, "password": password}, allow_redirects=True)
    
    if login_resp.status_code != 200 or "login" in login_resp.url.lower():
        print(f"[-] [LOGIN FAILED] Status: {login_resp.status_code}, Final URL: {login_resp.url}")
        return {"role": role_key, "login": False, "results": []}

    print(f"[+] [LOGIN SUCCESS] Final URL: {login_resp.url}")

    results = []
    routes = ROLE_ROUTES.get(role_key, ["/dashboard"])

    for route in routes:
        full_url = f"{BASE_URL}{route}"
        resp = session.get(full_url, allow_redirects=True)
        
        # Check if redirected away due to permission denied
        text_lower = resp.text.lower()
        is_permission_blocked = "access required" in text_lower or "access denied" in text_lower
        is_redirected_away = (route != "/dashboard" and resp.url.endswith("/dashboard")) or "login" in resp.url.lower()

        if resp.status_code == 200 and not is_permission_blocked and not (is_redirected_away and route not in resp.url):
            print(f"  [+] [PASS 200] {route}")
            results.append({"route": route, "status": 200, "ok": True})
        elif is_permission_blocked or is_redirected_away:
            print(f"  [!] [BLOCKED] {route} -> Redirected to {resp.url}")
            results.append({"route": route, "status": resp.status_code, "ok": False, "reason": "Permission Blocked"})
        else:
            print(f"  [-] [FAIL {resp.status_code}] {route} -> URL: {resp.url}")
            results.append({"route": route, "status": resp.status_code, "ok": False, "reason": f"HTTP {resp.status_code}"})

    # Logout
    session.get(f"{BASE_URL}/logout")
    return {"role": role_key, "login": True, "results": results}

def main():
    print(f"Connecting to live Vercel URL: {BASE_URL}")
    total_passed = 0
    total_failed = 0
    role_summaries = []

    for role_key, email, pwd in TEST_ROLES:
        res = audit_role(role_key, email, pwd)
        role_summaries.append(res)
        if not res["login"]:
            total_failed += 1
        for r in res["results"]:
            if r["ok"]:
                total_passed += 1
            else:
                total_failed += 1

    print("\n" + "="*60)
    print(f"LIVE VERCEL AUDIT SUMMARY: {total_passed} Routes Passed, {total_failed} Routes Failed/Blocked")
    print("="*60)

    for s in role_summaries:
        flaws = [r for r in s["results"] if not r["ok"]]
        if not s["login"]:
            print(f"[-] {s['role'].upper()}: LOGIN FAILED")
        elif flaws:
            print(f"[!] {s['role'].upper()}: {len(flaws)} flaws detected:")
            for f in flaws:
                print(f"    - {f['route']}: {f.get('reason')}")
        else:
            print(f"[+] {s['role'].upper()}: All routes verified 100% OK")

if __name__ == "__main__":
    main()
