"""Entrada manual de la entrega OCI; delega en la prueba de integración oficial."""

import os
from pathlib import Path

import pytest


def main():
    if os.environ.get("RUN_OCI_INTEGRATION") != "1":
        print("Configura RUN_OCI_INTEGRATION=1 para autorizar la prueba OCI real.")
        return 2
    test_path = Path(__file__).parent / "tests/test_oci_integration.py"
    return pytest.main([str(test_path), "-v", "-s"])


if __name__ == "__main__":
    raise SystemExit(main())
