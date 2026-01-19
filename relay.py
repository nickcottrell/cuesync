#!/usr/bin/env python3
"""
CueSync - Minimal, Disposable Cue Relay

This relay accepts authenticated CUE payloads from upstream (Cue Dispatcher),
stores them, and executes each one ONCE by sending its payload to the mapped webhook.

CueSync does NOT make decisions. It only validates, stores, and relays.
CueSync is cheaper to destroy than repair.
"""

import os
import sys
import json
import time
import hashlib
import hmac
import threading
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional
import yaml


class CueSyncConfig:
    """Single source of truth - loaded from config.yaml"""

    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Required fields
        self.cuesync_id: str = config["cuesync_id"]
        self.expires_at: datetime = datetime.fromisoformat(
            config["expires_at"].replace("Z", "+00:00")
        )
        self.upstream_key_hash: str = config["auth"]["upstream_key_hash"]
        self.tools: Dict[str, str] = config.get("tools", {})

        # Optional fields
        self.db_path: str = config.get("db_path", "cuesync.db")
        self.worker_interval_seconds: int = config.get("worker_interval_seconds", 10)
        self.max_retry_attempts: int = config.get("max_retry_attempts", 3)
        self.renewal_window_seconds: int = config.get("renewal_window_seconds", 86400)

    def is_expired(self) -> bool:
        """Check if CueSync has passed its expiration"""
        return datetime.now(timezone.utc) >= self.expires_at

    def can_renew(self) -> bool:
        """Check if we're in the renewal window"""
        time_until_expiration = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return 0 < time_until_expiration <= self.renewal_window_seconds

    def get_webhook_url(self, tool: str) -> Optional[str]:
        """Get webhook URL for a tool"""
        return self.tools.get(tool)


class CueStore:
    """SQLite-based storage for cues with execution tracking"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cues (
                    cue_id TEXT PRIMARY KEY,
                    tool TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    metadata TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    received_at TEXT NOT NULL,
                    executed_at TEXT,
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON cues(status)
            """)
            conn.commit()

    def store(self, cue: Dict) -> bool:
        """
        Store a cue for execution.
        Returns False if cue_id already exists.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO cues
                    (cue_id, tool, payload, metadata, received_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    cue["cue_id"],
                    cue["tool"],
                    json.dumps(cue.get("payload", {})),
                    json.dumps(cue.get("metadata", {})),
                    datetime.now(timezone.utc).isoformat(),
                ))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # Duplicate cue_id
            return False

    def get_pending(self, limit: int = 10) -> List[Dict]:
        """Get pending cues to execute"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM cues
                WHERE status = 'pending'
                ORDER BY received_at ASC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def mark_executed(self, cue_id: str):
        """Mark cue as successfully executed"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE cues
                SET status = 'executed',
                    executed_at = ?
                WHERE cue_id = ?
            """, (datetime.now(timezone.utc).isoformat(), cue_id))
            conn.commit()

    def mark_failed(self, cue_id: str, error: str, retry: bool = False):
        """Mark cue as failed (or increment retry count)"""
        with sqlite3.connect(self.db_path) as conn:
            if retry:
                conn.execute("""
                    UPDATE cues
                    SET retry_count = retry_count + 1,
                        error_message = ?
                    WHERE cue_id = ?
                """, (error, cue_id))
            else:
                conn.execute("""
                    UPDATE cues
                    SET status = 'failed',
                        error_message = ?,
                        executed_at = ?
                    WHERE cue_id = ?
                """, (error, datetime.now(timezone.utc).isoformat(), cue_id))
            conn.commit()

    def get_stats(self) -> Dict:
        """Get execution statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count
                FROM cues
                GROUP BY status
            """)
            stats = {row[0]: row[1] for row in cursor.fetchall()}

            cursor = conn.execute("SELECT COUNT(*) FROM cues")
            stats["total"] = cursor.fetchone()[0]

            return stats


