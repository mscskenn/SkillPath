import os

import psycopg
from dotenv import load_dotenv


def get_connection() -> psycopg.Connection:
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")
    return psycopg.connect(database_url)
