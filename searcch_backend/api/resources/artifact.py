# logic for /artifacts

from searcch_backend.api.app import db, config_name, mail, app
from searcch_backend.api.common.sql import (
    object_from_json, artifact_diff, artifact_clone,
    artifact_apply_curation)
from searcch_backend.api.common.auth import (verify_api_key, has_api_key, has_token, verify_token)
from searcch_backend.api.common.importer import schedule_import
from searcch_backend.api.common.stats import StatsResource
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint, url_for, Response, render_template
from flask_restful import reqparse, Resource, fields, marshal
import sqlalchemy
from sqlalchemy import func, desc, asc, sql, and_, or_, not_, distinct
import datetime
import json
import sys
import logging
import math
import threading
from flask_mail import Message

LOG = logging.getLogger(__name__)

class ArtifactIndexAPI(Resource):

    def __init__(self):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="type", type=str, required=False, action="append",
            help="missing type to filter results")
        self.getparse.add_argument(
            name="published", type=int, required=False,
            help="if 1, show only published artifacts")
        self.getparse.add_argument(
            name="allusers", type=int, required=False, default=0, location="args",
            help="if set 1, and if caller is authorized, show all user artifacts")
        self.getparse.add_argument(
            name="allversions", type=int, required=False, default=0, location="args",
            help="if set 1, and if caller is authorized, show all artifact versions")
        self.getparse.add_argument(
            name="owner", type=str, required=False, location="args",
            help="if set, filter by user email and name")
        self.getparse.add_argument(
            name="artifact_group_id", type=int, required=False, default=None, location="args",
            help="if set, filter by artifact group id")
        self.getparse.add_argument(
            name="short_view_include", type=str, required=False,
            help="Return only fields, unless relations are specified in this field (valid: %s)" % (
                ",".join(Artifact.__mapper__.relationships.keys())))
        self.getparse.add_argument(
            name="page", type=int, required=False,
            help="page number for paginated results")
        self.getparse.add_argument(
            name="items_per_page", type=int, required=False, default=20,
            help="results per page if paginated")
        self.getparse.add_argument(
            name="sort", type=str, required=False, default=None,
            choices=("id", "type", "title", "url", "ctime", "mtime" ),
            help="bad sort field: {error_msg}")
        self.getparse.add_argument(
            name="sort_desc", type=int, required=False, default=1,
            help="if set True, sort descending, else ascending")

        super(ArtifactIndexAPI, self).__init__()

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.getparse.parse_args()
        artifact_types = args['type']

        if artifact_types:
            for a_type in artifact_types:
                if a_type not in ARTIFACT_TYPES:
                    abort(400, description='invalid artifact type passed')

        artifacts = db.session.query(Artifact).\
          join(ArtifactGroup, Artifact.artifact_group_id == ArtifactGroup.id).\
          filter(True if login_session.is_admin and args["allusers"] \
                      else (Artifact.owner_id == login_session.user_id \
                            or ArtifactGroup.owner_id == login_session.user_id))
        if not args.allversions:
            artifacts = artifacts.distinct(Artifact.artifact_group_id)
        if args.artifact_group_id is not None:
            artifacts = artifacts.\
              filter(Artifact.artifact_group_id == args.artifact_group_id)
        if not args.allversions:
            # If an artifact group has a current publication, only return that.
            if args.published == 1:
                artifacts = artifacts.\
                  join(ArtifactPublication, ArtifactGroup.publication_id == ArtifactPublication.id)
                artifacts = artifacts.\
                  filter(ArtifactPublication.artifact_id == Artifact.id)
        if artifact_types:
            artifacts = artifacts.\
              filter(Artifact.type.in_(artifact_types))
        if args["published"] == 1:
            artifacts = artifacts.\
              filter(Artifact.publication != None)
        elif args["published"] == 0:
            artifacts = artifacts.\
              filter(Artifact.publication == None)
        if args["owner"]:
            owner_cond = "%" + args["owner"] + "%"
            artifacts = artifacts.\
              join(User, Artifact.owner_id == User.id).\
              join(Person, User.person_id == Person.id)
            artifacts = artifacts.\
              filter(or_(Person.name.ilike(owner_cond),
                         Person.email.ilike(owner_cond)))
        # We need a default sort order that has artifact_group_id as the
        # primary column, so that the possible above distinct() clause works in
        # postgres -- it requires that the distinct on column be the
        # first-ordered column.  So, if we have custom sort, we turn this into
        # a subquery and re-sort the subquery.
        artifacts = artifacts.\
          order_by(desc(Artifact.artifact_group_id),
                   desc(Artifact.id))

        if args.sort:
            artifacts = db.session.query(Artifact).\
              select_entity_from(artifacts.subquery())
            if args.sort_desc:
                artifacts = artifacts.\
                  order_by(desc(args.sort))
            else:
                artifacts = artifacts.\
                  order_by(asc(args.sort))

        pagination = None
        if "page" in args and args["page"]:
            if args["items_per_page"] <= 0:
                args["items_per_page"] = sys.maxsize
            pagination = artifacts.paginate(
                page=args["page"], error_out=False, per_page=args["items_per_page"])
            artifacts = pagination.items
        else:
            artifacts = artifacts.all()

        exclude = []
        if args["short_view_include"] is not None:
            sva = args["short_view_include"].split(",")
            exclude = list(Artifact.__mapper__.relationships.keys())
            for x in sva:
                if not x in exclude:
                    abort(401, description="invalid short_view_include relation")
                exclude.remove(x)

        response_dict = {
            "artifacts": ArtifactSchema(
                many=True,exclude=exclude).dump(artifacts)
        }
        if pagination:
            response_dict["page"] = pagination.page
            response_dict["total"] = pagination.total
            response_dict["pages"] = int(math.ceil(pagination.total / args["items_per_page"]))

        response = jsonify(response_dict)

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def post(self):
        """
        Creates a new artifact from the given JSON document, without invoking the importer.
        """
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)

        data = request.json
        if "artifact" in data:
            data = data["artifact"]
        artifact = object_from_json(db.session, Artifact, data, skip_primary_keys=True,
                                    error_on_primary_key=False, allow_fk=True)
        if not artifact.ctime:
            artifact.ctime = datetime.datetime.now()
        if login_session:
            artifact.owner = login_session.user
        artifact_group = ArtifactGroup(owner=artifact.owner, next_version=0)
        artifact.artifact_group = artifact_group
        db.session.add(artifact_group)

        # If we were given a publication record, set its version.  Note that we
        # cannot update the artifact_group.publication record until we commit
        # the state.  That happens below, after the first commit.
        if artifact.publication:
            artifact.publication.version = artifact_group.next_version
            artifact_group.next_version += 1

        db.session.add(artifact)
        fake_module_name = "manual"
        if not login_session:
            fake_module_name = "cli-export"
        fake_artifact_import = ArtifactImport(
            type=artifact.type,url=artifact.url,importer_module_name=fake_module_name,
            owner=artifact.owner,ctime=artifact.ctime,status="completed",
            phase="done",artifact=artifact)
        db.session.add(fake_artifact_import)
        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            # psycopg2.errors.UniqueViolation:
            ex = sys.exc_info()[1]
            LOG.exception(ex)
            msg = None
            try:
                msg = "%r" % (ex.args)
            except:
                pass
            if not msg:
                msg = "malformed object"
            abort(400, description=msg)
        except:
            LOG.exception(sys.exc_info()[1])
            abort(500)

        # Refresh to pick up committed state, as well as for updating
        # artifact_group.publication record.
        db.session.refresh(artifact)

        # If there had been a publication sent to us (e.g. via importer
        # artifact.export), now that it has been added above, we need to update
        # the artifact_group to point to it.  But we could not do that before,
        # since there would have been a circular dep.  And this is safe to do
        # without error in a second transaction.
        if artifact.publication:
            db.session.refresh(artifact_group)
            artifact_group.publication = artifact.publication
            db.session.commit()

        response = jsonify(dict(artifact=ArtifactSchema().dump(artifact)))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200

        return response


