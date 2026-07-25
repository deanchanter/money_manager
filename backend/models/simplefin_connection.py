from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from database import Base

class SimpleFinConnection(Base):
    """A claimed SimpleFIN Bridge access URL.

    The access URL embeds credentials in its userinfo, so this row is
    effectively a secret. It lives in the SQLite file, which is gitignored but
    unencrypted -- fine for a single-user local app, not for a hosted one.
    """
    __tablename__ = "simplefin_connections"

    id = Column(Integer, primary_key=True, index=True)
    access_url = Column(String, nullable=False)
    org_name = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)
