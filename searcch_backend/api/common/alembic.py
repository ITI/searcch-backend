
def maybe_auto_upgrade_db(app, db, migrate, force=False):
    if not force and "DB_AUTO_MIGRATE" not in app.config or not app.config["DB_AUTO_MIGRATE"]:
        return

    with app.app_context():
        #
        # All this work to safely auto-migrate in the presence of multiple
        # processes.  NB: the table create is separated out due to racy table
        # creation semantics in postgres:
        # https://www.postgresql.org/message-id/CA+TgmoZAdYVtwBfp1FL2sMZbiHCWT4UPrzRLNnX1Nb30Ku3-gg@mail.gmail.com
        #
        import alembic
        # First create the table (we don't have alembic_versions until later).
        try:
            db.session.execute("create table if not exists alembic_lock (locked boolean)")
        except:
            db.session.commit()
        # Lock the table.
        try:
            db.session.execute("lock table alembic_lock in exclusive mode")
        except:
            app.logger.error("failed to lock before auto_migrate")
            raise
        # Migrate.
        try:
            alembic.command.upgrade(migrate.get_config(),"head")
        except:
            app.logger.error("failed to auto_migrate database; exiting")
            raise
        app.logger.info("auto_migrated database")
        # Commit (unlock).
        db.session.commit()
