# logic for /login

from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
import requests
import datetime

from searcch_backend.api.app import db, app
from searcch_backend.api.common.auth import verify_api_key, verify_token
from searcch_backend.models.model import *
from searcch_backend.models.schema import *


def verify_strategy(strategy):
    if strategy not in ['github']:
        abort(403, description="missing/incorrect strategy")


def create_new_session(user_id, sso_token):
    login_session = db.session.query(Sessions).filter(Sessions.sso_token == sso_token).first()
    if login_session:
        if login_session.expires_on < datetime.datetime.now():  # token has expired
            db.session.delete(login_session)
            db.session.commit()
    else:
        expiry_timestamp = datetime.datetime.now(
        ) + datetime.timedelta(minutes=app.config['SESSION_TIMEOUT_IN_MINUTES'])
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
                                   help='missing SSO token from auth provider in post request')
        self.reqparse.add_argument(name='strategy',
                                   type=str,
                                   default='',
                                   required=True,
                                   help='missing auth strategy in post request')

    def post(self):
        args = self.reqparse.parse_args(strict=True)

        api_key = request.headers.get('X-API-Key')
        verify_api_key(api_key)

        strategy = args.get('strategy')
        verify_strategy(strategy)

        sso_token = args.get('token')
        if not verify_token(sso_token):
            # get email from Github
            github_user_email_api = 'https://api.github.com/user/emails'
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'Authorization': sso_token
            }
            response = requests.get(github_user_email_api, headers=headers)
            if response.status_code != requests.codes.ok:
                abort(response.status_code, description="invalid SSO token")
            response_json = response.json()[0]
            user_email = response_json["email"]

            # check if Person entity with that email exists
            person = db.session.query(Person).filter(Person.email == user_email).first()

            if person:  # create new session
                user = db.session.query(User).filter(
                    User.person_id == person.id).first()
                create_new_session(user.id, sso_token)
                response = jsonify({
                    "userid": user.id,
                    "person": PersonSchema().dump(person),
                    "message": "login successful. created new session for the user"
                })

            else:  # create new user
                github_user_details_api = 'https://api.github.com/user'
                headers = {
                    'Accept': 'application/vnd.github.v3+json',
                    'Authorization': sso_token
                }
                response = requests.get(github_user_details_api, headers=headers)
                
                if response.status_code != requests.codes.ok:
                    abort(response.status_code, description="invalid SSO token")
                
                user_details_json = response.json()
                user_name = user_details_json["name"] if user_details_json["name"] != '' else user_details_json["login"]
                
                # create database entities
                new_person = Person(name=user_name, email=user_email)
                db.session.add(new_person)
                db.session.commit()
                db.session.refresh(new_person)

                new_user = User(person_id=new_person.id)
                db.session.add(new_user)
                db.session.commit()
                db.session.refresh(new_user)

                create_new_session(new_user.id, sso_token)
                response = jsonify({
                    "userid": new_user.id,
                    "person": PersonSchema().dump(new_person),
                    "message": "login successful. created new person and user entity"
                })
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
            return response
        else:
            login_session = db.session.query(Sessions).filter(Sessions.sso_token == sso_token).first()
            existing_user = db.session.query(User).filter(User.id == login_session.user_id).first()
            existing_person = db.session.query(Person).filter(Person.id == existing_user.person_id).first()
            response = jsonify({
                "userid": login_session.user_id,
                "person": PersonSchema().dump(existing_person),
                "message": "login successful with valid session"
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
        return response
