
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///reports.db")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(
        text("""
        CREATE TABLE IF NOT EXISTS mybase (
            id TEXT PRIMARY KEY,
            file BYTEA,
            annotated_file BYTEA,
            severity REAL,
            longtitude DECIMAL(11,8),
            latitude DECIMAL (10,8),
            pothole_count INTEGER,
            created_at TEXT
        )
    """)
    )
    conn.commit()