class SignatureValidator:
    """Validates upstream signatures using dual-key handshake"""

    def __init__(self, upstream_key_hash: str):
        self.upstream_key_hash = upstream_key_hash

    def validate(self, payload: bytes, signature: str, upstream_key: str) -> bool:
        """
        Validate that:
        1. The provided upstream_key matches our stored hash
        2. The signature matches the payload
        """
        # Verify the upstream key matches our stored hash
        provided_key_hash = hashlib.sha256(upstream_key.encode()).hexdigest()
        if provided_key_hash != self.upstream_key_hash:
            return False

        # Verify the signature matches the payload
        expected_signature = hmac.new(
            upstream_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)


class CueExecutor:
    """Executes cues by sending payloads to their mapped webhook URLs"""

    def __init__(self, config: CueSyncConfig, max_retry_attempts: int = 3):
        self.config = config
        self.max_retry_attempts = max_retry_attempts

    def execute(self, cue: Dict) -> tuple[bool, Optional[str]]:
        """
        Execute cue by POSTing payload to webhook_url mapped from tool.
        Returns (success, error_message)
        """
        import urllib.request
        import urllib.error

        tool = cue["tool"]
        webhook_url = self.config.get_webhook_url(tool)

        if not webhook_url:
            return False, f"Tool '{tool}' not found in config"

        payload = json.loads(cue["payload"]) if isinstance(cue["payload"], str) else cue["payload"]

        try:
            payload_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-CueSync-ID": cue["cue_id"],
                    "X-CueSync-Tool": tool,
                }
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                if response.status >= 400:
                    return False, f"HTTP {response.status}"
                return True, None

        except urllib.error.HTTPError as e:
            return False, f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return False, f"URLError: {e}"
        except Exception as e:
            return False, f"Error: {e}"


class CueSyncRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for CueSync relay"""

    config: CueSyncConfig = None
    store: CueStore = None
    validator: SignatureValidator = None

    def log_message(self, format, *args):
        """Override to add timestamps"""
        timestamp = datetime.now(timezone.utc).isoformat()
        sys.stderr.write(f"[{timestamp}] {format % args}\n")

    def do_GET(self):
        """Health check and stats endpoints"""
        if self.path == "/health":
            if self.config.is_expired():
                self.send_response(410)  # Gone
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "expired",
                    "expires_at": self.config.expires_at.isoformat(),
                }).encode())
            else:
                stats = self.store.get_stats()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "ready",
                    "cuesync_id": self.config.cuesync_id,
                    "expires_at": self.config.expires_at.isoformat(),
                    "can_renew": self.config.can_renew(),
                    "tools": list(self.config.tools.keys()),
                    "stats": stats,
                }).encode())

        elif self.path == "/stats":
            stats = self.store.get_stats()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(stats).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Accept CUE payloads"""
        if self.config.is_expired():
            self.send_response(410)  # Gone
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "CueSync has expired",
                "expires_at": self.config.expires_at.isoformat(),
            }).encode())
            return

        if self.path == "/cue":
            content_length = int(self.headers.get("Content-Length", 0))
            payload = self.rfile.read(content_length)

            # Extract authentication headers
            signature = self.headers.get("X-CueSync-Signature")
            upstream_key = self.headers.get("X-CueSync-Key")

            if not signature or not upstream_key:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Missing authentication headers",
                }).encode())
                return

            # Validate signature
            if not self.validator.validate(payload, signature, upstream_key):
                self.send_response(403)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Invalid signature or key",
                }).encode())
                return

            # Parse cue
            try:
                cue = json.loads(payload)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Invalid JSON payload",
                }).encode())
                return

            # Validate cue structure
            if "cue_id" not in cue:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Missing cue_id",
                }).encode())
                return

            if "tool" not in cue:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Missing tool",
                }).encode())
                return

            # Validate tool exists
            if cue["tool"] not in self.config.tools:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": f"Unknown tool: {cue['tool']}",
                    "available_tools": list(self.config.tools.keys()),
                }).encode())
                return

            if "payload" not in cue:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Missing payload",
                }).encode())
                return

            # Store cue
            if not self.store.store(cue):
                self.send_response(409)  # Conflict
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": "Cue already exists",
                    "cue_id": cue["cue_id"],
                }).encode())
                return

            # Success
            self.send_response(202)  # Accepted
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "accepted",
                "cue_id": cue["cue_id"],
            }).encode())

        else:
            self.send_response(404)
            self.end_headers()


