import os
import json
from datetime import datetime
from celery import Celery
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', "amqp://guest:guest@rabbitmq:5672//")
celery_app = Celery("analytics_tasks", broker=CELERY_BROKER_URL)

POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

@celery_app.task(name="tasks.save_event")
def save_event_task(event_data: dict):
    session = SessionLocal()
    try:
        if isinstance(event_data.get("time_event"), str):
            clean_date_str = event_data["time_event"].replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean_date_str)
            event_data["time_event"] = dt.replace(tzinfo=None)

        raw_metadata = event_data.get("metadata")
        if isinstance(raw_metadata, dict):
            event_data["metadata"] = json.dumps(raw_metadata)
        elif raw_metadata is None:
            event_data["metadata"] = json.dumps({})

        query = text("""
            INSERT INTO raw.events (event_id, user_id, type_event, time_event, metadata)
            VALUES (:event_id, :user_id, :type_event, :time_event, :metadata)
        """)

        session.execute(query, event_data)
        session.commit()
        return {"status": "success", "event_type": event_data.get("type_event")}

    except Exception as e:
        session.rollback()
        print(f"Ошибка при сохранении таски в БД: {e}")
        raise e
    finally:
        session.close()
