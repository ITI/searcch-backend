'''Token (JWT) handling for antapi'''


from functools import wraps
from datetime import (
    datetime,
    timedelta,
)
from flask import jsonify, request
import jwt

from .users import User

JWT_TOKEN_ALGO = "HS256"
JWT_TOKEN_LIFETIME = timedelta(hours=1)


def generate_token(secret_key, email, realm):
    '''Generate a JWT token with user email, realm and expiration'''
    token = jwt.encode({
        "email": email,
        "realm": realm,
        "exp" : datetime.utcnow() + JWT_TOKEN_LIFETIME}, secret_key, algorithm=JWT_TOKEN_ALGO)

    return token


# decorator for verifying the JWT
def validate_token(secret_key, realm, log=None):
    '''Validate JTW token in a flask path'''
    def decorate(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # jwt is passed in the request header
            token = request.headers.get('x-access-token')
            # return 401 if token is not passed
            if token is None:
                return jsonify({'message' : 'Error: token is required'}), 401

            try:
                # decoding the payload to fetch the stored details
                data = jwt.decode(token, secret_key, algorithms=[JWT_TOKEN_ALGO])
                if data['realm'] != realm:
                    raise ValueError('User not authorized for this realm')
                current_user = User.lookup(data['email'], data['realm'])
            except Exception as ex: # pylint: disable=broad-except
                if log:
                    log.error('Error validation token: %s', ex)
                return jsonify({ 'message' : 'Error: token is invalid' }), 401

            #token validated
            return  func(current_user, *args, **kwargs)

        return wrapper

    return decorate
