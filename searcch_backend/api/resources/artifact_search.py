# logic for /artifacts

from searcch_backend.api.app import db
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, url_for
from flask_restful import reqparse, Resource
from sqlalchemy import func, desc, sql, or_
import math
import logging

LOG = logging.getLogger(__name__)

def generate_artifact_uri(artifact_id):
    return url_for('api.artifact', artifact_id=artifact_id)

def search_artifacts(keywords, artifact_types, author_keywords, organization, owner_keywords, badge_id_list, page_num, items_per_page):
    """ search for artifacts based on keywords, with optional filters by owner and affiliation """
    sqratings = db.session.query(
        ArtifactRatings.artifact_id,
        func.count(ArtifactRatings.id).label('num_ratings'),
        func.avg(ArtifactRatings.rating).label('avg_rating')
    ).group_by("artifact_id").subquery()
    sqreviews = db.session.query(
        ArtifactReviews.artifact_id,
        func.count(ArtifactReviews.id).label('num_reviews')
    ).group_by("artifact_id").subquery()

    # create base query object
    if not keywords:
        query = db.session.query(Artifact,
                                    sql.expression.bindparam("zero", 0).label("rank"),
                                    'num_ratings', 'avg_rating', 'num_reviews'
                                    ).order_by(
                                    db.case([
                                        (Artifact.type == 'software', 1),
                                        (Artifact.type == 'dataset', 2),
                                        (Artifact.type ==
                                        'publication', 3),
                                    ], else_=4)
                                )
        query = query.join(sqratings, Artifact.id == sqratings.c.artifact_id, isouter=True
                        ).join(ArtifactPublication, ArtifactPublication.artifact_id == Artifact.id
                        ).join(sqreviews, Artifact.id == sqreviews.c.artifact_id, isouter=True
                        ).order_by(sqratings.c.avg_rating.desc().nullslast(),sqreviews.c.num_reviews.desc())
    else:
        search_query = db.session.query(ArtifactSearchMaterializedView.artifact_id, 
                                        func.ts_rank_cd(ArtifactSearchMaterializedView.doc_vector, func.websearch_to_tsquery("english", keywords)).label("rank")
                                    ).filter(ArtifactSearchMaterializedView.doc_vector.op('@@')(func.websearch_to_tsquery("english", keywords))
                                    ).subquery()
        query = db.session.query(Artifact, 
                                    search_query.c.rank, 'num_ratings', 'avg_rating', 'num_reviews'
                                    ).join(ArtifactPublication, ArtifactPublication.artifact_id == Artifact.id
                                    ).join(search_query, Artifact.id == search_query.c.artifact_id, isouter=False)
        
        query = query.join(sqratings, Artifact.id == sqratings.c.artifact_id, isouter=True
                        ).join(sqreviews, Artifact.id == sqreviews.c.artifact_id, isouter=True
                        ).order_by(desc(search_query.c.rank))

    if author_keywords or organization:
        rank_list = []
        if author_keywords:
            author_keywords = ' '.join(author_keywords)
            rank_list.append(
                func.ts_rank_cd(Person.person_tsv, func.websearch_to_tsquery("english", author_keywords)).label("arank"))
        if organization:
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
        owner_keywords = ' '.join(owner_keywords)
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
        artifact, _, num_ratings, avg_rating, num_reviews = row
        abstract = {
            "id": artifact.id,
            "uri": generate_artifact_uri(artifact.id),
            "doi": artifact.url,
            "type": artifact.type,
            "title": artifact.title,
            "description": artifact.description,
            "avg_rating": float(avg_rating) if avg_rating else None,
            "num_ratings": num_ratings if num_ratings else 0,
            "num_reviews": num_reviews if num_reviews else 0,
            "owner": { "id": artifact.owner.id }
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

        result = search_artifacts(keywords, artifact_types, author_keywords, organization, owner_keywords, badge_id_list, page_num, items_per_page)
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
