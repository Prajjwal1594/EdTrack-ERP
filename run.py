from app import create_app, db, socketio
from app.models import User, College, Semester, Section, Subject, Student

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'College': College,
            'Semester': Semester, 'Section': Section, 'Subject': Subject, 'Student': Student}

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
