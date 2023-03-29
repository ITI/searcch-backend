import atexit, secrets, logging

from flask_sqlalchemy import SQLAlchemy
from searcch_backend.models.model import OwnershipEmail, OwnershipInvitation, Sessions, StatsRecentViews, StatsArtifactViews, ArtifactGroup, User, Person
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func, or_
from datetime import datetime, timedelta
from flask_mail import Message, Mail
from flask import render_template

LOG = logging.getLogger(__name__)

# Subject line for email invitations
SUBJECT = 'The SEARCCH Invitation: Help Us Help Others Find and Reuse Your Research Artifacts'
class SearcchBackgroundTasks():

    def __init__(self, config, db: SQLAlchemy, mail: Mail):
        self.config = config
        self.db = db
        self.mail = mail
        self.setupScheduledTask()

    def setupScheduledTask(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=self.collectRecentViews, trigger="interval", seconds=self.config['STATS_GARBAGE_COLLECTOR_INTERVAL'])
        scheduler.add_job(func=self.email_invitations_task, trigger="interval", days=self.config["EMAIL_INTERVAL_DAYS"])
        scheduler.start()
        
        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

    def collectRecentViews(self):
        # Garbage Collector used to empty recent_views database table and update the stats_views table periodically
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

    def create_key(self):
        key = secrets.token_urlsafe(64)[:64]
        return key

    def create_email(self, email, author_name, artifact_groups: set):
        """ Generate emails for the given artifact set.
        Artifacts are grouped by first, reminder, and final notice.
        Multiple emails may be generated if the email has artifacts that fit in multiple groups.
        """
        ownership_email = OwnershipEmail.query.filter_by(email=email).first()
        valid_until = datetime.today() + timedelta(days=self.config['EMAIL_INTERVAL_DAYS'])
        if not ownership_email:
            ownership_email = OwnershipEmail(email=email, key=self.create_key(), valid_until=valid_until, opt_out=False)
            query = self.db.session.add(ownership_email)
            self.db.session.commit()
            
        first_artifacts = []
        reminder_artifacts = []
        final_artifacts = []
        for artifact_group in artifact_groups:
            exists = OwnershipInvitation.query.filter_by(email=email, artifact_group_id=artifact_group.id).first()
            if not exists:
                exists = OwnershipInvitation(email=email, artifact_group_id=artifact_group.id, attempts=0, last_attempt=datetime.today())
                self.db.session.add(exists)
                first_artifacts.append(artifact_group)
            elif exists.attempts < self.config['MAX_INVITATION_ATTEMPTS'] - 1:
                reminder_artifacts.append(artifact_group)
            elif exists.attempts == self.config['MAX_INVITATION_ATTEMPTS'] - 1:
                final_artifacts.append(artifact_group)
            else:
                # skip if max attempts reached
                continue
            exists.attempts += 1
            exists.last_attempt = datetime.today()
        self.db.session.commit()
        msgs = []
        if len(first_artifacts) > 0:
            html = render_template("ownership_invitation_attempt_1.html", artifact_groups=first_artifacts, author_name=author_name, email=email, key=ownership_email.key, frontend_url=self.config['FRONTEND_URL'])
            msgs.append(Message(SUBJECT, [email], html=html))
        if len(reminder_artifacts) > 0:
            html = render_template("ownership_invitation_attempt_2.html", artifact_groups=reminder_artifacts, author_name=author_name, email=email, key=ownership_email.key, frontend_url=self.config['FRONTEND_URL'])
            msgs.append(Message(SUBJECT, [email], html=html))
        if len(final_artifacts) > 0:
            html = render_template("ownership_invitation_attempt_3.html", artifact_groups=final_artifacts, author_name=author_name, email=email, key=ownership_email.key, frontend_url=self.config['FRONTEND_URL'])
            msgs.append(Message(SUBJECT, [email], html=html))
        return msgs
            
    def find_author_name(self, persons):
        """ Simple algorithm to take the name with the most tokens in it. 
        The assumption is that usernames will be one token while real names will be 2 or 3.
        Defaults to Artifact Author if no name is found.
        """
        best = ''
        for person in persons:
            if not person.name or not person.name.strip():
                continue
            elif len(person.name.split(' ')) > len(best.split(' ')):
                best = person.name
        if not best:
            best = "Artifact Author"
        return best

    def email_invitations_task(self):
        """ Sends artifact ownership invitation emails """

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
                        if aaf.affiliation.person.email:
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
        

        for email, persons in persons_by_email.items():
            persons_by_email[email] = self.find_author_name(persons)

        email_msgs = [msg for email, artifact_groups in groups_by_email.items() for msg in self.create_email(email, persons_by_email[email], artifact_groups)]
        try:

            with self.mail.connect() as conn:
                for email_msg in email_msgs:
                    if not self.config['TESTING'] and not self.config['DEBUG']:
                        # conn.send(email_msg) # Do not go live until frontend urls in place
                        pass
                    else:
                        LOG.debug(email_msg)
        except:
            LOG.warning("could not connect to email service")


