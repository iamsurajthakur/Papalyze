from tenacity import retry, stop_after_attempt, wait_fixed
from app.extensions import db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text


@retry(stop=stop_after_attempt(5), wait=wait_fixed(3))
def ping_database():
    db.session.execute(text("SELECT 1"))