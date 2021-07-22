from marshmallow_sqlalchemy import ModelSchema, SQLAlchemyAutoSchema, auto_field
from marshmallow_sqlalchemy.convert import ModelConverter as BaseModelConverter
from marshmallow_sqlalchemy.fields import Nested

from searcch_backend.api.app import ma
from searcch_backend.models.model import *


class ModelConverter(BaseModelConverter):
    SQLA_TYPE_MAPPING = {
        **BaseModelConverter.SQLA_TYPE_MAPPING
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


class ExporterSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Exporter
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class ArtifactTagSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactTag
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True
        exclude = ('artifact_id',)


class ArtifactFileMemberSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactFileMember
        exclude = ('parent_file_id',)
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class ArtifactFileSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactFile
        exclude = ('artifact_id',)
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    members = Nested(ArtifactFileMemberSchema, many=True)


class ArtifactRelationshipSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactRelationship
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


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
        exclude = ('person_id',)
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    person = Nested(PersonSchema)


class ArtifactPublicationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactPublication
        exclude = ('artifact_id', 'publisher_id',)
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    publisher = Nested(UserSchema)


class ArtifactCurationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactCuration
        exclude = ('artifact_id', 'curator_id')
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    curator = Nested(UserSchema)


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

    reviewer = Nested(UserSchema())


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


class ArtifactSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Artifact
        model_converter = ModelConverter
        # exclude = ('license_id', 'owner_id', 'importer_id',
        #            'parent_id', 'exporter_id', 'document_with_idx')
        exclude = ('license_id', 'owner_id', 'importer_id',
                   'parent_id', 'exporter_id')
        include_fk = True
        include_relationships = True

    license = Nested(LicenseSchema, many=False)
    meta = Nested(ArtifactMetadataSchema, many=True)
    tags = Nested(ArtifactTagSchema, many=True)
    files = Nested(ArtifactFileSchema, many=True)
    owner = Nested(UserSchema)
    importer = Nested(ImporterSchema, many=False)
    # parent = Nested(ArtifactSchema, many=True)
    curations = Nested(ArtifactCurationSchema, many=True)
    publication = Nested(ArtifactPublicationSchema, many=False)
    releases = Nested(ArtifactReleaseSchema, many=True)
    affiliations = Nested(ArtifactAffiliationSchema, many=True)
    relationships = Nested(ArtifactRelationshipSchema, many=True)
    badges = Nested(ArtifactBadgeSchema, many=True)

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


class ImporterInstanceSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ImporterInstance
        model_converter = ModelConverter
        exclude = ()
        include_fk = True
        include_relationships = True


class ImporterScheduleSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ImporterSchedule
        model_converter = ModelConverter
        exclude = ()
        include_fk = True
        include_relationships = True

    artifact_import = Nested(ArtifactImportSchema, many=False)
    importer_instance = Nested(ImporterInstanceSchema, many=False)
