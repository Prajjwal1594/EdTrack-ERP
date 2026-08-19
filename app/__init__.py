import sys
import traceback
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_socketio import SocketIO
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
socketio = SocketIO()

def sync_database_schema(engine):
    """Safely ensure all required columns exist in PostgreSQL and SQLite databases."""
    columns_map = {
        'students': [
            ('course_id', 'INTEGER'),
            ('stream_id', 'INTEGER'),
            ('batch_id', 'INTEGER'),
            ('section_id', 'INTEGER'),
            ('roll_number', 'VARCHAR(50)'),
            ('date_of_birth', 'DATE'),
            ('gender', 'VARCHAR(10)'),
            ('address', 'TEXT'),
            ('state', 'VARCHAR(100)'),
            ('country', 'VARCHAR(100)'),
            ('enrollment_date', 'DATE'),
            ('is_active', 'BOOLEAN DEFAULT TRUE'),
            ('blood_group', 'VARCHAR(10)'),
            ('religion', 'VARCHAR(50)'),
            ('caste', 'VARCHAR(50)'),
            ('aadhar_number', 'VARCHAR(20)'),
            ('admission_category', 'VARCHAR(50)'),
            ('session', 'VARCHAR(20)'),
            ('tc_date', 'DATE'),
            ('biometric_card_no', 'VARCHAR(50)'),
            ('alternate_semester_group', 'VARCHAR(20)'),
            ('semester_group', 'VARCHAR(20)'),
            ('phone2', 'VARCHAR(30)'),
            ('landline', 'VARCHAR(30)'),
            ('tenth_year', 'INTEGER'),
            ('tenth_roll', 'VARCHAR(50)'),
            ('tenth_board', 'VARCHAR(100)'),
            ('tenth_obtained', 'FLOAT'),
            ('tenth_max', 'FLOAT'),
            ('twelfth_year', 'INTEGER'),
            ('twelfth_roll', 'VARCHAR(50)'),
            ('twelfth_board', 'VARCHAR(100)'),
            ('twelfth_obtained', 'FLOAT'),
            ('twelfth_max', 'FLOAT'),
            ('father_name', 'VARCHAR(100)'),
            ('father_occupation', 'VARCHAR(100)'),
            ('father_mobile', 'VARCHAR(30)'),
            ('mother_name', 'VARCHAR(100)'),
            ('mother_mobile', 'VARCHAR(30)'),
            ('local_guardian_name', 'VARCHAR(100)'),
            ('local_guardian_mobile', 'VARCHAR(30)'),
            ('local_guardian_address', 'TEXT'),
        ],
        'sections': [
            ('course_id', 'INTEGER'),
            ('stream_id', 'INTEGER'),
            ('batch_id', 'INTEGER'),
            ('batch_counselor_id', 'INTEGER'),
        ],
        'users': [
            ('phone', 'VARCHAR(30)'),
            ('college_id', 'INTEGER'),
            ('is_active', 'BOOLEAN DEFAULT TRUE'),
            ('avatar_url', 'VARCHAR(255)'),
        ],
        'asset_records': [
            ('college_id', 'INTEGER'),
            ('item_name', 'VARCHAR(200)'),
            ('category', 'VARCHAR(100)'),
            ('quantity', 'INTEGER'),
            ('unit_cost', 'FLOAT'),
            ('total_cost', 'FLOAT'),
            ('purchase_date', 'DATE'),
            ('vendor_name', 'VARCHAR(150)'),
            ('invoice_no', 'VARCHAR(100)'),
            ('warranty_expiry', 'DATE'),
            ('block_name', 'VARCHAR(100)'),
            ('floor_level', 'VARCHAR(50)'),
            ('corridor_wing', 'VARCHAR(100)'),
            ('room_number', 'VARCHAR(100)'),
            ('department', 'VARCHAR(100)'),
            ('status', 'VARCHAR(50)'),
            ('notes', 'TEXT'),
        ]
    }

    from sqlalchemy import text, inspect
    try:
        inspector = inspect(engine)
        tables = [t.lower() for t in inspector.get_table_names()]
        with engine.begin() as conn:
            for table_name, cols in columns_map.items():
                if table_name in tables:
                    try:
                        existing_cols = [c['name'].lower() for c in inspector.get_columns(table_name)]
                    except Exception:
                        existing_cols = []
                    for col_name, col_type in cols:
                        if not existing_cols or col_name.lower() not in existing_cols:
                            try:
                                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type}"))
                                print(f"[SCHEMA SYNC] Added column {table_name}.{col_name}", flush=True)
                            except Exception:
                                try:
                                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
                                    print(f"[SCHEMA SYNC] Added column {table_name}.{col_name} (fallback)", flush=True)
                                except Exception as ex:
                                    print(f"[SCHEMA SYNC] Note on {table_name}.{col_name}: {ex}", flush=True)
    except Exception as e:
        print(f"[SCHEMA SYNC] Global schema sync note: {e}", flush=True)

