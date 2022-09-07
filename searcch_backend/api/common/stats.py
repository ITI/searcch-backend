# logic for stat collection

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.models.model import Sessions, StatsRecentViews
from sqlalchemy import func, asc, desc, sql, and_, or_
import logging

LOG = logging.getLogger(__name__)

class StatsResource():

    def __init__(self, artifact_group_id, session_id):
        self.artifact_group_id = artifact_group_id
        self.session_id = session_id

    def recordView(self):
        query = db.session.query(StatsRecentViews).filter(and_(StatsRecentViews.session_id == self.session_id, StatsRecentViews.artifact_group_id == self.artifact_group_id)).first()
        if query is None:
            query = db.session.query(Sessions).filter(Sessions.sso_token == self.session_id).first()
            if query is not None:
                user_id = query.user_id
            else:
                user_id = None
            stats_recent_view = StatsRecentViews(
                        session_id=self.session_id, artifact_group_id=self.artifact_group_id, user_id=user_id, view_count=1
                )
            db.session.add(stats_recent_view)
            db.session.commit()
