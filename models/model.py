from api.app import db
from models.licenses import *
from sqlalchemy.dialects.postgresql import TSVECTOR


class ArtifactFile(db.Model):
    __tablename__ = "artifact_files"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    parent_file_id = db.Column(db.Integer, db.ForeignKey("artifact_files.id"))
    url = db.Column(db.String(512), nullable=False)
    filetype = db.Column(db.String(128), nullable=False)
    content = db.Column(db.LargeBinary())
    size = db.Column(db.Integer)
    mtime = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint("artifact_id", "parent_file_id", "url"),)

    def __repr__(self):
        return "<ArtifactFile(id=%r,artifact_id=%r,parent_file_id=%r,url='%s',size=%r,mtime='%s')>" % (
            self.id, self.artifact_id,
            self.parent_file_id if self.parent_file_id else 0,
            self.url, self.size,
            self.mtime.isoformat() if self.mtime else "")


class ArtifactFunding(db.Model):
    __tablename__ = "artifact_funding"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey(
        "artifacts.id"), nullable=False)
    funding_org_id = db.Column(db.Integer, db.ForeignKey(
        "organizations.id"), nullable=False)
    grant_number = db.Column(db.String(128), nullable=False)
    grant_url = db.Column(db.String(256), nullable=True)
    grant_title = db.Column(db.String(512), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("artifact_id", "funding_org_id", "grant_number"),)


class ArtifactMetadata(db.Model):
    __tablename__ = "artifact_metadata"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey('artifacts.id'))
    name = db.Column(db.String(64), nullable=False)
    value = db.Column(db.String(1024), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("name", "artifact_id"),)

    def __repr__(self):
        return "<ArtifactMetadata(artifact_id=%r,name='%s', value='%s')>" % (
            self.artifact_id, self.name, self.value)


class ArtifactPublication(db.Model):
    __tablename__ = "artifact_publications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    time = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)
    publisher_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False)
    # publisher = db.relationship("User", uselist=False, backref="publisher_user")
    publisher = db.relationship("User", uselist=False)

    def __repr__(self):
        return "<ArtifactPublication(id=%r,artifact_id=%r,time='%s',publisher='%r')>" % (
            self.id, self.artifact_id, self.time.isoformat(), self.publisher)


class Exporter(db.Model):
    __tablename__ = "exporters"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    version = db.Column(db.String(32))

    __table_args__ = (
        db.UniqueConstraint("name","version"),)

    def __repr__(self):
        return "<Exporter(id=%r,name='%s',version='%s')>" % (self.id, self.name, self.version)


class ArtifactTag(db.Model):
    __tablename__ = "artifact_tags"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey('artifacts.id'))
    tag = db.Column(db.String(64), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("tag", "artifact_id"),)

    def __repr__(self):
        return "<ArtifactTag(artifact_id=%r,tag='%s')>" % (
            self.artifact_id, self.tag)


class ArtifactCuration(db.Model):
    __tablename__ = "artifact_curations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    time = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)
    curator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    curator = db.relationship("User")

    def __repr__(self):
        return "<ArtifactCuration(id=%r,artifact_id=%r,time='%s',curator='%r')>" % (
            self.id, self.artifact_id, self.time.isoformat(),
            self.curator)


class ArtifactAffiliation(db.Model):
    __tablename__ = "artifact_affiliations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey(
        "artifacts.id"), nullable=False)
    affiliation_id = db.Column(db.Integer, db.ForeignKey(
        "affiliations.id"), nullable=False)

    artifact = db.relationship("Artifact",uselist=False)
    affiliation = db.relationship("Affiliation",uselist=False)

    __table_args__ = (
        db.UniqueConstraint("artifact_id", "affiliation_id"),)

    def __repr__(self):
        return "<ArtifactAffiliation(artifact_id=%r,affiliation_id=%r)>" % (
            self.artifact_id, self.affiliation_id)


class ArtifactRelationship(db.Model):
    # The ArtifactRelationship class declares a db.relationship between two SEARCCH artifacts.

    __tablename__ = "artifact_relationships"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    relation = db.Column(db.Enum(
        "cites", "supplements", "continues", "references", "documents",
        "compiles",
        name="artifact_relationship_enum"))
    related_artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    # related_artifact = db.relationship("Artifact", uselist=False, foreign_keys=[related_artifact_id], backref="related_artifacts")
    related_artifact = db.relationship(
        "Artifact", uselist=False, foreign_keys=[related_artifact_id])

    __table_args__ = (
        db.UniqueConstraint("artifact_id", "relation", "related_artifact_id"),)


