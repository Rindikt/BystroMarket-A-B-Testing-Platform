import os
import pandas as pd
import scipy.stats as stats
from tasks import engine


POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")

DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres:5432/{POSTGRES_DB}"

query = '''
    SELECT *
    FROM raw.events e
    JOIN raw.users u ON u.user_id = e.user_id
'''

df = pd.read_sql(query, engine)
