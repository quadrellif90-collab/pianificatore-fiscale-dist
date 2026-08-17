"""Analytics module: event tracking, metrics, reporting."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib

from appinfo import get_data_dir


class EventType(Enum):
    """Tipi di eventi tracciabili."""
    APP_START = "app_start"
    APP_CLOSE = "app_close"
    CALCULATION = "calculation"
    PROFILE_SAVE = "profile_save"
    PROFILE_LOAD = "profile_load"
    EXPORT_CSV = "export_csv"
    EXPORT_JSON = "export_json"
    EXPORT_PDF = "export_pdf"
    IMPORT_CSV = "import_csv"
    IMPORT_JSON = "import_json"
    REGIME_COMPARISON = "regime_comparison"
    WHAT_IF_SIMULATION = "what_if_simulation"
    AI_QUERY = "ai_query"
    AI_SUGGESTION = "ai_suggestion"
    ERROR = "error"
    SETTINGS_CHANGE = "settings_change"
    UPDATE_CHECK = "update_check"
    UPDATE_INSTALL = "update_install"


@dataclass
class AnalyticsEvent:
    """Evento di analytics."""
    event_type: str
    timestamp: str
    session_id: str
    user_hash: str
    data: Dict[str, Any]
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None


class AnalyticsManager:
    """Gestore analytics centralizzato."""
    
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.session_id = self._generate_session_id()
        self.user_hash = self._generate_user_hash()
        self.db_path = self._get_db_path()
        self._init_db()
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._event_buffer: List[AnalyticsEvent] = []
        self._flush_interval = 30  # secondi
        self._last_flush = time.time()
        
    def _generate_session_id(self) -> str:
        """Genera ID sessione univoco."""
        return hashlib.md5(f"{time.time()}{os.urandom(8).hex()}".encode()).hexdigest()[:16]
    
    def _generate_user_hash(self) -> str:
        """Genera hash anonimo utente (basato su hardware)."""
        import platform
        hw_info = f"{platform.node()}{platform.processor()}{platform.machine()}"
        return hashlib.sha256(hw_info.encode()).hexdigest()[:16]
    
    def _get_db_path(self) -> str:
        """Percorso database analytics."""
        data_dir = get_data_dir()
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, f"analytics_{self.app_name}.db")
    
    def _init_db(self) -> None:
        """Inizializza database analytics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    user_hash TEXT NOT NULL,
                    data TEXT NOT NULL,
                    duration_ms INTEGER,
                    success INTEGER NOT NULL,
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON events(event_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_session 
                ON events(session_id)
            """)
    
    def track(self, event_type: EventType, data: Dict[str, Any], 
              duration_ms: Optional[int] = None, success: bool = True, 
              error_message: Optional[str] = None) -> None:
        """Traccia un evento."""
        event = AnalyticsEvent(
            event_type=event_type.value,
            timestamp=datetime.now().isoformat(),
            session_id=self.session_id,
            user_hash=self.user_hash,
            data=data,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message
        )
        
        with self._lock:
            self._event_buffer.append(event)
            
            # Flush periodico
            if time.time() - self._last_flush > self._flush_interval:
                self._flush()
    
    def _flush(self) -> None:
        """Salva buffer su database."""
        if not self._event_buffer:
            return
        
        events_to_save = self._event_buffer.copy()
        self._event_buffer.clear()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                for event in events_to_save:
                    conn.execute(
                        """INSERT INTO events (event_type, timestamp, session_id, 
                           user_hash, data, duration_ms, success, error_message)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (event.event_type, event.timestamp, event.session_id,
                         event.user_hash, json.dumps(event.data), 
                         event.duration_ms, int(event.success), event.error_message)
                    )
                conn.commit()
        except Exception:
            # Re-add to buffer on failure
            self._event_buffer = events_to_save + self._event_buffer
        finally:
            self._last_flush = time.time()
    
    def track_calculation(self, regime: str, ral: float, netto: float, 
                          duration_ms: int, success: bool = True) -> None:
        """Traccia calcolo fiscale."""
        self.track(EventType.CALCULATION, {
            "regime": regime,
            "ral": ral,
            "netto": netto
        }, duration_ms=duration_ms, success=success)
    
    def track_ai_query(self, query: str, response_length: int, 
                       duration_ms: int, success: bool = True) -> None:
        """Traccia query AI."""
        self.track(EventType.AI_QUERY, {
            "query_hash": hashlib.md5(query.encode()).hexdigest()[:8],
            "query_length": len(query),
            "response_length": response_length
        }, duration_ms=duration_ms, success=success)
    
    def track_error(self, error: Exception, context: str) -> None:
        """Traccia errore."""
        self.track(EventType.ERROR, {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context
        }, success=False, error_message=str(error))
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Statistiche sessione corrente."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """SELECT event_type, COUNT(*) as count, 
                          AVG(duration_ms) as avg_duration,
                          SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as success_count
                   FROM events WHERE session_id = ?
                   GROUP BY event_type""",
                (self.session_id,)
            )
            events = [dict(row) for row in cursor.fetchall()]
            
            cursor = conn.execute(
                "SELECT COUNT(*) as total FROM events WHERE session_id = ?",
                (self.session_id,)
            )
            total = cursor.fetchone()[0]
            
            return {
                "session_id": self.session_id,
                "duration_seconds": time.time() - self._start_time,
                "total_events": total,
                "events_by_type": events
            }
    
    def get_usage_report(self, days: int = 30) -> Dict[str, Any]:
        """Report utilizzo ultimi N giorni."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Eventi per tipo
            cursor = conn.execute(
                """SELECT event_type, COUNT(*) as count, 
                          AVG(duration_ms) as avg_duration,
                          SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
                   FROM events WHERE timestamp > ?
                   GROUP BY event_type ORDER BY count DESC""",
                (since,)
            )
            by_type = [dict(row) for row in cursor.fetchall()]
            
            # Trend giornaliero
            cursor = conn.execute(
                """SELECT date(timestamp) as day, COUNT(*) as count
                   FROM events WHERE timestamp > ?
                   GROUP BY date(timestamp) ORDER BY day""",
                (since,)
            )
            daily = [dict(row) for row in cursor.fetchall()]
            
            # Sessioni uniche
            cursor = conn.execute(
                "SELECT COUNT(DISTINCT session_id) as sessions FROM events WHERE timestamp > ?",
                (since,)
            )
            sessions = cursor.fetchone()[0]
            
            return {
                "period_days": days,
                "total_sessions": sessions,
                "events_by_type": by_type,
                "daily_trend": daily
            }
    
    def export_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Esporta tutti i dati analytics."""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM events WHERE timestamp > ? ORDER BY timestamp",
                (since,)
            )
            events = [dict(row) for row in cursor.fetchall()]
        
        return {
            "app_name": self.app_name,
            "export_date": datetime.now().isoformat(),
            "period_days": days,
            "events": events
        }
    
    def close(self) -> None:
        """Chiude il manager (flush finale)."""
        self._flush()


# Istanza globale (singleton per app)
_analytics_instance: Optional[AnalyticsManager] = None


def get_analytics(app_name: str) -> AnalyticsManager:
    """Ottieni istanza analytics (singleton)."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = AnalyticsManager(app_name)
    return _analytics_instance


def track_event(event_type: EventType, data: Dict[str, Any], **kwargs) -> None:
    """Helper per tracciare evento rapido."""
    get_analytics("PianificatoreFiscale").track(event_type, data, **kwargs)