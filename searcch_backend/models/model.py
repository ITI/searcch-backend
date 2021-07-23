from searcch_backend.api.app import db
from sqlalchemy.dialects.postgresql import TSVECTOR, BYTEA
from sqlalchemy import Table, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

metadata = MetaData()
Base = declarative_base(metadata=metadata)


ARTIFACT_TYPES = (
    "dataset", "executable", "methodology", "metrics",
    "priorwork", "publication", "hypothesis", "code", "domain",
    "supportinginfo"
)
ARTIFACT_IMPORT_TYPES = (
    "unknown", *ARTIFACT_TYPES
)
RELATION_TYPES = (
    "cites", "supplements", "continues", "references", "documents",
    "compiles","publishes"
)

class ArtifactFile(db.Model):
    __tablename__ = "artifact_files"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    url = db.Column(db.String(512), nullable=False)
    name = db.Column(db.String(512))
    filetype = db.Column(db.String(128), nullable=False)
    content = db.Column(db.LargeBinary())
    size = db.Column(db.BigInteger)
    mtime = db.Column(db.DateTime)
    
    members = db.relationship("ArtifactFileMember", uselist=True)

    __table_args__ = (
        db.UniqueConstraint("artifact_id", "url"),)

    def __repr__(self):
        return "<ArtifactFile(id=%r,artifact_id=%r,url=%r,name=%r,size=%r,mtime=%r)>" % (
            self.id, self.artifact_id, self.url, self.name, self.size,
            self.mtime.isoformat() if self.mtime else "")


class ArtifactFileMember(db.Model):
    __tablename__ = "artifact_file_members"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parent_file_id = db.Column(db.Integer, db.ForeignKey("artifact_files.id"),nullable=False)
    pathname = db.Column(db.String(512), nullable=False)
    html_url = db.Column(db.String(512))
    download_url = db.Column(db.String(512))
    name = db.Column(db.String(512))
    filetype = db.Column(db.String(128), nullable=False)
    content = db.Column(db.LargeBinary())
    size = db.Column(db.Integer)
    mtime = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint("parent_file_id", "pathname"),)

    def __repr__(self):
        return "<ArtifactFileMember(id=%r,parent_file_id=%r,pathname=%r,name=%r,html_url=%r,size=%r,mtime=%r)>" % (
            self.id,self.parent_file_id,self.pathname,self.name,self.html_url,self.size,
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
    grant_title = db.Column(db.String(1024), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("artifact_id", "funding_org_id", "grant_number"),)


class ArtifactMetadata(db.Model):
    __tablename__ = "artifact_metadata"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey('artifacts.id'))
    name = db.Column(db.String(64), nullable=False)
    value = db.Column(db.String(16384), nullable=False)
    type = db.Column(db.String(256), nullable=True)
    source = db.Column(db.String(256), nullable=True)

    def __repr__(self):
        return "<ArtifactMetadata(artifact_id=%r,name=%r,value=%r,type=%r,source=%r)>" % (
            self.artifact_id, self.name, self.value, self.type,
            self.source)


class ArtifactPublication(db.Model):
    __tablename__ = "artifact_publications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    time = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)
    publisher_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False)
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
        db.UniqueConstraint("name", "version"),)

    def __repr__(self):
        return "<Exporter(id=%r,name='%s',version='%s')>" % (self.id, self.name, self.version)


class ArtifactTag(db.Model):
    __tablename__ = "artifact_tags"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey('artifacts.id'))
    tag = db.Column(db.String(256), nullable=False)
    source = db.Column(db.String(256), nullable=False, default="")

    __table_args__ = (
        db.UniqueConstraint("tag", "artifact_id", "source"),)

    def __repr__(self):
        return "<ArtifactTag(artifact_id=%r,tag=%r,source=%r)>" % (
            self.artifact_id, self.tag, self.source)


