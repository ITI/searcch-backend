# logic for /login

from api.app import db, app
from api.common.auth import verify_api_key, verify_token
from models.model import *
from models.schema import *
from datetime import datetime
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
import requests

def verify_strategy(strategy):
    if strategy not in ['github']:
        abort(403, description="missing/incorrect strategy")


def create_new_session(user_id, sso_token):
    expiry_timestamp = datetime.now() + datetime.timedelta(minutes=app.config['SESSION_TIMEOUT_IN_MINUTES'])
    new_session = Sessions(
        user_id=user_id, sso_token=sso_token, expires_on=expiry_timestamp)
    db.session.add(new_session)
    db.session.commit()


class LoginAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='token',
                                   type=str,
                                   required=True,
                                   default='',
                                   location='form',
                                   help='missing SSO token from auth provider in post request')
        self.reqparse.add_argument(name='api_key',
                                   type=str,
                                   required=True,
                                   default='',
                                   location='form',
                                   help='missing API secret key in post request')
        self.reqparse.add_argument(name='strategy',
                                   type=str,
                                   default='',
                                   location='form',
                                   required=True,
                                   help='missing auth strategy in post request')

    def post(self):
        args = self.reqparse.parse_args(strict=True)
        sso_token = args.get('token')
        api_key = args.get('api_key')
        strategy = args.get('strategy')

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
                abort(response.status_code, description="invalid SSO token")
            
            # check if Person entity with that email exists
            person = db.session.query(Person).filter(Person.email == response.email).first()
            
            if person: # create new session
                user = db.session.query(User).filter(User.person_id == person.id).first()
                create_new_session(user.id, sso_token)
                msg = 'login successful. created new session for the user'
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
                msg = 'login successful. created new person and user entity'

            response = jsonify({"message": msg})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
            return response
        else:
            response = jsonify({"message": "login successful with valid session"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
            return response
