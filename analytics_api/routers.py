
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db
from schemas import UserEvent, UserBulkCreate
from tasks import celery_app

router = APIRouter(prefix="/api/v1", tags=["events"])

@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def create_event(event: UserEvent):
    """
    Принимает событие и отправляет его в очередь Celery для фоновой записи в БД.
    Не ждёт завершения записи, чтобы не блокировать клиента.
    """
    try:
        event_dict = event.model_dump(mode="json")
        celery_app.send_task("tasks.save_event", args=[event_dict])

        return {"status": "accepted", "message": "Event queued successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue event: {str(e)}"
        )


@router.post("/users/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_create_users(users: list[UserBulkCreate], db: AsyncSession = Depends(get_db)):
    """
    Массовая регистрация пользователей.
    Использует цикл для корректной работы с text() + параметрами.
    Все вставки происходят в рамках одной транзакции.
    """
    if not users:
        return {"status": "success", "message": "No users to process"}

    users_data = [
        {
            "user_id": u.user_id,
            "test_group": u.group_test,
            "date_registration": u.date_registration.replace(tzinfo=None)
        }
        for u in users
    ]

    query = text("""
        INSERT INTO raw.users (user_id, test_group, date_registration)
        VALUES (:user_id, :test_group, :date_registration)
        ON CONFLICT (user_id) DO NOTHING
    """)

    try:
        for user in users_data:
            await db.execute(query, user)
        await db.commit()

        return {
            "status": "success",
            "message": f"Successfully processed {len(users)} users"
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while processing users bulk: {str(e)}"
        )