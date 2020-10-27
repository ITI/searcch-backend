from app import app
from app import db
from app.common.auth import verify_api_key, verify_token
from app.models.model import *
from app.models.schema import *
from datetime import datetime
from flask import request, jsonify, render_template, Blueprint, abort
import json
import requests


login_bp = Blueprint('login', __name__, url_prefix='login')

@login_bp.app_errorhandler(401)
def unauthorized(err):
    return jsonify(error=str(err)), 401

@login_bp.app_errorhandler(403)
def forbidden(err):
    return jsonify(error=str(err)), 403


@login_bp.app_errorhandler(404)
def resource_not_found(err):
    return jsonify(error=str(err)), 404


@login_bp.app_errorhandler(500)
def resource_not_found(err):
    return jsonify(error=str(err)), 500


def verify_strategy(strategy):
    if strategy not in ['github']:
        abort(403, description="missing/incorrect strategy")

def create_new_session(user_id, sso_token):
    # TODO: replace expiry time with config variable
    expiry_timestamp = datetime.now() + datetime.timedelta(days=7)
    new_session = Sessions(user_id=user.id, sso_token=sso_token, expires_on=expiry_timestamp)
    db.session.add(new_session)
    db.session.commit()

@login_bp.route("/", methods=['POST'])
def login():
    """login [summary]
    Payload: 
    {
        token: “Bearer 3b760d...7c14741daf429872afc”,
        api_key: the API token from the back-end // for non-GET requests only
        strategy: “github”
    }

    """
    args = request.get_json()
    sso_token = args.get('token', '')
    api_key = args.get('api_key', '')
    strategy = args.get('strategy', '')

    verify_api_key(api_key)
    verify_strategy(strategy)

    if not verify_token(sso_token):
        # get email from Github
        github_user_email_api = 'https://api.github.com/user/emails'
        headers = {
            'accept': 'application/vnd.github.v3+json',
            'Authorization': 'token ' + sso_token
        }
        response = requests.get(github_user_email_api, headers=headers)
        if response.status_code != requests.codes.ok:
            abort(response.status_code, description="invalid token")
        
        # check if Person entity with that email exists
        person = db.session.query(Person).filter(Person.email == response.email).first()
        
        if person: # create new session
            user = db.session.query(User).filter(User.person_id == person.id).first()
            create_new_session(user.id, sso_token)
        else: # create new user
            # TODO: get user's name from Github
            new_person = Person(name='', email=response.email)
            db.session.add(new_person)
            db.session.commit()
            db.session.refresh(new_person)
            
            new_user = User(person_id=new_person.id)
            db.session.add(new_user)
            db.session.commit()
            db.session.refresh(new_user)

            create_new_session(new_user.id, sso_token)

        response = jsonify({"message": "login successful"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
