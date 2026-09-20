import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from models import Offer

DB_PATH = Path(__file__).parent / 'offers.db'

class Storage:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS seen_offers (
                    id TEXT PRIMARY KEY,
                    slug TEXT NOT NULL,
                    title TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    reason TEXT,
                    price REAL,
                    volunteer INTEGER,
                    processed_at TEXT NOT NULL,
                    created_at TEXT
                )
            ''')
            conn.commit()

    def is_offer_seen(self, offer_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM seen_offers WHERE id = ?', (offer_id,))
            return cursor.fetchone() is not None

    def save_offer(self, offer: Offer, decision: str, reason: str):
        now = datetime.utcnow().isoformat()
        price = offer.pricing.value if offer.pricing else 0.0
        volunteer = 1 if (offer.pricing and offer.pricing.volunteer) else 0
        with self._get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO seen_offers 
                (id, slug, title, decision, reason, price, volunteer, processed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                offer.id,
                offer.slug,
                offer.title,
                decision,
                reason,
                price,
                volunteer,
                now,
                offer.createdAt
            ))
            conn.commit()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM seen_offers ORDER BY processed_at DESC LIMIT ?', (limit,))
            return [dict(row) for row in cursor.fetchall()]

storage = Storage()