class ArtifactAPI(Resource):

    def __init__(self):
        self.postparse = reqparse.RequestParser()
        self.postparse.add_argument(
            name="reimport", type=bool, required=False, default=False,
            help="set reimport `true` to reimport into a new version")

        super(ArtifactAPI, self).__init__()

    def get(self, artifact_group_id, artifact_id=None):
        if has_api_key(request):
            verify_api_key(request)

        # Verify the group exists
        artifact_group = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).first()
        if not artifact_group:
            abort(404, description="nonexistent artifact group")

        #
        # Determine which artifact record to return.
        #
        # If the artifact_id is not specified, there must be a publication
        # record for the group, unless: 1) caller is owner and has a draft; 2)
        # caller is admin and gets the most recent draft.  I do not like this
        # because it might be confusing, but we have to do it because a user
        # can add a relationship to an unpublished artifact (and
        # favorite/review/rate it), and we don't want to break the frontend for
        # the user or admins.
        #
        # If the artifact_id is specified, and if it is published, anyone can
        # retrieve it.  If not published, only the owner of the group or of the
        # artifact, or an admin, may retrieve it.
        #
        artifact = None
        if not artifact_id:
            if not artifact_group.publication:
                login_session = None
                if has_token(request):
                    login_session = verify_token(request)
                if not (login_session
                        and (login_session.user_id == artifact_group.owner_id
                             or login_session.is_admin)):
                    abort(400, description="insufficient permission to access unpublished artifact")
                # Find the most recent owner draft
                artifact = db.session.query(Artifact)\
                  .filter(Artifact.artifact_group_id == artifact_group_id)\
                  .filter(Artifact.owner_id == artifact_group.owner_id)\
                  .order_by(desc(Artifact.ctime))\
                  .first()
            else:
                artifact = artifact_group.publication.artifact
        else:
            res = db.session.query(Artifact, ArtifactPublication)\
              .join(ArtifactPublication, ArtifactPublication.artifact_id == Artifact.id, isouter=True)\
              .filter(and_(Artifact.id == artifact_id,Artifact.artifact_group_id == artifact_group_id))\
              .first()
            if not res:
                abort(404, description="no such artifact")
            (artifact, publication) = res
            if not artifact:
                abort(404, description="no such artifact")
            if not publication:
                login_session = None
                if has_token(request):
                    login_session = verify_token(request)
                if not (login_session
                        and (login_session.user_id == artifact_group.owner_id
                             or login_session.user_id == artifact.owner_id
                             or login_session.is_admin)):
                    abort(400, description="insufficient permission to access artifact")

        # get average rating for the artifact, number of ratings
        rating_aggregates = db.session.query(ArtifactRatings.artifact_group_id, func.count(ArtifactRatings.id).label('num_ratings'), func.avg(
            ArtifactRatings.rating).label('avg_rating')).filter(ArtifactRatings.artifact_group_id == artifact_group.id).group_by("artifact_group_id").all()

        ratings = db.session.query(ArtifactRatings, ArtifactReviews).join(ArtifactReviews, and_(
            ArtifactRatings.user_id == ArtifactReviews.user_id,
            ArtifactRatings.artifact_group_id == ArtifactReviews.artifact_group_id
        )).filter(ArtifactRatings.artifact_group_id == artifact_group.id).all()

        # Record Artifact view in database
        # XXX: need to handle API-only case.
        session_id = request.cookies.get('session_id')
        if session_id:
            stat_view_obj = StatsResource(artifact_group_id=artifact_group_id, session_id=session_id)
            stat_view_obj.recordView()

        response = jsonify({
            "artifact": ArtifactSchema().dump(artifact),
            "avg_rating": float(rating_aggregates[0][2]) if rating_aggregates else None,
            "num_ratings": rating_aggregates[0][1] if rating_aggregates else 0,
            "num_reviews": len(ratings) if ratings else 0,
            "rating_review": [{
                "rating": ArtifactRatingsSchema(only=("rating",)).dump(rating), 
                "review": ArtifactReviewsSchema(exclude=("artifact_group_id", "user_id")).dump(review)
                } for rating, review in ratings]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_group_id, artifact_id=None):
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)

        artifact_group = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).first()
        if not artifact_group:
            abort(404, description="nonexistent artifact group")
        # We can only modify specific versions.
        if not artifact_id:
            abort(400, description="can only modify specific artifacts; must supply artifact_id")

        # We can only change unpublished artifacts unless admin.
        artifact = db.session.query(Artifact)\
          .filter(Artifact.id == artifact_id)\
          .filter(Artifact.artifact_group_id == artifact_group_id)\
          .first()
        if not artifact:
            abort(404, description="no such artifact")
        if login_session and not login_session.is_admin and artifact.owner_id != login_session.user_id:
            abort(401, description="insufficient permission to modify artifact")
        if artifact.publication and not login_session.is_admin:
            abort(403, description="artifact already published; cannot modify")
        if not request.is_json:
            abort(400, description="request body must be a JSON representation of an artifact")

        data = request.json

        replay_results = None
        if "replay_curations" in data and data["replay_curations"]:
            if artifact.curations:
                abort(400, description="cannot replay past curations once you have edited an artifact")

            # Take a backwards-slice of curations using artifact.parent_id
            curations = []
            parent_id = artifact.parent_id
            while parent_id:
                res = db.session.query(ArtifactCuration).filter(ArtifactCuration.artifact_id == parent_id).all()
                if res:
                    tmp = res
                    tmp.extend(curations)
                    curations = tmp
                parent_id = db.session.query(Artifact.parent_id).filter(Artifact.id == parent_id).first()

            LOG.debug("curation: replaying %r",curations)

            # Apply the curations
            replay_results = []
            with db.session.no_autoflush:
                for curation in curations:
                    (status,message) = artifact_apply_curation(db.session, artifact, curation)
                    replay_results.append(
                        dict(status=status,message=message,curation=ArtifactCurationSchema().dump(curation)))

                try:
                    db.session.commit()
                    db.session.refresh(artifact)
                except:
                    ex = sys.exc_info()[1]
                    LOG.exception(ex)
                    db.session.rollback()
                    abort(500, description="unexpected internal error during curation replay: %r" % (ex,))

        artifact_data = data
        if "artifact" in data:
            artifact_data = data["artifact"]
        if "artifact" in data or len(data) > 1:
            mod_artifact = None
            with db.session.no_autoflush:
                try:
                    # Beware -- in order to use this diff-style comparison,
                    # mod_artifact must be a fully-valid object.  For instance, if
                    # we do not manually set mod_artifact.owner, and try to display
                    # via repr when DEBUG, sqlalchemy will whine that it cannot
                    # refresh the object if a refresh is attempted.  This is a bit
                    # odd, given that mod_artifact is not in the session, but it is
                    # how things work.
                    #
                    mod_artifact = object_from_json(
                        db.session, Artifact, artifact_data, skip_primary_keys=False,
                        error_on_primary_key=False, should_query=True, allow_fk=True)
                    mod_artifact.owner = artifact.owner
                except:
                    LOG.exception(sys.exc_info()[1])
                    abort(400, description="cannot parse updated artifact: %s" % (
                        repr(sys.exc_info()[1])))
                if not mod_artifact:
                    abort(400, description="cannot parse updated artifact")

                curations = None
                try:
                    curator = login_session.user if login_session else artifact.owner
                    curations = artifact_diff(db.session, curator, artifact, artifact, mod_artifact)
                    if curations:
                        artifact.mtime = datetime.datetime.now()
                        db.session.add_all(curations)
                        db.session.add(artifact)
                except sqlalchemy.exc.IntegrityError:
                    ex = sys.exc_info()[1]
                    LOG.exception(ex)
                    abort(400, description="malformed input: %r" % (ex.args,))
                except (TypeError, ValueError):
                    ex = sys.exc_info()[1]
                    LOG.exception(ex)
                    db.session.rollback()
                    if ex.args:
                        abort(500, description="%r" % (ex.args))
                    else:
                        abort(500, description="%r" % (ex))
                except:
                    ex = sys.exc_info()[1]
                    LOG.exception(ex)
                    db.session.rollback()
                    abort(500, description="unexpected internal error")

        if "publication" in data and data["publication"] is not None \
          and not artifact.publication:
            notes = None
            if data["publication"].get("notes",None):
                notes = data["publication"]["notes"]
            now = datetime.datetime.now()
            publication = ArtifactPublication(
                artifact_id=artifact.id, publisher_id=artifact.owner_id,
                version=artifact.artifact_group.next_version,
                time=now,notes=notes)
            db.session.add(publication)
            db.session.commit()
            db.session.refresh(publication)
            artifact_group.publication = publication
            artifact.publication = publication
            artifact.artifact_group.next_version += 1
            # Automatically archive the artifact.
            artifact_import = db.session.query(ArtifactImport).\
              filter(ArtifactImport.artifact_id == artifact.id).\
              first()
            if artifact_import:
                artifact_import.archived = True
            artifact.mtime = now
        db.session.commit()
        db.session.refresh(artifact)

        ret = dict(artifact=ArtifactSchema().dump(artifact))
        if replay_results is not None:
            ret["replay_results"] = replay_results
        response = jsonify(ret)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200

        return response

    def _delete_artifact(self, artifact_group_id, artifact_id):
        artifact_group = db.session.query(ArtifactGroup).\
          filter(ArtifactGroup.id == artifact_group_id).\
          first()

        artifact = db.session.query(Artifact).\
          filter(Artifact.id == artifact_id).\
          first()

        # If currently importing, delete that first, and commit:
        artifact_import = db.session.query(ArtifactImport).\
          filter(ArtifactImport.artifact_id == artifact_id).\
          first()
        if artifact_import:
            schedule = db.session.query(ImporterSchedule).\
              filter(ImporterSchedule.artifact_import_id == artifact_import.id).\
              first()
            if schedule:
                db.session.delete(schedule)
            db.session.delete(artifact_import)

        #db.session.refresh(artifact)

        # If artifact is referenced by an ArtifactPublication, and if that
        # publication is the current one referenced by the ArtifactGroup,
        # remove all that.
        if artifact.publication:
            if artifact.publication.id == artifact_group.publication_id:
                artifact_group.publication_id = None
            db.session.delete(artifact.publication)

        # Update Artifact "member" tables that are primarily related to the
        # group, but index the related artifact version specifically.
        indexing = [ ArtifactRatings, ArtifactReviews, ArtifactFavorites ]
        for table in indexing:
            records = db.session.query(table).\
              filter(getattr(table, "artifact_id") == artifact_id).\
              all()
            for record in records:
                record.artifact_id = None
        # Handle ArtifactRelationship specially, since it has pointers to both
        # artifact_id and related_artifact_id.
        records = db.session.query(ArtifactRelationship).\
          filter(or_(ArtifactRelationship.artifact_id == artifact_id,\
                     ArtifactRelationship.artifact_id == artifact_id)).\
          all()
        for record in records:
          if record.artifact_id == artifact_id:
            record.artifact_id = None
          if record.related_artifact_id == artifact_id:
            record.related_artifact_id = None

        # Delete all the Artifact "member" table records.
        for af in getattr(artifact, "files", []):
            for afm in getattr(af, "members", []):
                db.session.delete(afm)
            af.members = []
            db.session.delete(af)
        artifact.files = []
        many = [ "meta", "tags", "curations", "affiliations", "releases",
                 "badges", "funding", "releases" ]
        for field in many:
            for x in getattr(artifact, field, []):
                db.session.delete(x)
            setattr(artifact, field, [])

        # If anyone's parent_id is us, unlink that.
        records = db.session.query(Artifact).\
          filter(Artifact.parent_id == artifact_id).\
          all()
        for record in records:
            record.parent_id = None

        db.session.delete(artifact)
        db.session.commit()

    def _maybe_delete_artifact_group(self, artifact_group_id):
        artifact_group = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).first()
        artifacts = db.session.query(Artifact).\
          filter(Artifact.artifact_group_id == artifact_group_id).\
          all()
        if artifacts:
            # Still artifact versions; don't delete the group.
            return

        # Update Artifact "member" tables that are primarily related to the
        # group, but index the related artifact version specifically.
        tables = [ ArtifactRatings, ArtifactReviews, ArtifactFavorites, StatsRecentViews, StatsArtifactViews ]
        for table in tables:
            records = db.session.query(table).\
              filter(getattr(table, "artifact_group_id") == artifact_group_id).\
              all()
            for record in records:
                db.session.delete(record)
        # Handle ArtifactRelationship specially, since it has pointers to both
        # artifact_group_id and related_artifact_group_id.
        records = db.session.query(ArtifactRelationship).\
          filter(or_(ArtifactRelationship.artifact_group_id == artifact_group_id,\
                     ArtifactRelationship.artifact_group_id == artifact_group_id)).\
          all()
        for record in records:
            if record.artifact_group_id == artifact_group_id:
                db.session.delete(record)
            if record.related_artifact_group_id == artifact_group_id:
                db.session.delete(record)

        # Finally delete the group object.
        db.session.delete(artifact_group)
        db.session.commit()

    def delete(self, artifact_group_id, artifact_id=None):
        verify_api_key(request)
        login_session = verify_token(request)

        # We can only delete unpublished artifacts.
        artifact_group = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).first()
        if not artifact_group:
            abort(404, description="nonexistent artifact group")
        # We can only delete specific versions unless admin.
        if not artifact_id and not login_session.is_admin:
            abort(400, description="can only delete specific artifacts; must supply artifact_id")

        artifacts = []
        if artifact_id:
            artifact = db.session.query(Artifact).\
              filter(Artifact.id == artifact_id).\
              first()
            if not artifact:
                abort(404, description="no such artifact")
            if not (login_session.is_admin or artifact.owner_id == login_session.user_id or artifact_group.owner_id == login_session.user_id):
                abort(401, description="insufficient permission to delete artifact")
            if artifact.publication and not login_session.is_admin:
                abort(403, description="artifact already published; cannot delete")
            artifacts.append(artifact)
        else:
            artifacts = db.session.query(Artifact).\
              filter(Artifact.artifact_group_id == artifact_group_id).\
              all()

        for artifact in artifacts:
            try:
                self._delete_artifact(artifact.artifact_group_id, artifact.id)
            except:
                LOG.error("failed to delete artifact %r", artifact.id)
                LOG.exception(sys.exc_info()[1])
                abort(500, description="failed to delete artifact %r" % (artifact.id,))

        # If the artifact_group is now empty, remove it.
        try:
            self._maybe_delete_artifact_group(artifact_group_id)
        except:
            LOG.error("failed to delete artifact_group %r", artifact_group_id)
            LOG.exception(sys.exc_info()[1])
            abort(500, description="failed to delete artifact_group %r" % (artifact_group_id,))

        return Response(status=200)

    def post(self, artifact_group_id, artifact_id=None):
        """Creates a new artifact version"""
        verify_api_key(request)
        login_session = verify_token(request)

        # We can only modify specific versions.
        if not artifact_id:
            abort(400, description="can only create new version from a specific artifact; must supply artifact_id")

        # We can only change unpublished artifacts unless admin.
        artifact = db.session.query(Artifact).\
          filter(Artifact.id == artifact_id)\
          .first()
        if not artifact:
            abort(404, description="no such artifact")
        if not login_session.is_admin and artifact.artifact_group.owner_id != login_session.user_id:
            abort(401, description="insufficient permission to modify artifact")
        if not artifact.publication:
            abort(403, description="artifact not published; cannot create new version from unpublished artifact")

        #j = request.json
        args = self.postparse.parse_args()
        response = None
        if args.reimport: #j and getattr(j,"reimport",False):
            res = db.session.query(ArtifactImport).\
              filter(ArtifactImport.url == artifact.url).\
              filter(ArtifactImport.owner_id == login_session.user_id).\
              filter(ArtifactImport.artifact_id == None).\
              filter(not_(ArtifactImport.status.in_(["completed","failed"]))).\
              all()
            if len(res) > 0:
                abort(400, description="user_id %r already importing from %r" % (login_session.user_id,artifact.url))

            dt = datetime.datetime.now()
            ai = ArtifactImport(
                type=artifact.type,url=artifact.url,
                artifact_group_id=artifact.artifact_group_id,
                parent_artifact_id=artifact.id,owner_id=login_session.user_id,
                ctime=dt,mtime=dt,status="pending",phase="start",archived=False)
            ims = ImporterSchedule(artifact_import=ai)
            db.session.add(ai)
            db.session.add(ims)
            db.session.commit()
            db.session.refresh(ai)

            LOG.debug("scheduling %r" % (ai,))
            threading.Thread(target=schedule_import,name="schedule_import").start()

            response = jsonify({"artifact_import": ArtifactImportSchema().dump(ai)})
        else:
            cloned_artifact = artifact_clone(artifact)
            cloned_artifact.owner_id = login_session.user_id
            cloned_artifact.ctime = datetime.datetime.now()
            cloned_artifact.parent_id = artifact.id

            try:
                db.session.add(cloned_artifact)
                db.session.commit()
            except:
                LOG.error("failed to add cloned artifact %r", cloned_artifact)
                LOG.exception(sys.exc_info()[1])
                abort(500, description="failed to add cloned artifact (source id %r/%r)" % (artifact_group_id, artifact_id,))

            response = jsonify({"artifact": ArtifactSchema().dump(cloned_artifact)})

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200

        return response


