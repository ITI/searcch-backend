
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
from datetime import datetime

LOG = logging.getLogger(__name__)

class DUAResource(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='researchers',
                                   type=str,
                                   required=True,
                                   help='missing researchers')
        self.reqparse.add_argument(name='research',
                                   type=str,
                                   required=True,
                                   help='missing research')  
        self.reqparse.add_argument(name='project',
                                   type=str,
                                   required=True,
                                   help='missing project name')    
        self.reqparse.add_argument(name='dataset_name',
                                   type=str,
                                   required=True,
                                   help='missing dataset name')
        self.reqparse.add_argument(name='representative',
                                   type=str,
                                   required=True,
                                   help='missing representative') 
        self.reqparse.add_argument(name='poc',
                                   type=str,
                                   required=True,
                                   help='missing poc')
        self.reqparse.add_argument(name='merit_org',
                                    type=str,
                                    required=True,
                                    help='missing org')  
        self.reqparse.add_argument(name='merit_researcher',
                                    type=str,
                                    required=True,
                                    help='missing merit researcher')  
        self.reqparse.add_argument(name='merit_researcher_title',
                                    type=str,
                                    required=True,
                                    help='missing merit researcher title')                            
        super(DUAResource, self).__init__()

    def get(self, artifact_group_id):
        args = self.reqparse.parse_args()
        researchers = args['researchers']
        research = args['research']
        project = args['project']
        dataset_name = args['dataset_name']
        representative = args['representative']
        poc = args['poc']
        merit_org = args['merit_org']
        merit_researcher = args['merit_researcher']
        merit_researcher_title = args['merit_researcher_title']
        researchers = json.loads(researchers)
        representative = json.loads(representative)
        poc = json.loads(poc)
        
        dataset_category = db.session.query(Artifact.datasetCategory).filter(artifact_group_id == Artifact.artifact_group_id).first()[0]
        dataset_category = "" if dataset_category is None else dataset_category  
        dataset_subcategory = db.session.query(Artifact.datasetSubCategory).filter(artifact_group_id == Artifact.artifact_group_id).first()[0]
        dataset_subcategory = "" if dataset_subcategory is None else dataset_subcategory  
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
                        
            soup.find(id='dua_b_category').string = dataset_category
            soup.find(id='dua_b_sub_category').string = dataset_subcategory
            soup.find(id='dua_b_dataset_name').string = dataset_name

            soup.find(id='dua_c_project_name').string = project
            soup.find(id='dua_c_desc').string = research

            soup.find(id='rep_by').string = representative['name']
            soup.find(id='rep_email').string = representative['email']
            soup.find(id='rep_name').string = representative['name']
            soup.find(id='rep_title').string = representative['title']
            soup.find(id='rep_date').string = datetime.now().strftime("%m/%d/%Y")

            soup.find(id='poc_name').string = poc['name']
            soup.find(id='poc_email').string = poc['email']

        elif dua_name == 'merit_network_dua.md':
            soup.find(id='rep_org').string = merit_org
            soup.find(id='rep_name').string = merit_researcher
            soup.find(id='rep_by').string = merit_researcher
            soup.find(id='rep_title').string = merit_researcher_title
            soup.find(id='rep_date').string = datetime.now().strftime("%m/%d/%Y")

        response = jsonify({"dua": str(soup)})
        response.status_code = 200
        return response