class ArtifactCuration(db.Model):
    __tablename__ = "artifact_curations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    time = db.Column(db.DateTime, nullable=False)
    notes = db.Column(db.Text)
    opdata = db.Column(db.Text,nullable=False)
    curator_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False)

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
    roles = db.Column(
        db.Enum("Author", "ContactPerson", "Other",
                name="artifact_affiliation_enum"),
        nullable=False, default="Author")

    affiliation = db.relationship("Affiliation", uselist=False)

    __table_args__ = (
        db.UniqueConstraint("artifact_id", "affiliation_id", "roles"),)

    def __repr__(self):
        return "<ArtifactAffiliation(artifact_id=%r,affiliation_id=%r,roles=%r)>" % (
            self.artifact_id, self.affiliation_id, self.roles)


class ArtifactRelationship(db.Model):
    # The ArtifactRelationship class declares a db.relationship between two SEARCCH artifacts.

    __tablename__ = "artifact_relationships"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"))
    relation = db.Column(db.Enum(
        *RELATION_TYPES,
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
    title = db.Column(db.String(1024))
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
    name = db.Column(db.String(1024), nullable=True)
    email = db.Column(db.String(256), nullable=True)
    profile_photo = db.Column(BYTEA, nullable=True)
    research_interests = db.Column(db.Text, nullable=True)
    website = db.Column(db.Text, nullable=True)
    person_tsv = db.Column(TSVECTOR)

    def __repr__(self):
        return "<Person(id=%r,name=%r, email=%r)>" % (
            self.id, self.name, self.email)


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
    person = db.relationship("Person", uselist=False)

    __table_args__ = (
        db.UniqueConstraint("person_id"),)

    def __repr__(self):
        return "<User(id=%r,person_id=%r)>" % (
            self.id, self.person_id)


class License(db.Model):
    __tablename__ = "licenses"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    short_name = db.Column(db.String(64))
    long_name = db.Column(db.String(512), nullable=False)
    url = db.Column(db.String(1024), nullable=False)
    verified = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint("long_name", "url", "verified"),)

    __object_from_json_allow_pk__ = True

    def __repr__(self):
        return "<License(id=%r,long_name=%r,short_name=%r,url=%r,verified=%r)>" % (
            self.id, self.long_name, self.short_name, self.url, self.verified)


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(1024), nullable=False)
    type = db.Column(
        db.Enum("Institution", "Company", "Institute", "ResearchGroup", "Sponsor", "Other",
                name="organization_enum"),
        nullable=False)
    state = db.Column(db.String(64), nullable=True)
    country = db.Column(db.String(64), nullable=True)
    latitude = db.Column(db.Float(), nullable=True)
    longitude = db.Column(db.Float(), nullable=True)
    address = db.Column(db.String(512), nullable=True)
    verified = db.Column(db.Boolean, nullable=False, default=False)
    org_tsv = db.Column(TSVECTOR)

    def __repr__(self):
        return "<Organization(name=%r,type=%r,verified=%r)>" % (
            self.name, self.type, self.verified)


class Affiliation(db.Model):
    __tablename__ = "affiliations"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    person_id = db.Column(db.Integer, db.ForeignKey(
        "persons.id"), nullable=False)
    org_id = db.Column(db.Integer, db.ForeignKey(
        "organizations.id"))

    person = db.relationship("Person", uselist=False)
    org = db.relationship("Organization", uselist=False)

    __table_args__ = (
        db.UniqueConstraint("person_id", "org_id"),)

    def __repr__(self):
        return "<Affiliation(person=%r,org=%r)>" % (
            self.person, self.org)


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


class Badge(db.Model):
    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(1024), nullable=False)
    url = db.Column(db.String(1024), nullable=False)
    image_url = db.Column(db.String(1024))
    description = db.Column(db.Text)
    version = db.Column(db.String(256), nullable=False, default="")
    organization = db.Column(db.String(1024), nullable=False)
    venue = db.Column(db.String(1024))
    issue_time = db.Column(db.DateTime)
    doi = db.Column(db.String(128))
    verified = db.Column(db.Boolean, nullable=False, default=False)

    __table_args__ = (
        db.UniqueConstraint("title", "url", "version", "organization"),)

    def __repr__(self):
        return "<Badge(title=%r,url=%r,version=%r,organization=%r,venue=%r,verified=%r)>" % (
            self.title, self.url, self.version, self.organization, self.venue, self.verified)


