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
        exclude = ('id', 'artifact_id',)


class ArtifactPublicationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactPublication
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


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
        exclude = ('id', 'artifact_id',)


class ArtifactAffiliationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactAffiliation
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True


class ArtifactFileSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactFile
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True
        exclude = ('id', 'artifact_id',)


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
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    person = Nested(PersonSchema)


class ArtifactCurationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = ArtifactCuration
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
        include_fk = True
        include_relationships = True


class AffiliationSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Affiliation
        model_converter = ModelConverter
        include_fk = True
        include_relationships = True

    person = Nested(PersonSchema)
    org = Nested(OrganizationSchema)


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

    reviewer = Nested(UserSchema)


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
        exclude = ('document_with_idx',)
        include_fk = True
        include_relationships = True

    meta = Nested(ArtifactMetadataSchema, many=True)
    tags = Nested(ArtifactTagSchema, many=True)
    files = Nested(ArtifactFileSchema, many=True)
    owner = Nested(UserSchema)
    importer = Nested(ImporterSchema, many=False)
    # parent = Nested(ArtifactSchema, many=True)
    curations = Nested(ArtifactCurationSchema, many=True)
    publication = Nested(ArtifactPublicationSchema, many=False)
    releases = Nested(ArtifactReleaseSchema, many=True)
