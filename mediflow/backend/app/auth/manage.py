"""Agregado por Edil: gestión local de cuentas; nunca recibe claves por argv."""
import argparse
import getpass
import sqlite3

from app.core.environment import load_environment
from .store import SessionStore, normalize_username, validate_new_password


def _new_password():
    first = getpass.getpass("Contraseña nueva (mínimo 12 caracteres): ")
    second = getpass.getpass("Repite la contraseña: ")
    if first != second:
        raise ValueError("Las contraseñas no coinciden.")
    validate_new_password(first)
    return first


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["add-auditor", "add-user", "reset-password", "disable-user"])
    parser.add_argument("username")
    args = parser.parse_args()
    load_environment()
    try:
        username = normalize_username(args.username)
        store = SessionStore()
        if args.command in {"add-auditor", "add-user"}:
            store.add_user(username, _new_password(), can_review=args.command == "add-auditor")
            print("Cuenta de MediFlow creada. La contraseña no se muestra ni se guarda en texto plano.")
        elif args.command == "reset-password":
            store.reset_password(username, _new_password())
            print("Contraseña actualizada y sesiones anteriores revocadas.")
        else:
            store.disable_user(username)
            print("Cuenta deshabilitada y sesiones revocadas.")
    except sqlite3.IntegrityError:
        parser.exit(1, "La cuenta ya existe; no se sobrescribió.\n")
    except (ValueError, OSError, sqlite3.Error) as error:
        # No incluir diagnósticos SQLite ni rutas locales en salidas compartidas.
        message = str(error) if isinstance(error, ValueError) else "No se pudo acceder al almacenamiento local de usuarios."
        parser.exit(1, message + "\n")
    except (EOFError, KeyboardInterrupt):
        parser.exit(1, "\nCreación de cuenta cancelada.\n")


if __name__ == "__main__":
    main()