class CueSyncRelay:
    """Main relay orchestrator"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = CueSyncConfig(config_path)
        self.store = CueStore(self.config.db_path)
        self.validator = SignatureValidator(self.config.upstream_key_hash)
        self.executor = CueExecutor(self.config, self.config.max_retry_attempts)
        self.running = False
        self.worker_thread = None

    def start_http_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Start HTTP server to accept cues"""
        # Share instances with request handler
        CueSyncRequestHandler.config = self.config
        CueSyncRequestHandler.store = self.store
        CueSyncRequestHandler.validator = self.validator

        server = HTTPServer((host, port), CueSyncRequestHandler)
        print(f"[{datetime.now(timezone.utc).isoformat()}] CueSync relay started")
        print(f"  ID: {self.config.cuesync_id}")
        print(f"  Listening: {host}:{port}")
        print(f"  Worker interval: {self.config.worker_interval_seconds}s")
        print(f"  Expires: {self.config.expires_at.isoformat()}")
        print(f"  Database: {self.config.db_path}")
        print(f"  Tools configured: {len(self.config.tools)}")

        # Start worker thread
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print(f"\n[{datetime.now(timezone.utc).isoformat()}] Shutting down...")
            self.running = False
            server.shutdown()

    def _worker_loop(self):
        """Background thread that executes pending cues"""
        while self.running:
            time.sleep(self.config.worker_interval_seconds)

            if self.config.is_expired():
                print(f"[{datetime.now(timezone.utc).isoformat()}] EXPIRED - stopping worker")
                self.running = False
                break

            # Get pending cues
            pending = self.store.get_pending(limit=10)

            if not pending:
                continue

            timestamp = datetime.now(timezone.utc).isoformat()
            print(f"[{timestamp}] Processing {len(pending)} pending cues...")

            for cue in pending:
                cue_id = cue["cue_id"]
                tool = cue["tool"]
                webhook_url = self.config.get_webhook_url(tool)

                # Execute
                success, error = self.executor.execute(cue)

                if success:
                    self.store.mark_executed(cue_id)
                    print(f"  [{cue_id}] SUCCESS → {tool} ({webhook_url})")
                else:
                    retry_count = cue["retry_count"]
                    if retry_count < self.config.max_retry_attempts:
                        self.store.mark_failed(cue_id, error, retry=True)
                        print(f"  [{cue_id}] RETRY ({retry_count + 1}/{self.config.max_retry_attempts}): {error}")
                    else:
                        self.store.mark_failed(cue_id, error, retry=False)
                        print(f"  [{cue_id}] FAILED (max retries): {error}")


def main():
    """Entry point"""
    config_path = os.getenv("CUESYNC_CONFIG", "config.yaml")

    if not Path(config_path).exists():
        print(f"ERROR: Config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    relay = CueSyncRelay(config_path)

    # Check expiration before starting
    if relay.config.is_expired():
        print(f"ERROR: CueSync has expired (expires_at: {relay.config.expires_at.isoformat()})", file=sys.stderr)
        print("This relay must be destroyed and recreated.", file=sys.stderr)
        sys.exit(1)

    # Start relay
    host = os.getenv("CUESYNC_HOST", "0.0.0.0")
    port = int(os.getenv("CUESYNC_PORT", "8080"))

    relay.start_http_server(host, port)


if __name__ == "__main__":
    main()