class ArtifactBadge(db.Model):
    __tablename__ = "artifact_badges"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_id = db.Column(db.Integer, db.ForeignKey(
        "artifacts.id"), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey(
        "badges.id"), nullable=False)

    badge = db.relationship("Badge", uselist=False)

    __table_args__ = (
        db.UniqueConstraint("artifact_id", "badge_id"),)

    def __repr__(self):
        return "<ArtifactBadge(artifact_id=%r,badge_id=%r)>" % (
            self.artifact_id, self.badge_id)


class ArtifactRatings(db.Model):
    __tablename__ = "artifact_ratings"
    __table_args__ = (
        db.CheckConstraint(
            'rating >= 0', name='artifact_ratings_valid_rating_lower_bound'),
        db.CheckConstraint(
            'rating <= 5', name='artifact_ratings_valid_rating_upper_bound'),
        db.UniqueConstraint("artifact_id", "user_id"),
    )

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
    artifact_id = db.Column(db.Integer, db.ForeignKey(
        "artifacts.id"), nullable=False)
    review = db.Column(db.Text, nullable=False)
    review_time = db.Column(db.DateTime, nullable=False)

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
    expires_on = db.Column(db.DateTime, nullable=False)
    user = db.relationship("User", uselist=False)

    def __repr__(self):
        return "<Session(id=%r, user_id=%r, sso_token='%s')>" \
            % (self.id, self.user_id, self.sso_token)


class Artifact(db.Model):
    # The Artifact class provides an internal model of a SEARCCH artifact.
    # An artifact is an entity that may be added to or edited within the SEARCCH Hub.

    __tablename__ = "artifacts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.Enum(*ARTIFACT_TYPES,name="artifact_enum"))
    version = db.Column(db.Integer, nullable=False, default=0)
    url = db.Column(db.String(1024), nullable=False)
    ext_id = db.Column(db.String(512))
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
    parent_id = db.Column(db.Integer, db.ForeignKey(
        "artifacts.id"), nullable=True)

    exporter = db.relationship("Exporter", uselist=False)
    license = db.relationship("License", uselist=False)
    meta = db.relationship("ArtifactMetadata")
    tags = db.relationship("ArtifactTag")
    files = db.relationship("ArtifactFile")
    owner = db.relationship("User", uselist=False)
    importer = db.relationship("Importer", uselist=False)
    parent = db.relationship("Artifact", uselist=False)
    curations = db.relationship("ArtifactCuration")
    publication = db.relationship("ArtifactPublication", uselist=False)
    releases = db.relationship("ArtifactRelease", uselist=True)
    affiliations = db.relationship("ArtifactAffiliation")
    relationships = db.relationship("ArtifactRelationship",uselist=True,
                                    foreign_keys=[ArtifactRelationship.artifact_id])
    badges = db.relationship("ArtifactBadge", uselist=True)

    # NB: all foreign keys are read-only, so not included here.
    __user_ro_fields__ = (
        "version","ctime","mtime","ext_id" )
    __user_ro_relationships__ = (
        "exporter","owner","importer","parent","curations","publication",
        "relationships"
    )
    __user_skip_relationships__ = (
        "curations",
    )

    def __repr__(self):
        return "<Artifact(id=%r,title='%s',description='%s',type='%s',url='%s',owner='%r',files='%r',tags='%r',metadata='%r',publication='%r')>" % (
            self.id, self.title, self.description, self.type, self.url, self.owner, self.files, self.tags, self.meta, self.publication)


class ArtifactSearchMaterializedView(db.Model):
    # The ArtifactSearchMaterializedView class provides an internal model of a SEARCCH artifact's searchable index.
    __tablename__ = "artifact_search_view"

    dummy_id = db.Column(db.Integer, primary_key=True)  # this id does not actually exist in the database
    artifact_id = db.Column(db.Integer)
    doc_vector = db.Column(TSVECTOR)
    
    def __repr__(self):
        return "<ArtifactSearchMaterializedView(artifact_id=%r,doc_vector='%s')>" % (self.id, self.doc_vector)