class ArtifactRelease(db.Model):
    __tablename__ = "artifact_releases"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    url = db.Column(db.String(512))
    author_login = db.Column(db.String(128))
    author_email = db.Column(db.String(128))
    author_name = db.Column(db.String(128))
    tag = db.Column(db.String(128))
    title = db.Column(db.String(256))
    time = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    def __repr__(self):
        return "<ArtifactRelease(id=%r,artifact_id=%r,url='%s',title='%s',author_email='%s',time='%s')>" % (
            self.id, self.artifact_id, self.url, self.title, self.author_email,
            self.time.isoformat() if self.time else "")


class Importer(db.Model):
    __tablename__ = "importers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), nullable=False)
    version = db.Column(db.String(32))

    __table_args__ = (
        db.UniqueConstraint("name", "version"),)

    def __repr__(self):
        return "<Importer(id=%r,name='%s',version='%s')>" % (self.id, self.name, self.version)


class Person(db.Model):
    __tablename__ = "persons"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(128), nullable=True)

    def __repr__(self):
        return "<Person(id=%r,name=%r, email=%r)>" % (
            self.id,self.name,self.email)


class UserAuthorization(db.Model):
    __tablename__ = "user_authorizations"

    user_id = db.Column(db.Integer, db.ForeignKey(
        "users.id"), primary_key=True)
    roles = db.Column(
        db.Enum("Uploader", "Editor", "Curator",
                name="user_authorization_role_enum"),
        nullable=False)
    scope = db.Column(
        db.Enum("Org", "Artifact",
                name="user_authorization_scope_enum"),
        nullable=False)
    # A NULL scoped_id is a wildcard, meaning everything.
    scoped_id = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "roles", "scope", "scoped_id"),)

    def __repr__(self):
        return "<UserAuthorization(user_id=%r,roles='%s',scope='%s',scoped_id='%s')>" % (
            self.user_id, self.roles, self.scope, str(self.scoped_id))


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    person_id = db.Column(db.Integer, db.ForeignKey(
        "persons.id"), nullable=False)
    person = db.relationship("Person",uselist=False)

    __table_args__ = (
        db.UniqueConstraint("person_id"),)

    def __repr__(self):
        return "<User(id=%r,person_id=%r)>" % (
            self.id, self.person_id)


class License(db.Model):
    __tablename__ = "licenses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    short_name = db.Column(db.String(64), nullable=False)
    long_name = db.Column(db.String(512))

    __table_args__ = (
        db.UniqueConstraint("short_name"),)

    def __repr__(self):
        return "<License(id=%r,short_name='%s')>" % (self.id, self.short_name)


@db.event.listens_for(License.__table__, "after_create")
def insert_licenses(target, connection, **kwargs):
    for key in sorted(license_map):
        connection.execute(
            "INSERT INTO %s (short_name) VALUES ('%s')" % (target.name, key))


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(1024), nullable=False)
    type = db.Column(
        db.Enum("Institution", "Institute", "ResearchGroup", "Sponsor", "Other",
                name="organization_enum"),
        nullable=False)
    parent_org_id = db.Column(db.Integer, db.ForeignKey(
        "organizations.id"), nullable=True)
    state = db.Column(db.String(64), nullable=True)
    country = db.Column(db.String(64), nullable=True)
    latitude = db.Column(db.Float(), nullable=True)
    longitude = db.Column(db.Float(), nullable=True)
    address = db.Column(db.String(512), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("name", "type", "parent_org_id"),)

    def __repr__(self):
        return "<Organization(name='%s',type='%s')>" % (self.name, self.type)


class Affiliation(db.Model):
    __tablename__ = "affiliations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    person_id = db.Column(db.Integer, db.ForeignKey(
        "persons.id"), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey(
        "organizations.id"))
    roles = db.Column(
        db.Enum("Author", "ProjectManager", "Researcher", "ContactPerson",
                "PrincipalInvestigator", "CoPrincipalInvestigator", "Other",
                name="affiliation_enum"),
        nullable=False)

    person = db.relationship("Person", uselist=False)
    org = db.relationship("Organization", uselist=False)

    __table_args__ = (
        db.UniqueConstraint("person_id", "org_id", "roles"),)

    def __repr__(self):
        return "<Affiliation(person='%r',org='%r',roles='%s')>" % (
            self.person, self.org, self.roles)


class PersonMetadata(db.Model):
    __tablename__ = "person_metadata"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    person_id = db.Column(db.Integer, db.ForeignKey(
        "persons.id"), nullable=False)
    name = db.Column(db.String(64), nullable=False)
    value = db.Column(db.String(1024), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("person_id", "name"),)

    def __repr__(self):
        return "<PersonMetadata(person_id=%r,name='%s')>" % (
            self.id, self.name)


