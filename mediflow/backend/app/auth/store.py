"""Agregado por Edil: contraseñas con scrypt y sesiones opacas en SQLite local.

La base privada no contiene documentos clínicos. No usa cuentas de Tailscale,
OCI o Gemini y no crea usuarios predeterminados.
"""
from dataclasses import dataclass
from contextlib import contextmanager
import base64
import hashlib
import os
from pathlib import Path
import re
import secrets
import sqlite3
import time
from urllib.parse import urlsplit

from app.core.review_auth import Principal

COOKIE_NAME = "mediflow_session"
DEFAULT_DB = Path(__file__).resolve().parents[3] / ".local" / "auth.sqlite3"
SCRYPT_N, SCRYPT_R, SCRYPT_P = 32768, 8, 3
LOGIN_WINDOW_SECONDS = 15 * 60
MAX_LOGIN_FAILURES = 5
MAX_ADDRESS_FAILURES = 20
_DUMMY_SALT = b"MediFlowNoUser001"


class InvalidCredentials(Exception):
    pass


class LoginRateLimited(Exception):
    pass


def normalize_username(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@+-]{0,127}", value):
        raise ValueError("El usuario debe tener entre 1 y 128 caracteres válidos.")
    return value.casefold()


def validate_new_password(password: str) -> None:
    if not isinstance(password, str) or not 12 <= len(password) <= 1024:
        raise ValueError("La contraseña debe tener entre 12 y 1024 caracteres.")


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N,
                          r=SCRYPT_R, p=SCRYPT_P, dklen=32, maxmem=64 * 1024 * 1024)


def hash_password(password: str) -> str:
    validate_new_password(password)
    salt = secrets.token_bytes(16)
    hashed = _derive(password, salt)
    return "scrypt$32768$8$3$" + base64.b64encode(salt).decode("ascii") + "$" + base64.b64encode(hashed).decode("ascii")


def verify_password(password: str, encoded: str | None) -> bool:
    # Agregado por Edil: el usuario inexistente también realiza la derivación;
    # nunca se devuelve si el nombre existe ni se registra la contraseña.
    if not encoded:
        _derive(password, _DUMMY_SALT)
        return False
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if (algorithm, n, r, p) != ("scrypt", "32768", "8", "3"):
            return False
        decoded_salt = base64.b64decode(salt, validate=True)
        decoded_expected = base64.b64decode(expected, validate=True)
        if len(decoded_salt) != 16 or len(decoded_expected) != 32:
            return False
        return secrets.compare_digest(_derive(password, decoded_salt), decoded_expected)
    except (ValueError, TypeError):
        return False


@dataclass(frozen=True)
class AuthSettings:
    db_file: Path = DEFAULT_DB
    session_ttl_seconds: int = 8 * 60 * 60
    public_origin: str = ""

    def __post_init__(self):
        public_files = DEFAULT_DB.parent.parent / "frontend_web" / "src"
        if self.db_file.resolve().is_relative_to(public_files.resolve()):
            raise ValueError("La base de usuarios no puede estar dentro del directorio web público.")
        if not 900 <= self.session_ttl_seconds <= 12 * 60 * 60:
            raise ValueError("MEDIFLOW_SESSION_TTL_SECONDS debe estar entre 900 y 43200.")
        if self.public_origin:
            parsed = urlsplit(self.public_origin)
            loopback_http = parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            if ((parsed.scheme != "https" and not loopback_http) or not parsed.hostname
                    or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                    or self.public_origin != f"{parsed.scheme}://{parsed.netloc.lower()}"):
                raise ValueError("MEDIFLOW_PUBLIC_ORIGIN debe ser un origen HTTPS sin ruta; HTTP solo en loopback.")
            _ = parsed.port

    @classmethod
    def from_environment(cls):
        path = os.getenv("MEDIFLOW_AUTH_DB_FILE", "").strip()
        db_file = Path(path).expanduser() if path else DEFAULT_DB
        if not db_file.is_absolute():
            db_file = DEFAULT_DB.parent.parent / db_file
        return cls(db_file=db_file.resolve(),
                   session_ttl_seconds=int(os.getenv("MEDIFLOW_SESSION_TTL_SECONDS", "28800")),
                   public_origin=os.getenv("MEDIFLOW_PUBLIC_ORIGIN", "").strip())


