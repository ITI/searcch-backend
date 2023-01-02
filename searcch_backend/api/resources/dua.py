
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource
import sqlalchemy
from sqlalchemy import func, asc, desc, sql, and_, or_
import logging
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from bs4 import BeautifulSoup
import copy
import json

LOG = logging.getLogger(__name__)

class DUAResource(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='researchers',
                                   type=str,
                                   required=True,
                                   help='missing researchers')
        super(DUAResource, self).__init__()

    def get(self, artifact_group_id):
        args = self.reqparse.parse_args()
        researchers = args['researchers']
        researchers = json.loads(researchers)
        dua_name = db.session.query(DUA.dua_url).join(Artifact, Artifact.provider == DUA.provider).filter(artifact_group_id == Artifact.artifact_group_id).first()[0]
        dua_file = open(f'searcch_backend/api/dua_content/{dua_name}', mode='r')
        dua_content = dua_file.read()
        dua_file.close()
        soup = BeautifulSoup(dua_content, 'html.parser')
        if dua_name == 'usc_dua.md':
            dua_a = soup.find(id='dua_a_to_replicate').parent
            dua_a_to_replicate_og = dua_a.find(id='dua_a_to_replicate')
            dua_a_to_replicate = copy.deepcopy(dua_a_to_replicate_og)
            dua_a_to_replicate_og.clear()
            for researcher in researchers:
                to_replicate = copy.deepcopy(dua_a_to_replicate)
                to_replicate.find(id='dua_a_name').string = researcher['name']
                to_replicate.find(id='dua_a_email').string = researcher['email']
                to_replicate.find(id='dua_a_contact').string = researcher['number']
                dua_a.append(to_replicate)
            # soup.find('span', {'id': 'dua_a_name'}).text = 'University of Southern California'
            # soup.find('span', {'id': 'dua_a_name'}).replace_with('University of Southern California')
        response = jsonify({"dua": str(soup)})
        response.status_code = 200
        return response
