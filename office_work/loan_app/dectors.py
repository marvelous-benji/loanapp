from functools import wraps
from flask import url_for, redirect
from flask_login import current_user


def detail_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.details_verified:
            return redirect(url_for('verify_user'))
        return f(*args, **kwargs)
    return decorated_function

def check_confirm(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated and not current_user.confirmed:
            return redirect(url_for('unconfirmed'))
        return f(*args, **kwargs)
    return decorated_function