class ArtifactRelationshipResourceRoot(Resource):
    def __init__(self):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(name='artifact_group_id',
                                   type=int,
                                   required=True,
                                   help='artifact group id to filter')
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='artifact_group_id',
                                   type=int,
                                   required=True,
                                   help='source artifact')
        self.reqparse.add_argument(name='relation',
                                   type=str,
                                   required=True,
                                   choices=RELATION_TYPES,
                                   help='relation from artifact_group_id to related_artifact_group_id')
        self.reqparse.add_argument(name='related_artifact_group_id',
                                   type=int,
                                   required=True,
                                   help='related artifact')

        super(ArtifactRelationshipResourceRoot, self).__init__()

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.getparse.parse_args()
        artifact_group_id = args["artifact_group_id"]

        # check for valid artifact id
        artifact_group = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).first()
        if not artifact_group:
            abort(400, description='invalid artifact group ID')

        # get all relationships
        relationships = ArtifactRelationship.query.filter_by(artifact_group_id=artifact_group_id).all()

        response = jsonify({"artifact_relationships": ArtifactRelationshipSchema(many=True, exclude=['related_artifact_group']).dump(relationships)})

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def post(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()

        artifact_group_id = args['artifact_group_id']
        relation = args['relation']
        related_artifact_group_id = args['related_artifact_group_id']

        # check for valid artifact id
        artifact_group = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).first()
        if not artifact_group:
            abort(400, description='invalid artifact group ID')

        # check for valid artifact ownership
        if artifact_group.owner_id != login_session.user_id and not login_session.is_admin:
            abort(400, description='insufficient permission: must own source artifact group')
            
        # Check if we are updating an existing relationship
        queried_relationship = ArtifactRelationship.query.filter_by(artifact_group_id=artifact_group_id, relation=relation, related_artifact_group_id=related_artifact_group_id).first()

        if queried_relationship:
            abort(403, description='relationship already exists')

        # insert the new relation
        new_relationship = ArtifactRelationship(
            artifact_group_id=artifact_group_id, relation=relation,
            related_artifact_group_id=related_artifact_group_id,
            artifact_id=artifact_group.publication_id)
        db.session.add(new_relationship)
        db.session.commit()
        db.session.refresh(new_relationship)

        response = jsonify({"artifact_relationship": ArtifactRelationshipSchema(many=False, exclude=['related_artifact_group']).dump(new_relationship)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


class ArtifactRelationshipResource(Resource):
    def __init__(self):
        self.putparse = reqparse.RequestParser()
        self.putparse.add_argument(
            name='relation',type=str,required=True,choices=RELATION_TYPES,
            help='missing relation between the two artifacts')

        super(ArtifactRelationshipResource, self).__init__()

    def get(self, artifact_relationship_id):
        verify_api_key(request)
        login_session = verify_token(request)

        # check for valid artifact_relationship id
        artifact_relationship = db.session.query(ArtifactRelationship).filter(
            ArtifactRelationship.id == artifact_relationship_id).first()
        if not artifact_relationship:
            abort(400, description='invalid artifact_relationship ID')

        response = jsonify(ArtifactRelationshipSchema(many=False, exclude=['related_artifact_group']).dump(artifact_relationship))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_relationship_id):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.putparse.parse_args()

        relation = args['relation']

        # check for valid artifact_relationship id
        artifact_relationship = db.session.query(ArtifactRelationship).filter(
            ArtifactRelationship.id == artifact_relationship_id).first()
        if not artifact_relationship:
            abort(400, description='invalid artifact_relationship ID')
        artifact_group_id = artifact_relationship.artifact_group_id

        # check for valid artifact_relationship ownership (via artifact)
        artifact_relationship_ownership = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).\
            filter(True if login_session.is_admin else ArtifactGroup.owner_id == login_session.user_id).\
            first()
        if not artifact_relationship_ownership:
            abort(400, description='insufficient permission: must own source artifact group')

        artifact_relationship.relation = relation
        db.session.commit()

        response = jsonify({"message": "updated artifact_relationship"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def delete(self, artifact_relationship_id):
        verify_api_key(request)
        login_session = verify_token(request)

        # check for valid artifact_relationship id
        artifact_relationship = db.session.query(ArtifactRelationship).filter(
            ArtifactRelationship.id == artifact_relationship_id).first()
        if not artifact_relationship:
            abort(400, description='invalid artifact_relationship ID')
        artifact_group_id = artifact_relationship.artifact_group_id

        # check for valid artifact ownership
        artifact_ownership = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).\
            filter(True if login_session.is_admin else ArtifactGroup.owner_id == login_session.user_id).\
            first()
        if not artifact_ownership:
            abort(400, description='insufficient permission: must own source artifact')

        db.session.delete(artifact_relationship)
        db.session.commit()
        response = jsonify({"message": "deleted artifact_relationship"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

class ArtifactOwnerRequestAPI(Resource):
    def __init__(self):
        self.postparse = reqparse.RequestParser()
        self.postparse.add_argument(name='message',
                                   type=str,
                                   required=True,
                                   help='reason for owernship request')

        super(ArtifactOwnerRequestAPI, self).__init__()

    def get(self, artifact_group_id):
        """Sends the existing ownership request if any"""
        verify_api_key(request)
        login_session = verify_token(request)

        #Check if artifact exists
        artifact_group = db.session.query(ArtifactGroup).filter(ArtifactGroup.id == artifact_group_id).first()
        if not artifact_group:
            abort(404, description="no such artifact group")
        if artifact_group.owner_id == login_session.user_id:
            response = jsonify({"artifact_owner_request": {"message": "You are the owner of this artifact.", "error": True}})
        else:
            #Check if any pending requests
            artifact_owner_request = db.session.query(ArtifactOwnerRequest).filter(and_(ArtifactOwnerRequest.user_id == login_session.user_id, ArtifactOwnerRequest.status == "pending", ArtifactOwnerRequest.artifact_group_id == artifact_group_id)).first()
            if artifact_owner_request:
                response = jsonify({"artifact_owner_request": ArtifactOwnerRequestSchema().dump(artifact_owner_request)})
            else:
                response = jsonify({"artifact_owner_request": None})

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


    def post(self, artifact_group_id):
        """Creates a new request for artifact ownership"""
        verify_api_key(request)
        login_session = verify_token(request)

        #Check if already an owner
        artifact_group = db.session.query(ArtifactGroup).filter(ArtifactGroup.id == artifact_group_id).first()
        if not artifact_group:
            abort(404, description="no such artifact group")
        if artifact_group.owner_id == login_session.user_id:
            abort(404, description="cannot process request, already an owner")
        #Check if any pending requests
        artifact_owner_request = db.session.query(ArtifactOwnerRequest).filter(and_(ArtifactOwnerRequest.user_id == login_session.user_id, ArtifactOwnerRequest.status == "pending", ArtifactOwnerRequest.artifact_group_id == artifact_group_id)).first()
        if artifact_owner_request:
            abort(404, description="cannot process request, pending request already exists")

        args = self.postparse.parse_args()
        dt = datetime.datetime.now()
        new_artifact_owner_request = ArtifactOwnerRequest(
            user_id=login_session.user_id,
            artifact_group_id=artifact_group_id, message=args.message,
            ctime=dt, status="pending")
        db.session.add(new_artifact_owner_request)
        db.session.commit()

        mail_data = db.session.query(ArtifactOwnerRequest, User, Person, Artifact).\
          join(User, ArtifactOwnerRequest.user_id == User.id).\
          join(Person, User.person_id == Person.id).\
          join(Artifact, ArtifactOwnerRequest.artifact_group_id == Artifact.artifact_group_id).\
          filter(ArtifactOwnerRequest.id == new_artifact_owner_request.id).\
          first()

        msg_recipients = [mail_data.Person.email, *app.config['ADMIN_MAILING_RECIPIENTS']]
        msg = Message(f'Artifact Ownership Claim - Artifact Group ID: {mail_data.Artifact.artifact_group_id}')

        for recipient in msg_recipients:
            if not recipient:
                continue
            msg.recipients = [recipient]
            is_admin = (recipient in app.config['ADMIN_MAILING_RECIPIENTS'])
            msg.html = render_template("ownership_request_email_pending.html",\
                artifact_group_id=mail_data.Artifact.artifact_group_id, \
                artifact_link=f'{app.config["FRONTEND_URL"]}/artifact/{mail_data.Artifact.artifact_group_id}',\
                artifact_title=mail_data.Artifact.title,\
                user_id=mail_data.User.id,\
                user_name=mail_data.Person.name,\
                user_email=mail_data.Person.email,
                justification=mail_data.ArtifactOwnerRequest.message,
                admin=is_admin,
                admin_link=f'{app.config["FRONTEND_URL"]}/admin/claims')
            mail.send(msg)

        response = jsonify({"message": "artifact ownership saved successfully"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

class ArtifactOwnerRequestsAPI(Resource):
    def __init__(self):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="allusers", type=int, required=False, default=0, location="args",
            help="if set 1, and if caller is authorized, show all user artifacts")
        self.getparse.add_argument(
            name="page", type=int, required=False,
            help="page number for paginated results")
        self.getparse.add_argument(
            name="items_per_page", type=int, required=False, default=20,
            help="results per page if paginated")
        self.getparse.add_argument(
            name="user", type=str, required=False, default="",
            help="user id/name")
        self.getparse.add_argument(
            name="artifact", type=str, required=False, default="",
            help="artifact id/name")
        self.getparse.add_argument(
            name="sort", type=str, required=False, default="",
            help="sort by")
        self.getparse.add_argument(
            name="sort_desc", type=int, required=False, default=0,
            help="sort order")

        self.putparse = reqparse.RequestParser()
        self.putparse.add_argument(
            name='artifact_owner_request_id',type=int,required=True,
            help='artifact ownership request id')
        self.putparse.add_argument(
            name='action',type=str,required=True,choices=["approve", "reject"],
            help='missing action type')
        self.putparse.add_argument(
            name='message',type=str,required=True,
            help='reason for selected request action')

        super(ArtifactOwnerRequestsAPI, self).__init__()

    def get(self):
        """Get artifact owernship request according to the logged user and passed settings"""
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.getparse.parse_args()

        artifact_owner_requests = db.session.query(ArtifactOwnerRequest).\
          filter(and_(True if login_session.is_admin and args["allusers"] \
                      else ArtifactOwnerRequest.user_id == login_session.user_id, \
                        ArtifactOwnerRequest.status == "pending"))

        artifact_owner_requests = artifact_owner_requests.\
          join(User, ArtifactOwnerRequest.user_id == User.id).\
          join(Person, User.person_id == Person.id).\
          join(Artifact, ArtifactOwnerRequest.artifact_group_id == Artifact.artifact_group_id)


        if "user" in args:
            if args["user"].isnumeric():
                artifact_owner_requests = artifact_owner_requests.filter(ArtifactOwnerRequest.user_id == int(args["user"]))
            else:
                user_cond = "%" + args["user"] + "%"
                artifact_owner_requests = artifact_owner_requests.\
                filter(Person.name.ilike(user_cond))

        if "artifact" in args:
            if args["artifact"].isnumeric():
                artifact_owner_requests = artifact_owner_requests.filter(ArtifactOwnerRequest.artifact_group_id == int(args["artifact"]))
            else:
                artifact_cond = "%" + args["artifact"] + "%"
                artifact_owner_requests = artifact_owner_requests.\
                filter(Artifact.title.ilike(artifact_cond))

        sort_keys = {
            "artifact_group_id": "artifact_group_id",
            "user.id": "user_id",
            "user.person.name": "name",
            "artifact_title": "title",
            "id": "id"
        }

        if args["sort"]=="":
            args["sort"] = "id"
        args["sort"] = sort_keys[args["sort"]]

        if (args["sort"] == "name"):
            table_obj = Person
        elif (args["sort"] == "title"):
            table_obj = Artifact
        else:
            table_obj = ArtifactOwnerRequest

        if args["sort_desc"]==1:
            artifact_owner_requests = artifact_owner_requests.\
              order_by(desc(getattr(table_obj,args["sort"])))
        else:
            artifact_owner_requests = artifact_owner_requests.\
              order_by(asc(getattr(table_obj,args["sort"])))

        pagination = None
        if "page" in args and args["page"]:
            if args["items_per_page"] <= 0:
                args["items_per_page"] = sys.maxsize
            pagination = artifact_owner_requests.paginate(
                page=args["page"], error_out=False, per_page=args["items_per_page"])
            artifact_owner_requests = pagination.items
        else:
            artifact_owner_requests = artifact_owner_requests.all()

        response_dict = {
            "artifact_owner_requests": ArtifactOwnerRequestSchema(many=True).dump(artifact_owner_requests)
        }
        if pagination:
            response_dict["page"] = pagination.page
            response_dict["total"] = pagination.total
            response_dict["pages"] = int(math.ceil(pagination.total / args["items_per_page"]))

        response = jsonify(response_dict)

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self):
        """Take action on request"""
        verify_api_key(request)
        login_session = verify_token(request)

        if not login_session.is_admin:
            abort(401, description="insufficient permission to take action")

        args = self.putparse.parse_args()
        artifact_owner_request = db.session.query(ArtifactOwnerRequest).filter(ArtifactOwnerRequest.id == args.artifact_owner_request_id).first()
        if not artifact_owner_request:
            abort(404, description="no such artifact owner request")
        if artifact_owner_request.status != "pending":
            abort(404, description="cannot take action on already executed requests")

        # # Update Database
        if args.action == "approve":
            artifact_owner_request.status = "approved"
            artifact_group = db.session.query(ArtifactGroup).\
              filter(ArtifactGroup.id == artifact_owner_request.artifact_group_id).\
              first()
            artifact_group.owner_id = artifact_owner_request.user_id
        else:
            artifact_owner_request.status = "rejected"
        artifact_owner_request.action_message = args.message
        artifact_owner_request.action_time = datetime.datetime.now()
        artifact_owner_request.action_by_user_id = login_session.user_id

        db.session.commit()

        # Send mail to raise approval request

        mail_data = db.session.query(ArtifactOwnerRequest, User, Person, Artifact).\
          join(User, ArtifactOwnerRequest.user_id == User.id).\
          join(Person, User.person_id == Person.id).\
          join(Artifact, ArtifactOwnerRequest.artifact_group_id == Artifact.artifact_group_id).\
          filter(ArtifactOwnerRequest.id == args.artifact_owner_request_id).\
          first()

        msg = Message(f'Artifact Ownership Claim - Artifact Group ID: {mail_data.Artifact.artifact_group_id}')
        
        recipients = app.config['ADMIN_MAILING_RECIPIENTS']
        if mail_data.Person.email:
            recipients.append(mail_data.Person.email)
        
        msg.recipients = recipients

        if mail_data.ArtifactOwnerRequest.status == "approved":
            msg.html = render_template("ownership_request_email_approved.html",\
                artifact_group_id=mail_data.Artifact.artifact_group_id, \
                artifact_link=f'{app.config["FRONTEND_URL"]}/artifact/{mail_data.Artifact.artifact_group_id}',\
                artifact_title=mail_data.Artifact.title,\
                user_id=mail_data.User.id,\
                user_name=mail_data.Person.name,\
                user_email=mail_data.Person.email,
                justification=mail_data.ArtifactOwnerRequest.action_message)
        else:
            msg.html = render_template("ownership_request_email_rejected.html",\
                artifact_group_id=mail_data.Artifact.artifact_group_id, \
                artifact_link=f'{app.config["FRONTEND_URL"]}/artifact/{mail_data.Artifact.artifact_group_id}',\
                artifact_title=mail_data.Artifact.title,\
                user_id=mail_data.User.id,\
                user_name=mail_data.Person.name,\
                user_email=mail_data.Person.email,
                justification=mail_data.ArtifactOwnerRequest.action_message)

        mail.send(msg)
        
        response = jsonify({"message": "artifact ownership request successfully " + artifact_owner_request.status})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