class SessionStore:
    def __init__(self, settings: AuthSettings | None = None, *, clock=time.time):
        self.settings = settings or AuthSettings.from_environment()
        self.clock = clock

    def _connection(self, *, write=False):
        path = self.settings.db_file
        if write:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            connection = sqlite3.connect(path, timeout=10)
            try:
                connection.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
                    can_review INTEGER NOT NULL CHECK(can_review IN (0,1)),
                    enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
                    created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY, username TEXT NOT NULL,
                    expires_at REAL NOT NULL, created_at REAL NOT NULL,
                    FOREIGN KEY(username) REFERENCES users(username));
                CREATE TABLE IF NOT EXISTS login_attempts (
                    bucket TEXT PRIMARY KEY, failures INTEGER NOT NULL,
                    window_start REAL NOT NULL);
                """)
                if os.name != "nt":
                    path.chmod(0o600)
            except (sqlite3.Error, OSError):
                connection.close()
                raise
        else:
            if not path.is_file():
                return None
            connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _write_connection(self):
        connection = self._connection(write=True)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def add_user(self, username: str, password: str, *, can_review=False):
        username = normalize_username(username)
        encoded = hash_password(password)
        with self._write_connection() as connection:
            # No sobrescribir cuentas ni claves existentes de forma accidental.
            connection.execute("INSERT INTO users(username,password_hash,can_review,created_at) VALUES(?,?,?,?)",
                               (username, encoded, int(can_review), self.clock()))
        return Principal(username, bool(can_review))

    def reset_password(self, username: str, password: str):
        username = normalize_username(username)
        encoded = hash_password(password)
        with self._write_connection() as connection:
            result = connection.execute("UPDATE users SET password_hash=? WHERE username=?", (encoded, username))
            if result.rowcount != 1:
                raise ValueError("La cuenta no existe.")
            connection.execute("DELETE FROM sessions WHERE username=?", (username,))

    def disable_user(self, username: str):
        username = normalize_username(username)
        with self._write_connection() as connection:
            result = connection.execute("UPDATE users SET enabled=0 WHERE username=?", (username,))
            if result.rowcount != 1:
                raise ValueError("La cuenta no existe.")
            connection.execute("DELETE FROM sessions WHERE username=?", (username,))

    def authenticate(self, username: str, password: str, *, client_address="unknown"):
        username = normalize_username(username)
        if not isinstance(password, str) or not 1 <= len(password) <= 1024:
            raise InvalidCredentials()
        now = self.clock()
        # Solo se guarda un hash del identificador del limitador, no la IP.
        bucket = hashlib.sha256(("user\0" + username + "\0" + client_address).encode()).hexdigest()
        address_bucket = hashlib.sha256(("address\0" + client_address).encode()).hexdigest()
        with self._write_connection() as connection:
            # Serializar intentos para que dos peticiones paralelas no eviten
            # el contador persistido. SQLite solo vive en el servidor local.
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM login_attempts WHERE window_start<=?", (now - LOGIN_WINDOW_SECONDS,))
            attempts = {}
            for key, maximum in [(bucket, MAX_LOGIN_FAILURES), (address_bucket, MAX_ADDRESS_FAILURES)]:
                attempt = connection.execute("SELECT failures,window_start FROM login_attempts WHERE bucket=?", (key,)).fetchone()
                in_window = attempt is not None and now - attempt["window_start"] < LOGIN_WINDOW_SECONDS
                start = attempt["window_start"] if in_window else now
                failures = attempt["failures"] if in_window else 0
                if failures >= maximum:
                    raise LoginRateLimited()
                attempts[key] = (failures, start)
            row = connection.execute("SELECT password_hash,can_review,enabled FROM users WHERE username=?", (username,)).fetchone()
            valid = verify_password(password, row["password_hash"] if row else None)
            if not row or not row["enabled"] or not valid:
                for key, (failures, start) in attempts.items():
                    connection.execute("INSERT INTO login_attempts(bucket,failures,window_start) VALUES(?,?,?) "
                                       "ON CONFLICT(bucket) DO UPDATE SET failures=excluded.failures,window_start=excluded.window_start",
                                       (key, failures + 1, start))
                connection.commit()
                raise InvalidCredentials()
            connection.execute("DELETE FROM login_attempts WHERE bucket=?", (bucket,))
            connection.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))
            token = secrets.token_urlsafe(32)
            connection.execute("INSERT INTO sessions(token_hash,username,expires_at,created_at) VALUES(?,?,?,?)",
                               (hashlib.sha256(token.encode()).hexdigest(), username, now + self.settings.session_ttl_seconds, now))
            return token, Principal(username, bool(row["can_review"]))

    def get_principal(self, token: str | None):
        if not token or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
            return None
        connection = self._connection()
        if connection is None:
            return None
        try:
            row = connection.execute("SELECT users.username,users.can_review FROM sessions JOIN users USING(username) "
                "WHERE sessions.token_hash=? AND sessions.expires_at>? AND users.enabled=1",
                (hashlib.sha256(token.encode()).hexdigest(), self.clock())).fetchone()
            return Principal(row["username"], bool(row["can_review"])) if row else None
        finally:
            connection.close()

    def revoke(self, token: str | None):
        if not token or not re.fullmatch(r"[A-Za-z0-9_-]{43}", token) or not self.settings.db_file.is_file():
            return
        with self._write_connection() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))


def get_principal_from_session(token: str | None):
    return SessionStore().get_principal(token)
