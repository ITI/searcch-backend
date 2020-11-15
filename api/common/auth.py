from api.app import app
from api.app import db
from models.model import *
from datetime import datetime
from flask import abort


def verify_api_key(api_key):
    if api_key == '':
        abort(403, description="missing secret api key")
    if api_key != app.config.get('SHARED_SECRET_KEY'):
        abort(403, description="incorrect secret api key")


def verify_token(sso_token):
    # sanity check input
    if sso_token == '':
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
            return True
    else:
        return False
