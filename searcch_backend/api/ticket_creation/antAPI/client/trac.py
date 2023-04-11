'''antAPI trac client calls'''

import typing
import requests

from .auth import AntAPIClientAuthenticator

from .errors import (
    AntAPIClientTracError,
)

def antapi_trac_ticket_new(auth: AntAPIClientAuthenticator, **kwticket_fields) -> str:
    '''Create a new trac ticket.

    :param auth:        An instance of AntAPIClientAuthenticator
    :type auth:         AntAPIClientAuthenticator
    :param kwticket_fields: ticket fields

    **Required fields**
    - description
    - researcher
    - email
    - affiliation
    - datasets (space-separated)

    :returns: if successful, returns ticket_id (str) of the created ticket
    :rtype: str

    :raises: AntAPIClientTracError
    '''
    ticket_new_url = auth.base_url + '/trac/ticket/new'

    required_ticket_fields = ('description', 'researcher',
                              'email', 'affiliation', 'datasets')
    try:
        data = { key: kwticket_fields[key] for key in required_ticket_fields }
    except KeyError as ex:
        raise AntAPIClientTracError(
                  f'ticket parameter ({str(ex)} is required') from ex
    try:
        req = requests.post(ticket_new_url, data=data, headers=auth.auth_header())

        json_reply = req.json()

    except requests.exceptions.JSONDecodeError as ex:
        raise AntAPIClientTracError(
            f"Can't submit request: status={req.status_code}, error parsing JSON"
        ) from ex

    except requests.exceptions.RequestException as ex:
        raise AntAPIClientTracError(ex) from ex

    msg = json_reply.get('message', 'None')
    if not req.ok:
        raise AntAPIClientTracError(
            f"Can't create ticket: status={req.status_code}, error={msg}")
    if 'ticket_id' not in json_reply:
        raise AntAPIClientTracError(
            f"Can't create ticket: no token, error={msg}")
    #everything appears OK
    return json_reply['ticket_id']


def antapi_trac_ticket_attach(auth: AntAPIClientAuthenticator,
                              ticket_id: str,
                              filenames: typing.List[str]) -> None:
    '''Attach files to the ticket, referred to by `ticket_id`.

    :param auth:        An instance of AntAPIClientAuthenticator
    :type auth:         AntAPIClientAuthenticator
    :param ticket_id:   Ticket ID to add attachments to
    :type ticket_id:    str
    :param filenames:   List of filenames containing the attachments
    :type filenames:    list[str]

    :raises: AntAPIClientTracError
    '''
    if not filenames:
        raise AntAPIClientTracError("Can't attach 0 files")
    ufiles = set(filenames)

    try:
        # pylint: disable=consider-using-with
        files = [ (fname, open(fname, 'rb')) for fname in ufiles ]
    except OSError as ex:
        raise AntAPIClientTracError(ex) from ex

    ticket_attach_url = auth.base_url + f'/trac/ticket/{ticket_id}/attach'
    try:
        req = requests.post(ticket_attach_url, files=files, headers=auth.auth_header())

        json_reply = req.json()

    except requests.exceptions.JSONDecodeError as ex:
        raise AntAPIClientTracError(
            f"Can't submit request: status={req.status_code}, error parsing JSON"
        ) from ex

    except requests.exceptions.RequestException as ex:
        raise AntAPIClientTracError(ex) from ex

    if not req.ok:
        msg = json_reply.get('message', 'None')
        raise AntAPIClientTracError(
            f"Can't create ticket: status={req.status_code}, error={msg}")


def antapi_trac_ticket_status(auth: AntAPIClientAuthenticator,
                              ticket_id: str) -> str: 
    '''Get the status of the ticket, referred to by `ticket_id`.

    :param auth:        An instance of AntAPIClientAuthenticator
    :type auth:         AntAPIClientAuthenticator
    :param ticket_id:   Ticket ID to add attachments to
    :type ticket_id:    str

    :raises: AntAPIClientTracError
    '''

    ticket_status_url = auth.base_url + f'/trac/ticket/{ticket_id}/status'
    try:
        req = requests.get(ticket_status_url, headers=auth.auth_header())

        json_reply = req.json()

    except requests.exceptions.JSONDecodeError as ex:
        raise AntAPIClientTracError(
            f"Can't submit request: status={req.status_code}, error parsing JSON"
        ) from ex

    except requests.exceptions.RequestException as ex:
        raise AntAPIClientTracError(ex) from ex

    if not req.ok:
        msg = json_reply.get('message', 'None')
        raise AntAPIClientTracError(
            f"Can't get ticket status: code is {req.status_code}, error={msg}")
    if 'status' not in json_reply:
        raise AntAPIClientTracError(
            f"Can't get ticket status: status is missing from reply, reply={json_reply}")
    return json_reply['status']
