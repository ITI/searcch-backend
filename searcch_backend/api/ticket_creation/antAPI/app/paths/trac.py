'''trac: rpc to create tickets'''

import os
import sys
import re
import subprocess
import logging

from flask import (
    Blueprint,
    request,
    jsonify,
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import (
    BadRequestKeyError,
)
from trac.env import Environment
from trac.ticket.model import Ticket

from ..tokens import validate_token
from ..flask_conf import (
    SECRET_KEY,
    TRAC_ATTACHMENT_DIR,
)


LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

PROVIDER_EMAIL = {
    'USC':     'usc-lander-host@isi.edu',
    'MERIT':   'mgkallit@merit.edu',
    'MEMPHIS': 'Christos.Papadopoulos@memphis.edu',
}
REQUIRED_PARAMS = {
    'ticket/new': (
        'description',
        'researcher',
        'email',
        'affiliation',
        'datasets',
    )
}
OPTIONAL_PARAMS = {
    'ticket/new': (
        'ssh_key',
    )
}
DATASETS_FSDB = '/nfs/lander/metadata/predict_schema/dataset_list.fsdb'
TRAC_HOME = '/nfs/lander/trace-distribution/lander_dua/trac/lander_dua2'


TRAC = Blueprint('trac', __name__)


def get_dataset_providers(datasets):
    '''
    Get all providers for `datasets` and return as a list of strings
    '''
    try:
        res = subprocess.run(
            f'dbcol datasetName providerName < {DATASETS_FSDB} | grep -v ^#',
            shell=True, capture_output=True, check=True)
    except subprocess.CalledProcessError as err:
        LOG.error("get_dataset_providers: cannot get dataset/provider list: %s", err)
        return []
    ds2provider = dict(x.split('\t') for x in res.stdout.decode('utf-8').split('\n')
                                         if '\t' in x)
    providers = set()
    for dataset in datasets.split():
        if not dataset:
            continue
        provider = ds2provider.get(dataset)
        if provider is None:
            LOG.error("get_dataset_providers: cannot find provider for dataset %s", dataset)
            #default to USC
            provider = 'USC'
        providers.add(provider)
    return providers


def add_attachment(filename, ticket_id):
    '''add attachment from `filename` to ticket id'd by ticket_id'''
    args = [ TRAC_HOME + '/venv/bin/trac-admin',
             TRAC_HOME + '/trac-env',
             'attachment',
             'add',
             f'ticket:{ticket_id}',
             filename,
             'antapi',
             'added attachment' ]
    try:
        proc = subprocess.run(args, capture_output=True, check=True)
    except subprocess.CalledProcessError as ex:
        LOG.error('add_attachment: ERROR adding attachment to ticket id %s: %s',
                  ticket_id, ex)
    return (proc.returncode, proc.stderr)


@TRAC.route('/trac/ticket/new', methods=['POST'])
@validate_token(secret_key=SECRET_KEY, realm='trac')
def ticket_new(current_user):
    '''Create ticket: uses a form with lots of fields'''
    LOG.info('Calling %s::ticket_new by %s', current_user.realm, current_user.email)

    #check all parameters
    try:
        params = { par : request.form[par]
                       for par in REQUIRED_PARAMS['ticket/new'] }
    except (AttributeError, BadRequestKeyError) as ex:
        LOG.error('ticket_new: parameter error (%s)', ex)
        return jsonify({'message': 'ERROR required parameter missing'}), 401

    for par in OPTIONAL_PARAMS['ticket/new']:
        if par in request.form:
            params[par] = request.form[par]

    #find providers for all present datasets
    all_providers = get_dataset_providers(params.get('datasets', ''))
    ccset = set()

    for provider in all_providers:
        addr = PROVIDER_EMAIL.get(provider)
        if addr is None:
            print(f"dataset_request.py: no address for provider `{provider}`, defaulting to USC's",
                  file=sys.stderr)
            addr = PROVIDER_EMAIL['USC']
        ccset.add(addr)

    if len(ccset) > 1:
        cc_str = ",".join(ccset)
        owner = PROVIDER_EMAIL['USC'].split('@', maxsplit=1)[0]
    else:
        cc_str = ccset.pop()
        owner = cc_str.split('@')[0]

    args = [ '/nfs/lander/trace-distribution/dataset_requests/cgi-bin/ticket2trac.py',
             '--reporter=dataset_request.py',
             '--type=DUA',
             '--keyword=web_request',
             f'--owner={owner}',
             f'--cc={cc_str}',
             f'--description={params["description"]}',
             '--extra=release_type=USC-direct',
             '--extra=dua_type=dua-ni-160816',
             f'--extra=researcher_name={params["researcher"]}',
             f'--extra=researcher_email={params["email"]}',
             f'--extra=researcher_affiliation={params["affiliation"]}',
             f'--extra=datasets={params["datasets"]}',
             f'--extra=ssh_key={params.get("ssh_key", "")}',
             TRAC_HOME + '/trac-env',
             f'{params["researcher"]} ({params["affiliation"]}) via Comunda' ]
    try:
        proc = subprocess.run(args, capture_output=True, check=True)
    except subprocess.CalledProcessError as ex:
        LOG.error("error creating ticket: %s", ex)
        return jsonify({'message': 'ERROR creating ticket'}), 401
    #ticket created successfully, extract ticket number
    rtid = re.compile(r".*#(\d+) .*")
    ticket_id = rtid.sub(r'\1', str(proc.stdout))
    if ticket_id != "":
        return jsonify({'message': 'OK', 'ticket_id': ticket_id}), 201

    LOG.error('error extracting ticket id')
    return jsonify({'message': 'OK', 'ticket_id': 'n/a'}), 201


@TRAC.route('/trac/ticket/<ticket_id>/attach', methods=['POST'])
@validate_token(secret_key=SECRET_KEY, realm='trac')
def ticket_attach(current_user, ticket_id):
    '''Create attachments to ticket <ticket_id>'''

    LOG.info('Calling %s::ticket_attach by %s to %s',
             current_user.realm, current_user.email, ticket_id)
    all_attachments = set()
    error_message = None
    try:
        for fname, file in request.files.items():
            int(ticket_id) #throws ValueError if ticket_id is not an integer
            saved_basename = str(ticket_id) + '-' + secure_filename(fname)
            saved_fname = os.path.join(TRAC_ATTACHMENT_DIR, saved_basename)
            file.save(saved_fname)
            all_attachments.add(saved_fname)
        LOG.info('trac::ticket_attach: saved attachments: %s', ', '.join(all_attachments))
        for fname in all_attachments:
            ret_code, error = add_attachment(fname, ticket_id)
            if ret_code != 0:
                if error_message is None:
                    error_message = f'ERROR adding attachments to ticket {ticket_id}:'
                error += f' ({fname}: {error})'

    except ValueError:
        return jsonify({'message':
                        'ERROR cannot process attachments: ticket id must be an integer'}), 401

    except Exception as ex: # pylint: disable=broad-except
        LOG.exception('ERROR: ticket_attach - exception: %s', ex)
        return jsonify({
            'message':
                f'ERROR cannot process attachments: exception -  {str(ex)}; cwd={os.getcwd()}'
        }), 401
    if error_message is not None:
        return jsonify({'message': error_message}), 401

    return jsonify({'message': 'OK'})


@TRAC.route('/trac/ticket/<ticket_id>/status', methods=['GET'])
@validate_token(secret_key=SECRET_KEY, realm='trac')
def ticket_status(current_user, ticket_id):
    '''Return the string with the status of the ticket <ticket_id>'''

    LOG.info('Calling %s::ticket_status by %s to %s',
             current_user.realm, current_user.email, ticket_id)

    env = Environment(TRAC_HOME + '/trac-env')
    try:
        ticket = Ticket(env, ticket_id)
    except Exception as ex: # pylint: disable=broad-except
        LOG.exception('ERROR: ticket_status - exception: %s', ex)
        return jsonify({
            'message':
                f'ERROR cannot obtain ticket status: exception -  {str(ex)}'
        }), 401
    return jsonify({'message': 'OK', 'status': ticket['status']})
