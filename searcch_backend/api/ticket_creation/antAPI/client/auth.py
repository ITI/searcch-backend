'''Authenticate to the antAPI system'''

import typing
from datetime import (
    datetime,
    timedelta,
)

import requests

from .errors import AntAPIClientAuthError

class AntAPIClientAuthenticator:
    '''
    Class for authentication and storing auth data
    '''
    base_url: str = ''
    realm: str = ''
    email: str = ''
    password:str = ''
    #cached header
    token_maxlifetime: timedelta = timedelta(minutes=50)
    _header_exp: typing.Optional[datetime] = None
    _header: typing.Optional[typing.Dict[str,str]] = None


    def __init__(self, base_url:str, realm:str, email:str, password:str):
        self.base_url = base_url
        self.realm = realm
        self.email = email
        self.password = password


    def refresh(self) -> typing.Dict[str,str]:
        '''
        Authenticate to antAPI and get an auth header with a JWT.
        '''
        auth_url = f'{self.base_url}/user/auth'

        try:
            req_time = datetime.utcnow()
            req = requests.post(auth_url, data=dict(realm=self.realm,
                                                    email=self.email,
                                                    pword=self.password))
            json_reply = req.json()

        except requests.exceptions.JSONDecodeError as ex:
            raise AntAPIClientAuthError(
                f"Can't authenticate: status={req.status_code}, error parsing JSON response"
            ) from ex

        except requests.exceptions.RequestException as ex:
            raise AntAPIClientAuthError from ex

        msg = json_reply.get('message', 'None')
        if not req.ok:
            raise AntAPIClientAuthError(
                f"Can't authenticate: status={req.status_code}, error={msg}")
        if 'token' not in json_reply:
            raise AntAPIClientAuthError(
                f"Can't authenticate: no token, status={req.status_code}, error={msg}")
        #everything appears OK
        self._header = { "x-access-token" : json_reply['token'] }
        self._header_exp = req_time + self.token_maxlifetime

        return self._header


    def auth_header(self) -> typing.Dict[str,str]:
        '''
        Get a cached auth header, or get a fresh one if none is cached
        Cache the new header.

        Returns the dictionary containing auth header, which can be
        passed to requests.post()

        Raises AntAPIClientAuthError on error
        '''

        if self._header and datetime.utcnow() <= self._header_exp:
            return self._header

        return self.refresh()
