from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow_sqlalchemy.convert import ModelConverter as BaseModelConverter
from marshmallow_sqlalchemy.fields import Nested
from marshmallow import fields, ValidationError
import sqlalchemy
import base64

from searcch_backend.api.app import ma
from searcch_backend.models.model import *


class Base64Field(fields.Field):
    """Field that serializes to a base64-encoded string and deserializes
    to bytes."""

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return ""
        return base64.b64encode(value).decode("utf-8")

    def _deserialize(self, value, attr, data, **kwargs):
        if value is None:
            return None
        if value == "":
            return b""
        try:
            return base64.b64decode(value)
        except Exception as error:
            raise ValidationError("Invalid base64 content") from error


class ModelConverter(BaseModelConverter):
    SQLA_TYPE_MAPPING = {
        **BaseModelConverter.SQLA_TYPE_MAPPING,
        sqlalchemy.LargeBinary: Base64Field,
        sqlalchemy.types.BINARY: Base64Field,
    }


class ArtifactFundingSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactFunding
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class ArtifactMetadataSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactMetadata
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True
        exclude = ('artifact_id',)


class ArtifactTagSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactTag
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True
        exclude = ('artifact_id',)


class FileContentSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = FileContent
        model_converter = ModelConverter
        include_fk = False
        include_relationships = False
        exclude = ()


class ArtifactFileMemberSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactFileMember
        exclude = ('parent_file_id', 'file_content_id')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    file_content = Nested(FileContentSchema, many=False)


class ArtifactFileSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactFile
        exclude = ('artifact_id', 'file_content_id')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    file_content = Nested(FileContentSchema, many=False)
    members = Nested(ArtifactFileMemberSchema, many=True)


class ArtifactRelationshipSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactRelationship
        #exclude = ('related_artifact_group',)
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    related_artifact_group = Nested("ArtifactGroupShallowSchema", many=False)


class ArtifactReleaseSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactRelease
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class ImporterSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Importer
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class PersonPublicSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Person
        model_converter = ModelConverter
        exclude = ('email', 'research_interests', 'website', 'profile_photo', 'person_tsv')
        include_fk = True
        include_relationships = True


class PersonSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Person
        model_converter = ModelConverter
        exclude = ('profile_photo', 'person_tsv')
        include_fk = True
        include_relationships = True


class UserAuthorizationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = UserAuthorization
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class UserSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        exclude = ('person_id', 'can_admin')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    person = Nested(PersonSchema)


class UserPublicSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = User
        exclude = ('person_id', 'can_admin')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    person = Nested(PersonPublicSchema)


class ArtifactCurationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactCuration
        exclude = ('artifact_id', 'curator_id')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    curator = Nested(UserPublicSchema)


class ArtifactCurationShallowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactCuration
        exclude = ('artifact_id', 'curator_id', 'time', 'notes', 'opdata')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    curator = Nested(UserPublicSchema)


class LicenseSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = License
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class OrganizationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Organization
        model_converter = ModelConverter
        exclude = ('org_tsv',)
        include_fk = True
        include_relationships = True


class BadgeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Badge
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class ArtifactBadgeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactBadge
        exclude = ('artifact_id', 'badge_id')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    badge = Nested(BadgeSchema, many=False)


class AffiliationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Affiliation
        exclude = ('person_id', 'org_id')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    person = Nested(PersonSchema)
    org = Nested(OrganizationSchema)


class UserAffiliationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = UserAffiliation
        exclude = ('user_id', 'org_id')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    #user = Nested(UserPublicSchema)
    org = Nested(OrganizationSchema)


class ArtifactAffiliationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactAffiliation
        exclude = ('artifact_id', 'affiliation_id')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    affiliation = Nested(AffiliationSchema, many=False)


class PersonMetadataSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = PersonMetadata
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class ArtifactRatingsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactRatings
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class ArtifactReviewsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactReviews
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    reviewer = Nested(UserPublicSchema())


class ArtifactFavoritesSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactFavorites
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class SessionsSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Sessions
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    user = Nested(UserSchema())


class ArtifactShallowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Artifact
        model_converter = ModelConverter
        exclude = ('importer_id', 'exporter_id', )
        include_fk = True
        include_relationships = False

    owner = Nested(UserPublicSchema)


class ArtifactPublicationShallowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactPublication
        exclude = ('publisher_id',)
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    artifact = Nested(ArtifactShallowSchema)
    publisher = Nested(UserPublicSchema)


class ArtifactPublicationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactPublication
        exclude = ('publisher_id',)
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    publisher = Nested(UserPublicSchema)


class ArtifactGroupSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactGroup
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    owner = Nested(UserPublicSchema)
    publication = Nested(ArtifactPublicationShallowSchema)
    relationships = Nested(ArtifactRelationshipSchema, many=True)
    reverse_relationships = Nested(ArtifactRelationshipSchema, many=True)
    publications = Nested(ArtifactPublicationShallowSchema, many=True)


class ArtifactGroupShallowSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactGroup
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    owner = Nested(UserPublicSchema)
    publication = Nested(ArtifactPublicationShallowSchema)
    #relationships = Nested(ArtifactRelationshipSchema, many=True)
    #reverse_relationships = Nested(ArtifactRelationshipSchema, many=True)
    #publications = Nested(ArtifactPublicationShallowSchema, many=True)


class ArtifactSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Artifact
        model_converter = ModelConverter
        # exclude = ('license_id', 'owner_id', 'importer_id',
        #            'parent_id', 'exporter_id', 'document_with_idx')
        exclude = ('license_id', 'owner_id', 'importer_id',
                   'exporter_id',)# 'curations')
        include_fk = True
        include_relationships = True

    artifact_group = Nested(ArtifactGroupSchema, many=False)
    license = Nested(LicenseSchema, many=False)
    meta = Nested(ArtifactMetadataSchema, many=True)
    tags = Nested(ArtifactTagSchema, many=True)
    files = Nested(ArtifactFileSchema, many=True)
    owner = Nested(UserPublicSchema)
    importer = Nested(ImporterSchema, many=False)
    # parent = Nested(ArtifactSchema, many=True)
    curations = Nested(ArtifactCurationShallowSchema, many=True)
    publication = Nested(ArtifactPublicationSchema, many=False)
    releases = Nested(ArtifactReleaseSchema, many=True)
    affiliations = Nested(ArtifactAffiliationSchema, many=True)
    badges = Nested(ArtifactBadgeSchema, many=True)

    view_count = fields.Method("get_views")

    def get_views(self, obj):
        result = db.session.query(Artifact, StatsArtifactViews.view_count.label("view_count")).join(StatsArtifactViews, Artifact.artifact_group_id==StatsArtifactViews.artifact_group_id).filter(Artifact.artifact_group_id==obj.artifact_group_id).first()
        if hasattr(result, "view_count"):
            return result.view_count
        return 0


class ArtifactSearchMaterializedViewSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactSearchMaterializedView
        model_converter = ModelConverter
        exclude = ('doc_vector',)
        include_fk = True
        include_relationships = True

class ArtifactImportSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactImport
        model_converter = ModelConverter
        exclude = ()
        include_fk = True
        include_relationships = True

    owner = Nested(UserSchema, many=False)
    #parent = Nested(ArtifactSchema, many=False)
    artifact = Nested(ArtifactSchema, many=False)

class ArtifactOwnerRequestSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactOwnerRequest
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True
    
    user = Nested(UserSchema, many=False)
    action_by_user = Nested(UserSchema, many=False)

    artifact_title = fields.Method("get_artifact_title")

    def get_artifact_title(self, obj):
        result = db.session.query(Artifact.title).filter(Artifact.artifact_group_id==obj.artifact_group_id).first()
        if hasattr(result, "title"):
            return result.title
        return ""

class ImporterScheduleSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ImporterSchedule
        model_converter = ModelConverter
        exclude = ()
        include_fk = True
        include_relationships = True

    artifact_import = Nested(ArtifactImportSchema, many=False)


class ImporterInstanceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ImporterInstance
        model_converter = ModelConverter
        exclude = ()
        include_fk = True
        include_relationships = True

    scheduled = Nested(ImporterScheduleSchema, many=True)
