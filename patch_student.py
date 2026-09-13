fix_code = '''
@bp.route('/timetable')
@student_required
def timetable():
    student = get_current_student()
    section = student.section if student else None
    from app.models import TimetableEntry
    entries = TimetableEntry.query.filter_by(section_id=student.section_id).all() if student and student.section_id else []
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    timetable_by_day = {day: [] for day in days_order}
    for e in entries:
        if e.day_of_week in timetable_by_day:
            timetable_by_day[e.day_of_week].append(e)
    for day in days_order:
        timetable_by_day[day].sort(key=lambda x: str(x.start_time))
    total_slots = len(entries)
    return render_template('student/timetable.html', student=student, section=section,
                           days_order=days_order, timetable_by_day=timetable_by_day, total_slots=total_slots)

@bp.route('/library')
@student_required
def library():
    student = get_current_student()
    search = request.args.get('search', '').strip()
    selected_category = request.args.get('category', '').strip()
    from app.models import LibraryBook, BookIssue
    from datetime import date
    
    query = LibraryBook.query.filter_by(college_id=current_user.college_id)
    if search:
        query = query.filter(
            db.or_(
                LibraryBook.title.ilike(f'%{search}%'),
                LibraryBook.author.ilike(f'%{search}%'),
                LibraryBook.isbn.ilike(f'%{search}%')
            )
        )
    if selected_category:
        query = query.filter_by(category=selected_category)
        
    books = query.all()
    all_books = LibraryBook.query.filter_by(college_id=current_user.college_id).all()
    categories = sorted(list(set(b.category for b in all_books if b.category)))
    
    my_issues = BookIssue.query.filter_by(user_id=current_user.id).order_by(BookIssue.issue_date.desc()).all()
    overdue_count = sum(1 for i in my_issues if i.status == 'overdue' or (i.due_date and i.due_date < date.today() and i.status == 'Issued'))
    
    return render_template('student/library.html', student=student, books=books,
                           categories=categories, search=search, selected_category=selected_category,
                           my_issues=my_issues, overdue_count=overdue_count)
'''

for fpath in ['app/student/routes.py', 'elwood/app/student/routes.py']:
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()
    needle = "@bp.route('/timetable')"
    idx = content.find(needle)
    if idx != -1:
        content = content[:idx].strip() + '\n\n' + fix_code.strip() + '\n'
    else:
        content = content.strip() + '\n\n' + fix_code.strip() + '\n'
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Successfully updated timetable & library in {fpath}')