def create_app(config_class=Config):
    print("[STARTUP] Creating Flask app...", flush=True)
    import os
    base_app_dir = os.path.abspath(os.path.dirname(__file__))
    templates_dir = os.path.abspath(os.path.join(base_app_dir, '..', 'templates'))
    statics_dir = os.path.abspath(os.path.join(base_app_dir, '..', 'static'))

    app = Flask(__name__,
                template_folder=templates_dir,
                static_folder=statics_dir)
    app.config.from_object(config_class)
    print(f"[STARTUP] DATABASE_URL set: {'DATABASE_URL' in app.config and bool(app.config.get('SQLALCHEMY_DATABASE_URI'))}", flush=True)
    print(f"[STARTUP] DB URI prefix: {app.config.get('SQLALCHEMY_DATABASE_URI', '')[:20]}...", flush=True)

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode='threading')

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @socketio.on('connect')
    def on_connect():
        print(f"[WS] Client connected")

    @socketio.on('subscribe_student')
    def on_subscribe(data):
        from flask_socketio import join_room
        sid = data.get('student_id')
        if sid:
            join_room(f"student_{sid}")

    @socketio.on('subscribe_user')
    def on_subscribe_user(data):
        from flask_socketio import join_room
        uid = data.get('user_id')
        if uid:
            join_room(f"user_{uid}")

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.faculty import bp as faculty_bp
    app.register_blueprint(faculty_bp, url_prefix='/faculty')

    from app.student import bp as student_bp
    app.register_blueprint(student_bp, url_prefix='/student')

    from app.parent import bp as parent_bp
    app.register_blueprint(parent_bp, url_prefix='/parent')

    from app.reports import bp as reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    from app.exams import bp as exams_bp
    app.register_blueprint(exams_bp, url_prefix='/exams')

    from app.messages import bp as messages_bp
    app.register_blueprint(messages_bp, url_prefix='/messages')

    from app.fees import bp as fees_bp
    app.register_blueprint(fees_bp, url_prefix='/fees')

    from app.timetable import bp as timetable_bp
    app.register_blueprint(timetable_bp, url_prefix='/timetable')

    from app.ai import bp as ai_bp
    app.register_blueprint(ai_bp, url_prefix='/api/ai')

    # ── Multi-tenant: Super Admin blueprint ──────────────────────────────────
    from app.superadmin import bp as superadmin_bp
    app.register_blueprint(superadmin_bp, url_prefix='/superadmin')

    # ── Enterprise ERP Module Blueprints ─────────────────────────────────────
    from app.admissions import bp as admissions_bp
    app.register_blueprint(admissions_bp, url_prefix='/admissions')

    from app.infra import bp as infra_bp
    app.register_blueprint(infra_bp, url_prefix='/infra')

    from app.hr import bp as hr_bp
    app.register_blueprint(hr_bp, url_prefix='/hr')

    from app.finance import bp as finance_bp
    app.register_blueprint(finance_bp, url_prefix='/finance')

    from app.accountant import bp as accountant_bp
    app.register_blueprint(accountant_bp, url_prefix='/accountant')

    @app.route('/health')
    def health_check():
        return jsonify({"status": "ok"}), 200

    @app.route('/init-db')
    def init_db_route():
        """Helper endpoint to initialize database tables and seed demo data on demand."""
        try:
            db.create_all()
            sync_database_schema(db.engine)
            from app.models import User
            if not User.query.first():
                from seed import seed
                seed(app, auto=True)
                return jsonify({"status": "success", "message": "Database initialized and seeded successfully!"}), 200
            return jsonify({"status": "success", "message": "Database tables and schema synchronized successfully."}), 200
        except Exception as e:
            traceback.print_exc()
            return jsonify({"status": "error", "message": str(e)}), 500

    @app.errorhandler(404)
    def not_found_error(error):
        print(f"DEBUG: 404 ERROR at {request.path} | Headers: {dict(request.headers)}", flush=True)
        if request.path.startswith('/api/'):
            return jsonify({"error": "Resource not found", "path": request.path}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        print(f"DEBUG: 500 ERROR at {request.path} | Error: {error}", flush=True)
        traceback.print_exc()
        if request.path.startswith('/api/') or request.args.get('debug') == '1':
            return jsonify({"error": "Internal server error", "details": str(error), "traceback": traceback.format_exc()}), 500
        return render_template('errors/500.html'), 500

    with app.app_context():
        try:
            print("[STARTUP] Running db.create_all()...", flush=True)
            db.create_all()
            print("[STARTUP] Running sync_database_schema()...", flush=True)
            sync_database_schema(db.engine)
            print("[STARTUP] db.create_all() and schema sync completed.", flush=True)

            from app.models import User
            if not User.query.first():
                try:
                    from seed import seed
                    seed(app, auto=True)
                    print("[STARTUP] Auto-seeded demo accounts successfully.", flush=True)
                except Exception as se:
                    print(f"[STARTUP] Auto-seed note: {se}", flush=True)
            else:
                # Ensure demo accountant accounts exist even on pre-existing Vercel databases
                acc_user = User.query.filter_by(email='accountant@gmail.com').first()
                if not acc_user:
                    admin_user = User.query.filter_by(role='admin').first()
                    cid = admin_user.college_id if admin_user else 1
                    new_acc = User(name="Robert Vance", email="accountant@gmail.com", role="accountant", college_id=cid, phone="+1 555-0004")
                    new_acc.set_password("accountant123")
                    db.session.add(new_acc)
                    db.session.commit()
                    print("[STARTUP] Ensured demo accountant@gmail.com exists.", flush=True)

                acc_user_2 = User.query.filter_by(email='accountant2@sunrise.edu').first()
                if not acc_user_2:
                    admin_user_2 = User.query.filter_by(email='admin2@sunrise.edu').first()
                    cid2 = admin_user_2.college_id if admin_user_2 else 2
                    new_acc2 = User(name="Sarah Jenkins", email="accountant2@sunrise.edu", role="accountant", college_id=cid2)
                    new_acc2.set_password("accountant123")
                    db.session.add(new_acc2)
                    db.session.commit()
                    print("[STARTUP] Ensured demo accountant2@sunrise.edu exists.", flush=True)

                hr_user = User.query.filter_by(email='hr@gmail.com').first()
                if not hr_user:
                    admin_user = User.query.filter_by(role='admin').first()
                    cid = admin_user.college_id if admin_user else 1
                    new_hr = User(name="Amanda Miller", email="hr@gmail.com", role="hr", college_id=cid, phone="+1 555-0005")
                    new_hr.set_password("hr123")
                    db.session.add(new_hr)
                    db.session.commit()
                    print("[STARTUP] Ensured demo hr@gmail.com exists.", flush=True)
        except Exception as e:
            print(f"[STARTUP] ERROR during db.create_all()/sync: {e}", flush=True)
            traceback.print_exc()

    print("[STARTUP] App creation complete. Ready to serve requests.", flush=True)
    return app
