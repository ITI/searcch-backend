import atexit
from searcch_backend.api.app import db
from searcch_backend.models.model import Sessions, StatsRecentViews, StatsArtifactViews
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func

# Garbage Collector used to empty recent_views database table and update the stats_views table periodically
class UpdateStatsViews():

    def __init__(self, interval_duration):
        self.interval_duration = interval_duration
        self.setupScheduledTask()

    def setupScheduledTask(self):
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=self.collectRecentViews, trigger="interval", seconds=self.interval_duration)
        scheduler.start()
        
        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())

    def collectRecentViews(self):
        query = db.session.query(StatsRecentViews.artifact_id.label('artifact_id'), StatsRecentViews.user_id.label('user_id'), StatsRecentViews.view_count.label('view_count')).all()

        self.addToStatsViews(query)

        StatsRecentViews.query.delete()
        db.session.commit()
        
        query = db.session.query(StatsArtifactViews.artifact_id, StatsArtifactViews.user_id, func.sum(StatsArtifactViews.view_count).label('view_count')).group_by(StatsArtifactViews.user_id).group_by(StatsArtifactViews.artifact_id).all()

        StatsArtifactViews.query.delete()
        db.session.commit()

        self.addToStatsViews(query)

    def addToStatsViews(self, query):
        for row in query:
            artifact_id, user_id, view_count = row
            stats_views_entry = StatsArtifactViews(
                        artifact_id=artifact_id, user_id=user_id, view_count=view_count
                )
            db.session.add(stats_views_entry)
            db.session.commit()