ARTIFACT_IMPORT_STATUSES = (
    "pending", "scheduled", "running", "completed", "failed"
)
ARTIFACT_IMPORT_PHASES = (
    "start", "validate", "import", "retrieve", "extract", "done"
)

class ArtifactImport(db.Model):
    """
    ArtifactImport represents an ongoing or completed artifact import session.
    """

    __tablename__ = "artifact_imports"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    type = db.Column(db.Enum(
        *ARTIFACT_IMPORT_TYPES,name="artifact_imports_type_enum"),
        nullable=False)
    url = db.Column(db.String(1024), nullable=False)
    #parent_id = db.Column(db.Integer, db.ForeignKey(
    #    "artifacts.id"), nullable=True)
    importer_module_name = db.Column(db.String(256), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    ctime = db.Column(db.DateTime, nullable=False)
    mtime = db.Column(db.DateTime, nullable=True)
    # Status of the import from back end's perspective
    status = db.Column(db.Enum(
        *ARTIFACT_IMPORT_STATUSES,
        name="artifact_imports_status_enum"), nullable=False)
    # Importer phase
    phase = db.Column(db.Enum(
        *ARTIFACT_IMPORT_PHASES,
        name="artifact_imports_phase_enum"), nullable=False)
    message = db.Column(db.Text, nullable=True)
    progress = db.Column(db.Float, default=0.0)
    bytes_retrieved = db.Column(db.Integer, default=0, nullable=False)
    bytes_extracted = db.Column(db.Integer, default=0, nullable=False)
    log = db.Column(db.Text, nullable=True)
    # Only set once status=complete and phase=done
    artifact_id = db.Column(db.Integer, db.ForeignKey("artifacts.id"), nullable=True)
    archived = db.Column(db.Boolean, nullable=False, default=False)

    owner = db.relationship("User", uselist=False)
    #parent = db.relationship("Artifact", uselist=False)
    artifact = db.relationship("Artifact", uselist=False)

    __table_args__ = (
        db.UniqueConstraint("owner_id","url","artifact_id"),
    )

    def __repr__(self):
        return "<ArtifactImport(id=%r,type=%r,url=%r,importer_module_name=%r,owner=%r,status=%r,artifact=%r)>" % (
            self.id, self.type, self.url, self.importer_module_name,
            self.owner, self.status, self.artifact)


class ImporterInstance(db.Model):
    """
    Represents registered, authorized importer instances.
    """
    __tablename__ = "importer_instances"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    url = db.Column(db.String(1024), nullable=False)
    key = db.Column(db.String(128), nullable=False)
    max_tasks = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(
        "up", "down", "stale", name="importer_instances_status_enum"),
        nullable=False)
    status_time = db.Column(db.DateTime, nullable=False)
    admin_status = db.Column(db.Enum(
        "enabled","disabled", name="importer_instances_admin_status_enum"),
        nullable=False)
    admin_status_time = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("url","key"),
    )

    def __repr__(self):
        return "<ImporterInstance(id=%r,url=%r,status=%r,status_time=%r,admin_status=%r,admin_status_time=%r)>" % (
            self.id, self.url, self.status, self.status_time, self.admin_status, self.admin_status_time)


class ImporterSchedule(db.Model):
    """
    Represents scheduled and pending imports.
    """
    __tablename__ = "importer_schedules"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    artifact_import_id = db.Column(
        db.Integer, db.ForeignKey("artifact_imports.id"), nullable=False)
    importer_instance_id = db.Column(
        db.Integer, db.ForeignKey("importer_instances.id"), nullable=True)
    schedule_time = db.Column(db.DateTime, nullable=True)
    # NB: this is the ID of the artifact import in the importer instance
    remote_id = db.Column(db.Integer, nullable=True)
    
    artifact_import = db.relationship("ArtifactImport", uselist=False)
    importer_instance = db.relationship("ImporterInstance", uselist=False)

    __table_args__ = (
        db.UniqueConstraint("artifact_import_id"),
    )

    def __repr__(self):
        return "<ImporterSchedule(id=%r,artifact_import=%r,importer_instance=%r,schedule_time=%r" % (
            self.id, self.artifact_import, self.importer_instance, self.schedule_time)
