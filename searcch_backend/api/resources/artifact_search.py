# logic for /artifacts

from searcch_backend.api.app import db
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, url_for, request
from flask_restful import reqparse, Resource
from sqlalchemy import func, desc, sql, or_, and_, exc
from searcch_backend.api.common.auth import (verify_api_key, has_api_key, has_token, verify_token)
import math
import logging
import json

LOG = logging.getLogger(__name__)

def generate_artifact_uri(artifact_group_id, artifact_id=None):
    return url_for('api.artifact', artifact_group_id=artifact_group_id,
                   artifact_id=artifact_id)

def search_artifacts(keywords, artifact_types, author_keywords, organization, owner_keywords, badge_id_list, page_num, items_per_page):
    """ search for artifacts based on keywords, with optional filters by owner and affiliation """
    sqratings = db.session.query(
        ArtifactRatings.artifact_group_id,
        func.count(ArtifactRatings.id).label('num_ratings'),
        func.avg(ArtifactRatings.rating).label('avg_rating')
    ).group_by("artifact_group_id").subquery()
    sqreviews = db.session.query(
        ArtifactReviews.artifact_group_id,
        func.count(ArtifactReviews.id).label('num_reviews')
    ).group_by("artifact_group_id").subquery()

    # create base query object
    if not keywords:
        query = db.session.query(Artifact,
                                    sql.expression.bindparam("zero", 0).label("rank"),
                                    'num_ratings', 'avg_rating', 'num_reviews', "view_count"
                                    ).order_by(
                                    db.case([
                                        (Artifact.type == 'software', 1),
                                        (Artifact.type == 'dataset', 2),
                                        (Artifact.type ==
                                        'publication', 3),
                                    ], else_=4)
                                )
        query = query.join(ArtifactGroup, ArtifactGroup.id == Artifact.artifact_group_id
                        ).join(sqratings, ArtifactGroup.id == sqratings.c.artifact_group_id, isouter=True
                        ).join(ArtifactPublication, ArtifactPublication.id == ArtifactGroup.publication_id
                        ).join(sqreviews, ArtifactGroup.id == sqreviews.c.artifact_group_id, isouter=True
                        ).order_by(sqratings.c.avg_rating.desc().nullslast(),sqreviews.c.num_reviews.desc())
    else:
        search_query = db.session.query(ArtifactSearchMaterializedView.artifact_id, 
                                        func.ts_rank_cd(ArtifactSearchMaterializedView.doc_vector, func.websearch_to_tsquery("english", keywords)).label("rank")
                                    ).filter(ArtifactSearchMaterializedView.doc_vector.op('@@')(func.websearch_to_tsquery("english", keywords))
                                    ).subquery()
        query = db.session.query(Artifact, 
                                    search_query.c.rank, 'num_ratings', 'avg_rating', 'num_reviews', "view_count"
                                    ).join(ArtifactPublication, ArtifactPublication.artifact_id == Artifact.id
                                    ).join(search_query, Artifact.id == search_query.c.artifact_id, isouter=False)
        
        query = query.join(sqratings, Artifact.artifact_group_id == sqratings.c.artifact_group_id, isouter=True
                        ).join(sqreviews, Artifact.artifact_group_id == sqreviews.c.artifact_group_id, isouter=True
                        ).order_by(desc(search_query.c.rank))

    if author_keywords or organization:
        rank_list = []
        if author_keywords:
            if type(author_keywords) is list:
                author_keywords = ' or '.join(author_keywords)
            rank_list.append(
                func.ts_rank_cd(Person.person_tsv, func.websearch_to_tsquery("english", author_keywords)).label("arank"))
        if organization:
            if type(organization) is list:
                organization = ' or '.join(organization)
            rank_list.append(
                func.ts_rank_cd(Organization.org_tsv, func.websearch_to_tsquery("english", organization)).label("orank"))
        author_org_query = db.session.query(
            Artifact.id, *rank_list
        ).join(ArtifactAffiliation, ArtifactAffiliation.artifact_id == Artifact.id
        ).join(Affiliation, Affiliation.id == ArtifactAffiliation.affiliation_id
        )
        if author_keywords:
            author_org_query = author_org_query.join(Person, Person.id == Affiliation.person_id)
        if organization:
            author_org_query = author_org_query.join(Organization, Organization.id == Affiliation.org_id)
        if author_keywords:
            author_org_query = author_org_query.filter(
                Person.person_tsv.op('@@')(func.websearch_to_tsquery("english", author_keywords))).order_by(desc("arank"))
        if organization:
            author_org_query = author_org_query.filter(
                Organization.org_tsv.op('@@')(func.websearch_to_tsquery("english", organization))).order_by(desc("orank"))
        author_org_query = author_org_query.subquery()
        query = query.join(author_org_query, Artifact.id == author_org_query.c.id, isouter=False)

    if owner_keywords:
        if type(owner_keywords) is list:
            owner_keywords = ' or '.join(owner_keywords)
        owner_query = db.session.query(
            User.id, func.ts_rank_cd(Person.person_tsv, func.websearch_to_tsquery("english", owner_keywords)).label("rank")
        ).join(Person, User.person_id == Person.id
        ).filter(Person.person_tsv.op('@@')(func.websearch_to_tsquery("english", owner_keywords))).order_by(desc("rank")).subquery()
        query = query.join(owner_query, Artifact.owner_id == owner_query.c.id, isouter=False)
    if badge_id_list:
        badge_query = db.session.query(ArtifactBadge.artifact_id
            ).join(Badge, Badge.id == ArtifactBadge.badge_id
            ).filter(Badge.id.in_(badge_id_list)
            ).subquery()
        query = query.join(badge_query, Artifact.id == badge_query.c.artifact_id, isouter=False)

    #Add View number to query
    query = query.join(StatsArtifactViews, Artifact.artifact_group_id == StatsArtifactViews.artifact_group_id, isouter=True)
    
    # add filters based on provided parameters
    query = query.filter(ArtifactPublication.id != None)
    if artifact_types:
        if len(artifact_types) > 1:
            query = query.filter(or_(Artifact.type == a_type for a_type in artifact_types))
        else:
            query = query.filter(Artifact.type == artifact_types[0])

    
    pagination = query.paginate(page=page_num, error_out=False, max_per_page=items_per_page)
    result = pagination.items

    artifacts = []
    for row in result:
        artifact, _, num_ratings, avg_rating, num_reviews, view_count = row
        abstract = {
            "id": artifact.id,
            "artifact_group_id": artifact.artifact_group_id,
            "artifact_group": {
                "id": artifact.artifact_group_id,
                "owner_id": artifact.artifact_group.owner_id
            },
            "uri": generate_artifact_uri(artifact.artifact_group_id, artifact_id=artifact.id),
            "doi": artifact.url,
            "type": artifact.type,
            "title": artifact.title,
            "description": artifact.description,
            "avg_rating": float(avg_rating) if avg_rating else None,
            "num_ratings": num_ratings if num_ratings else 0,
            "num_reviews": num_reviews if num_reviews else 0,
            "owner": { "id": artifact.owner.id },
            "views": view_count if view_count else 0
        }
        artifacts.append(abstract)

    return dict(
        page=pagination.page,total=pagination.total,
        pages=int(math.ceil(pagination.total / items_per_page)),
        artifacts=artifacts)

class ArtifactSearchIndexAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='keywords',
                                   type=str,
                                   required=False,
                                   help='missing keywords in query string')
        self.reqparse.add_argument(name='page',
                                   type=int,
                                   required=False,
                                   default=1,
                                   help='page number for paginated results')
        self.reqparse.add_argument(name='items_per_page',
                                   type=int,
                                   required=False,
                                   default=10,
                                   help='items per page for paginated results')
        
        # filters
        self.reqparse.add_argument(name='type',
                                   type=str,
                                   required=False,
                                   action='append',
                                   help='missing type to filter results')
        self.reqparse.add_argument(name='author',
                                   type=str,
                                   required=False,
                                   action='append',
                                   help='missing author to filter results')
        self.reqparse.add_argument(name='organization',
                                   type=str,
                                   required=False,
                                   default='',
                                   action='append',
                                   help='missing organization to filter results')
        self.reqparse.add_argument(name='owner',
                                   type=str,
                                   required=False,
                                   action='append',
                                   help='missing owner to filter results')
        self.reqparse.add_argument(name='badge_id',
                                   type=int,
                                   required=False,
                                   action='append',
                                   help='badge IDs to search for')

        super(ArtifactSearchIndexAPI, self).__init__()


    @staticmethod
    def is_artifact_type_valid(artifact_type):
        return artifact_type in ARTIFACT_TYPES

    def get(self):
        args = self.reqparse.parse_args()
        keywords = args['keywords']
        page_num = args['page']
        items_per_page = args['items_per_page']

        # artifact search filters
        artifact_types = args['type']
        author_keywords = args['author']
        organization = args['organization']
        owner_keywords = args['owner']
        badge_id_list = args['badge_id']

        # sanity checks
        if artifact_types:
            for a_type in artifact_types:
                if not ArtifactSearchIndexAPI.is_artifact_type_valid(a_type):
                    abort(400, description='invalid artifact type passed')

        try:
            stats_search = StatsSearches(
                    search_term=keywords
            )
            db.session.add(stats_search)
            db.session.commit()
        except exc.SQLAlchemyError as error:
            LOG.exception(f'Failed to log search term in the database. Error: {error}')

        result = search_artifacts(keywords, artifact_types, author_keywords, organization, owner_keywords, badge_id_list, page_num, items_per_page)
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

class ArtifactRecommendationAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='page',
                                   type=int,
                                   required=False,
                                   default=1,
                                   help='page number for paginated results')
        

        super(ArtifactRecommendationAPI, self).__init__()
    
    def get(self, artifact_group_id, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)
        args = self.reqparse.parse_args()
        page_num = args['page']

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).filter(
            Artifact.artifact_group_id == artifact_group_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        authors_res = db.session.query(ArtifactAffiliation, Person.name).filter(ArtifactAffiliation.artifact_id == artifact_id).join(Affiliation,Affiliation.id == ArtifactAffiliation.affiliation_id).join(Person, Affiliation.person_id == Person.id).all()

        #Authors of artifact for later
        authors = [res.name for res in authors_res]

    
        top_keywords = db.session.query(ArtifactTag.tag).filter(
            ArtifactTag.artifact_id == artifact_id, ArtifactTag.source.like('%keywords%')).all()
        if not top_keywords:
            response = jsonify({
                "artifacts": {
                    "total": 0, "page": 1, "pages": 1, "artifacts": []
                }, "avg_rating": None, "num_ratings": 0, "authors": []})
        else:
            keywords = [result.tag for result in top_keywords]
            artifacts = search_artifacts(keywords=" or ".join(keywords), artifact_types = ARTIFACT_TYPES, page_num = page_num, items_per_page= 10, author_keywords = None,  organization = None, owner_keywords = None, badge_id_list = None)
            res =  db.session.query(ArtifactRatings.artifact_id, func.count(ArtifactRatings.id).label('num_ratings'), func.avg(ArtifactRatings.rating).label('avg_rating')).group_by("artifact_id").filter(ArtifactRatings.artifact_id == artifact_id).first()
            if res:
                num_ratings = res.num_ratings if res.num_ratings else 0
                avg_rating = round(res.avg_rating,2) if res.avg_rating else None
            else:
                num_ratings = 0
                avg_rating = None
            response = jsonify({"artifacts": artifacts, "avg_rating": float(avg_rating) if avg_rating else None, "num_ratings": num_ratings, "authors": authors})



        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
