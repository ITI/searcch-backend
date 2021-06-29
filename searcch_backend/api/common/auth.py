from searcch_backend.api.app import app
from searcch_backend.api.app import db
from searcch_backend.models.model import Sessions
from datetime import datetime
from flask import abort


def has_api_key(request):
    if request.headers.get('X-Api-Key', None):
        return True
    return False

def verify_api_key(request):
    api_key = request.headers.get('X-Api-Key', None)
    if not api_key:
        abort(403, description="missing secret api key")
    if api_key != app.config.get('SHARED_SECRET_KEY'):
        abort(401, description="incorrect api key")

def has_token(request):
    auth_val = request.headers.get('Authorization', None)
    if auth_val:
        return True
    return False

def lookup_token(sso_token):
    # sanity check input
    if not sso_token:
        abort(403, description="missing SSO token from auth provider")

    # check for token in sessions table
    login_session = db.session.query(Sessions).filter(Sessions.sso_token == sso_token).first()
    if login_session:
        if login_session.expires_on < datetime.now():  # token has expired
            # delete token from sessions table
            db.session.delete(login_session)
            db.session.commit()

            # send back for relogin
            abort(401, description="session token has expired. please re-login")
        else:
            return login_session
    else:
        return None

def verify_token(request):
    sso_token = request.headers.get('Authorization', None)
    if not sso_token:
        abort(403, description="missing SSO token from auth provider")
    login_session = lookup_token(sso_token)
    if not login_session:
        abort(401, description="invalid session token")
    return login_session