class ArtifactRatings(db.Model):
    __tablename__ = "artifact_ratings"
    __table_args__ = (
        db.CheckConstraint(
            'rating >= 0', name='artifact_ratings_valid_rating_lower_bound'),
        db.CheckConstraint(
            'rating <= 5', name='artifact_ratings_valid_rating_upper_bound'),
        db.UniqueConstraint("artifact_id", "user_id"),
    )

    # id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    artifact_id = db.Column(db.Integer, db.ForeignKey(
        "artifacts.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return "<ArtifactRatings(id=%r, user_id=%r,artifact_id=%r,rating='%d')>" % (
            self.id, self.user_id, self.artifact_id, self.rating)


class ArtifactReviews(db.Model):
    __tablename__ = "artifact_reviews"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"), nullable=False)
    review = db.Column(db.Text, nullable=False)
    review_time = db.Column(db.DateTime, nullable=False)
    subject = db.Column(db.String(128), nullable=False)
    
    reviewer = db.relationship("User")

    def __repr__(self):
        return "<ArtifactReviews(id=%r, user_id=%r,artifact_id=%r,review='%s')>" % (
            self.id, self.user_id, self.artifact_id, self.review)


class ArtifactFavorites(db.Model):
    __tablename__ = "artifact_favorites"
    __table_args__ = (
        db.UniqueConstraint("artifact_id", "user_id"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    artifact_id = db.Column(db.Integer, db.ForeignKey(
        "artifacts.id"), nullable=False)
    
    def __repr__(self):
        return "<ArtifactFavorites(id=%r, user_id=%r,artifact_id=%r)>" % (
            self.id, self.user_id, self.artifact_id)


class Sessions(db.Model):
    __tablename__ = "sessions"
    __table_args__ = (
        db.UniqueConstraint("user_id", "sso_token"),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    sso_token = db.Column(db.String(64), nullable=False)
    # session_id = db.Column(db.String(64), nullable=False)
    expires_on = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        # return "<Session(id=%r, user_id=%r, sso_token='%s', session_id='%s')>" \
        #             % (self.id, self.user_id, self.sso_token, self.session_id)
        return "<Session(id=%r, user_id=%r, sso_token='%s')>" \
            % (self.id, self.user_id, self.sso_token)


class Artifact(db.Model):
    # The Artifact class provides an internal model of a SEARCCH artifact.
    # An artifact is an entity that may be added to or edited within the SEARCCH Hub.

    __tablename__ = "artifacts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.Enum("dataset", "executable", "methodology", "metrics",
                             "priorwork", "publication", "hypothesis", "code", "domain",
                             "supportinginfo",
                             name="artifact_enum"))
    version = db.Column(db.Integer, nullable=False, default=0)
    url = db.Column(db.String(1024), nullable=False)
    ext_id = db.Column(db.String(512), nullable=False)
    title = db.Column(db.Text, nullable=False)
    name = db.Column(db.String(1024), nullable=True)
    ctime = db.Column(db.DateTime, nullable=False)
    mtime = db.Column(db.DateTime, nullable=True)
    description = db.Column(db.Text, nullable=True)
    license_id = db.Column(db.Integer, db.ForeignKey(
        "licenses.id"), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    importer_id = db.Column(db.Integer, db.ForeignKey(
        "importers.id"), nullable=True)
    exporter_id = db.Column(db.Integer, db.ForeignKey(
        "exporters.id"), nullable=True)
    exporter = db.relationship("Exporter", uselist=False)
    parent_id = db.Column(db.Integer, db.ForeignKey(
        "artifacts.id"), nullable=True)
    document_with_idx = db.Column(TSVECTOR)

    license = db.relationship("License", uselist=False)
    meta = db.relationship("ArtifactMetadata")
    tags = db.relationship("ArtifactTag")
    files = db.relationship("ArtifactFile")
    owner = db.relationship("User", uselist=False)
    importer = db.relationship("Importer", uselist=False)
    parent = db.relationship("Artifact",uselist=False)
    curations = db.relationship("ArtifactCuration")
    publication = db.relationship("ArtifactPublication", uselist=False)
    releases = db.relationship("ArtifactRelease", uselist=True)
    affiliations = db.relationship("ArtifactAffiliation", uselist=True)

    __table_args__ = (
        db.UniqueConstraint("owner_id", "url", "version"),
        db.Index('document_idx', 'document_with_idx', postgresql_using='gin'),
    )

    def __repr__(self):
        return "<Artifact(id=%r,title='%s',description='%s',type='%s',url='%s',owner='%r',files='%r',tags='%r',metadata='%r')>" % (
            self.id, self.title, self.description, self.type, self.url, self.owner, self.files, self.tags, self.meta)
