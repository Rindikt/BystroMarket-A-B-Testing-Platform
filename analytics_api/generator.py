from datetime import datetime, timedelta
import random
import time
import uuid

import httpx
import pandas as pd


API_URL = "http://analytics_api:8000/api/v1/events"
BULK_USERS_URL = "http://analytics_api:8000/api/v1/users/bulk"

FUNNEL_CONFIG = {
    "A": {
        "click_given_view": 0.40,
        "add_to_cart_given_click": 0.12,
        "purchase_given_cart": 0.20
    },
    "B": {
        "click_given_view": 0.42,
        "add_to_cart_given_click": 0.15,
        "purchase_given_cart": 0.20
    }
}

def get_period():
    today = datetime.now()

    # конец последней полной недели
    end_date = today - timedelta(days=today.weekday() + 1)

    end_date = end_date.replace(
        hour=23,
        minute=59,
        second=59,
        microsecond=0
    )

    start_date = end_date - timedelta(days=13)

    start_date = start_date.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    return start_date, end_date

def generate_activity_time():
    hour = random.choices(
        population=range(24),
        weights=[
            1,1,1,1,1,2,
            4,6,8,10,11,12,
            12,12,11,10,9,8,
            7,6,5,4,2,1
        ]
    )[0]

    minute = random.randint(0,59)
    second = random.randint(0,59)

    return hour, minute, second

def generate_users(
    count: int,
    start_date,
    end_date
) -> pd.DataFrame:
    """
    Генерирует пользователей, зарегистрированных
    за месяц до начала эксперимента.
    """

    registration_start = start_date - timedelta(days=30)

    period = int(
        (start_date - registration_start).total_seconds()
    )

    users = []

    for user_id in range(1, count + 1):

        reg_time = registration_start + timedelta(
            seconds=random.randint(0, period)
        )

        users.append({
            "user_id": user_id,
            "group_test": random.choice(["A", "B"]),
            "date_registration": reg_time
        })

    return pd.DataFrame(users)


def simulate_user_session(group: str) -> list[str]:
    events = ['view']
    etg = FUNNEL_CONFIG[group]
    if random.random()<etg['click_given_view']:
        events.append('click')
        if random.random()<etg['add_to_cart_given_click']:
            events.append('add_to_cart')
            if random.random()<etg['purchase_given_cart']:
                events.append('purchase')
    return events

def send_event_with_retry(
                        payload: dict,
                        max_retries: int = 3,
                        base_delay: float = 1.0):
    """Отправляет одно событие с повторными попытками при ошибках."""

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=httpx.Timeout(10.0)) as client:
                resp = client.post(API_URL, json=payload)

                if 200 <= resp.status_code < 300:
                    return True, resp.status_code

                elif resp.status_code == 429:
                    wait_time = base_delay * (2 ** attempt)
                    print(
                        f"Rate limit (429). Повтор через {wait_time:.1f} сек..."
                    )
                    time.sleep(wait_time)

                else:
                    print(
                        f"HTTP {resp.status_code}: {resp.text}"
                    )
                    return False, resp.status_code

        except httpx.TimeoutException:
            wait_time = base_delay * (2 ** attempt)
            print(
                f"Таймаут. Повтор через {wait_time:.1f} сек..."
            )
            time.sleep(wait_time)

        except Exception as e:
            print(f"Ошибка соединения: {e}")
            time.sleep(base_delay * (2 ** attempt))

    return False, None


def run_generator(
    user_df: pd.DataFrame,
    start_date,
    end_date,
    total_events_target=170000
):

    print("=" * 60)
    print("Генерация событий...")
    print("=" * 60)

    users = user_df.to_dict("records")

    sent = 0
    errors = 0

    weekday_weights = {
        0: 0.95,
        1: 0.97,
        2: 1.00,
        3: 1.02,
        4: 0.90,
        5: 1.15,
        6: 1.20
    }

    days = []

    current = start_date.date()

    while current <= end_date.date():

        weight = weekday_weights[current.weekday()]

        days.append(
            {
                "date": current,
                "weight": weight
            }
        )

        current += timedelta(days=1)

    total_weight = sum(
        d["weight"] for d in days
    )

    for day in days:

        target_events = int(
            total_events_target *
            day["weight"] /
            total_weight
        )

        print(
            f'{day["date"]}: '
            f'{target_events:,} событий'
        )

        generated = 0

        while generated < target_events:

            user = random.choice(users)

            sessions = random.choices(
                [1,2,3],
                weights=[0.72,0.22,0.06]
            )[0]

            for _ in range(sessions):

                hour, minute, second = generate_activity_time()

                session_time = datetime.combine(
                    day["date"],
                    datetime.min.time()
                ).replace(
                    hour=hour,
                    minute=minute,
                    second=second
                )

                for event in simulate_user_session(
                    user["group_test"]
                ):

                    if (
                        generated >= target_events
                        or sent >= total_events_target
                    ):
                        break

                    payload = {

                        "event_id": str(uuid.uuid4()),

                        "user_id": int(user["user_id"]),

                        "type_event": event,

                        "metadata":
                            {
                                "price":
                                random.randint(
                                    500,
                                    5000
                                )
                            }
                            if event == "purchase"
                            else {},

                        "time_event":
                            session_time.isoformat()
                    }

                    ok, status = send_event_with_retry(
                        payload
                    )

                    if ok:

                        sent += 1
                        generated += 1

                    else:

                        errors += 1

            if sent % 5000 == 0 and sent > 0:

                print(
                    f"{sent:,}/{total_events_target:,}"
                )

    print("=" * 60)
    print(f"Успешно отправлено : {sent:,}")
    print(f"Ошибок             : {errors:,}")
    print("=" * 60)

def wait_for_api(max_retries=30, delay=2):
    print(f"Ожидание запуска API (макс. {max_retries * delay} сек)...")
    for i in range(max_retries):
        try:
            resp = httpx.get("http://analytics_api:8000/health", timeout=5.0)
            if resp.status_code == 200:
                print("API готов к работе!")
                return
        except Exception as e:
            print(f"API ещё не отвечает (попытка {i+1}/{max_retries}): {e}")
        time.sleep(delay)
    raise ConnectionError("API так и не запустился. Проверь логи контейнера analytics_api.")


if __name__ == "__main__":

    print("=" * 60)
    print("Запуск генератора данных")
    print("=" * 60)

    wait_for_api()

    print("\nГенерация пользователей...")
    start_date, end_date = get_period()
    df_users = generate_users(24_000, start_date, end_date)

    print(f"✓ Пользователей сгенерировано: {len(df_users):,}")

    df_prepared = df_users.copy()
    df_prepared["date_registration"] = (
        df_prepared["date_registration"]
        .dt.strftime("%Y-%m-%dT%H:%M:%S")
    )

    users_list = df_prepared.to_dict(orient="records")

    print("Регистрация пользователей...")

    try:
        response = httpx.post(
            BULK_USERS_URL,
            json=users_list,
            timeout=30.0
        )

        if response.status_code in (200, 201):
            print("✓ Пользователи успешно зарегистрированы.")
        else:
            print(
                f"Ошибка регистрации пользователей: "
                f"{response.status_code}"
            )
            print(response.text)
            exit(1)

    except Exception as err:
        print(f"Ошибка соединения: {err}")
        exit(1)

    run_generator(
        df_users,
        start_date,
        end_date,
        total_events_target=170_000
    )

    print("\nИсторический слой успешно создан.")

    #run_generator(df_users, is_historical=False)