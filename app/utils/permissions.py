from functools import wraps
from flask import flash, redirect, url_for, request
from flask_login import current_user, login_required

def role_required(*allowed_roles):
    """
    Fine-Grained Role-Based Access Control (RBAC) Decorator.
    Restricts access strictly to specified roles, plus superadmin/admin override.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            # Superadmin and Admin have global access override
            if current_user.role in ('admin', 'superadmin'):
                return f(*args, **kwargs)
                
            if current_user.role not in allowed_roles:
                flash(f'Access denied for role "{current_user.role}". Authorized roles: {", ".join(allowed_roles)}.', 'danger')
                return redirect(url_for('auth.dashboard'))
                
            return f(*args, **kwargs)
        return login_required(decorated_function)
    return decorator
