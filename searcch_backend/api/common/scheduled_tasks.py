import atexit, secrets, logging
from searcch_backend.models.model import Sessions, StatsRecentViews, StatsArtifactViews, OwnershipEmailInvitationKeys, OwnershipEmailInvitations, ArtifactGroup, User, Person
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func, or_
from datetime import datetime, timedelta

LOG = logging.getLogger(__name__)
# Garbage Collector used to empty recent_views database table and update the stats_views table periodically
class SearcchBackgroundTasks():

    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.setupScheduledTask()

    def setupScheduledTask(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=self.collectRecentViews, trigger="interval", seconds=self.app.config['STATS_GARBAGE_COLLECTOR_INTERVAL'])
        scheduler.add_job(func=self.email_invitations_task, trigger="interval", days=self.app.config["EMAIL_INTERVAL_DAYS"])
        scheduler.start()
        self.email_invitations_task()
        
        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

    def collectRecentViews(self):
        LOG.debug('starting collect recent views task')
        db = self.db
        query = db.session.query(StatsRecentViews.artifact_group_id.label('artifact_group_id'), StatsRecentViews.user_id.label('user_id'), StatsRecentViews.view_count.label('view_count')).all()

        self.addToStatsViews(query)

        StatsRecentViews.query.delete()
        db.session.commit()
        
        query = db.session.query(StatsArtifactViews.artifact_group_id, StatsArtifactViews.user_id, func.sum(StatsArtifactViews.view_count).label('view_count')).group_by(StatsArtifactViews.user_id).group_by(StatsArtifactViews.artifact_group_id).all()

        StatsArtifactViews.query.delete()
        db.session.commit()

        self.addToStatsViews(query)

    def addToStatsViews(self, query):
        db = self.db
        for row in query:
            artifact_group_id, user_id, view_count = row
            stats_views_entry = StatsArtifactViews(
                        artifact_group_id=artifact_group_id, user_id=user_id, view_count=view_count
                )
            db.session.add(stats_views_entry)
            db.session.commit()

    def create_key(self, email):
        key = secrets.token_urlsafe(64)[:64]
        date = datetime.today() + timedelta(days=self.app.config["EMAIL_INTERVAL_DAYS"])
        existing = OwnershipEmailInvitationKeys.query.filter_by(email=email).first()
        if not existing:
            new_record = OwnershipEmailInvitationKeys(key=key, email=email, valid_until=date)
            query = self.db.session.add(new_record)
        else:
            existing.key = key
            existing.valid_util = date
        self.db.session.commit()
        return key

    def create_email(self, email, person, artifact_groups):
        pass

    def email_invitations_task(self):
        LOG.debug('starting email invitations task')
        # query all artifact groups owned by an admin or by automatic-imports
        query = ArtifactGroup.query.join(ArtifactGroup.owner).join(User.person).filter(or_(User.can_admin==True, Person.email=="automatic-imports@cyberexperimentation.org")).all()

        # build association of potential owners and artifact groups
        person_to_artifact_group = []
        for artifact_group in query:
            if artifact_group.publication:
                emails = []
                for aaf in artifact_group.publication.artifact.affiliations:
                    emails.append(aaf.affiliation.person.email)
                # filter out artifact groups where admin is one of the authors
                if artifact_group.owner.person.email not in emails:
                    for aaf in artifact_group.publication.artifact.affiliations:
                        # remove those who have opted_out
                        if aaf.affiliation.person.email and not aaf.affiliation.person.opt_out:
                            person_to_artifact_group.append((aaf.affiliation.person, artifact_group))
                else:
                    LOG.debug("Author is admin")
        # group owners by email in case of duplicates
        persons_by_email = {}
        # group artifacts by email in case of multiple artifacts per owner
        groups_by_email = {}
        for person, artifact_group in person_to_artifact_group:
            names = persons_by_email.get(person.email, set())
            names.add(person)
            persons_by_email[person.email] = names
            group = groups_by_email.get(person.email, set())
            group.add(artifact_group)
            groups_by_email[person.email] = group
        # create secure keys for all emails
        for email, artifact_group in groups_by_email.items():
            key = self.create_key(email)