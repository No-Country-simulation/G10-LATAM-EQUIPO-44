"""Servidor solo de pruebas: API/gestor reales, SDK sustituido por memoria.

Agregado por Edil. No usa claves ni buckets reales; bloquea conexiones salientes.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
from threading import Lock
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
os.environ["GEMINI_API_KEY"] = ""
os.environ["RUN_OCI_INTEGRATION"] = "0"
real_connect = socket.socket.connect


def local_connect(sock, address):
    if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
        raise RuntimeError("External networking disabled in test fixture")
    return real_connect(sock, address)


socket.socket.connect = local_connect

import uvicorn
from oci.exceptions import ServiceError
from app.main import app
from app.api import routes
from app.core.oci_client import OCISettings, OCIStorageManager
from app.core.review_auth import Principal, require_auditor
from app.auth.store import AuthSettings, SessionStore, get_principal_from_session

# Agregado por Edil: identidad ficticia exclusiva de este proceso de pruebas.
# El servidor real no instala overrides ni permite introducir reviewer_id libre.
app.dependency_overrides[require_auditor] = lambda: Principal("test-auditor", True)

# Agregado por Edil: comprobar el formulario con usuarios de prueba reales
# del nuevo gestor, siempre en una base temporal y sin servicios externos.
local_auth_test = "--local-auth" in sys.argv
if local_auth_test:
    import tempfile
    os.environ["MEDIFLOW_AUTH_DB_FILE"] = str(Path(tempfile.mkdtemp(prefix="MediFlow-synthetic-auth-")) / "auth.sqlite3")
    os.environ["MEDIFLOW_PUBLIC_ORIGIN"] = ""
    SessionStore().add_user("auditor-sintetico", "Synthetic-password-only-2026", can_review=True)
    app.dependency_overrides.pop(require_auditor, None)


class FakeServiceError(ServiceError):
    def __init__(self, status):
        # El gestor real diferencia un 404 del SDK de cualquier excepción.
        # Simular el tipo correcto sin efectuar ninguna solicitud a OCI.
        super().__init__(status=status, code="SyntheticTestError", headers={}, message="Synthetic local storage error")


class MemoryObjectStorage:
    def __init__(self):
        self.objects = {}
        self.lock = Lock()
        for doc_id in ["DOC-SYNTHETIC-APPROVE", "DOC-SYNTHETIC-REJECT"]:
            doc = {
                "documento_id": doc_id, "status": "auditoria_humana",
                "clasificacion": {"tipo_documento": "Receta Médica", "especialidad": None,
                                  "nivel_prioridad": "Urgente", "score_confianza_clasificacion": 0.5},
                "datos_extraidos": {"paciente": {"nombre": "Persona ficticia", "edad": None},
                                    "medico_solicitante": {"nombre": None, "matricula": None},
                                    "estudio_realizado": None, "diagnostico_principal": None,
                                    "cie10_sugerido": None, "medicamentos_recetados": []},
                "decision_enrutamiento": {"destino_principal": "Cola_Revision_Humana", "requiere_auditoria_humana": True,
                                           "justificacion_enrutamiento": "Caso sintético de integración local, sin datos clínicos reales."},
                "notificacion_generada": None,
                "almacenamiento_oci": {"bucket": "auditoria_humana", "ruta_objeto": doc_id + ".txt", "status_backup": "exito"},
            }
            self.objects[("auditoria_humana", doc_id + ".json")] = json.dumps(doc).encode()

    def put_object(self, *, bucket_name, object_name, put_object_body, if_none_match=None, **kwargs):
        key = (bucket_name, object_name)
        with self.lock:
            if if_none_match == "*" and key in self.objects:
                raise FakeServiceError(412)
            self.objects[key] = bytes(put_object_body)
        checksum = base64.b64encode(hashlib.md5(put_object_body).digest()).decode()
        return SimpleNamespace(headers={"opc-content-md5": checksum})

    def get_object(self, *, bucket_name, object_name, **kwargs):
        if (bucket_name, object_name) not in self.objects:
            raise FakeServiceError(404)
        return SimpleNamespace(data=SimpleNamespace(content=self.objects[(bucket_name, object_name)]))

    def head_object(self, **kwargs):
        self.get_object(**kwargs)
        return SimpleNamespace(headers={})

    def list_objects(self, *, bucket_name, prefix="", limit=None, **kwargs):
        with self.lock:
            names = sorted(name for bucket, name in self.objects if bucket == bucket_name and name.startswith(prefix))
        return SimpleNamespace(data=SimpleNamespace(objects=[SimpleNamespace(name=n) for n in names[:limit]], next_start_with=None))


manager = OCIStorageManager(OCISettings.from_environment({"OCI_NAMESPACE": "test-local-only"}), object_storage_client=MemoryObjectStorage())
routes.OCIStorageManager = lambda: manager
def run():
    # Agregado por Edil: modo visual aislado para verificar el HTML real.
    # Estos controles y sustitutos solo existen en este servidor de tests.
    if "--web" in sys.argv:
        from fastapi import Request
        from fastapi.responses import HTMLResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles

        web_root = Path(__file__).resolve().parents[2] / "src"
        failure = {"enabled": False}

        @app.middleware("http")
        async def test_error_mode(request: Request, call_next):
            if failure["enabled"] and request.method == "GET" and request.url.path.startswith("/api/"):
                return JSONResponse({"detail": "Synthetic test outage"}, status_code=503)
            return await call_next(request)

        @app.post("/__test__/failure", include_in_schema=False)
        async def toggle_test_failure(request: Request):
            failure["enabled"] = (await request.body()).decode() == "on"
            return {"synthetic": True, "failure_enabled": failure["enabled"]}

        class TestWebFiles(StaticFiles):
            async def get_response(self, path, scope):
                if path.endswith(".html"):
                    # StaticFiles valida que la ruta permanezca dentro de web_root.
                    response = await super().get_response(path, scope)
                    if response.status_code == 200:
                        html = Path(response.path).read_text(encoding="utf-8")
                        identity = {"login": "test-auditor", "canReview": True}
                        if local_auth_test:
                            from starlette.requests import HTTPConnection
                            principal = get_principal_from_session(HTTPConnection(scope).cookies.get("mediflow_session"))
                            identity = {"login": principal.login, "canReview": principal.can_review} if principal else None
                        config = ('<script>window.MEDIFLOW_API_BASE_URL=location.origin;'
                                  'window.MEDIFLOW_REVIEW_CONTRACT_APPROVED=true;'
                                  f'window.MEDIFLOW_AUTHENTICATED_USER={json.dumps(identity)};</script>')
                        html = html.replace("</head>", config + "</head>")
                        banner = '''<aside style="padding:8px;background:#fff0d6;color:#15324c;font:14px sans-serif;position:fixed;bottom:0;left:0;right:0;z-index:9999" aria-label="Controles de prueba">
<strong>PRUEBA LOCAL SINTÉTICA — almacenamiento en memoria, sin OCI/Gemini.</strong>
<button type="button" id="testFailOn">Simular HTTP 503</button> <button type="button" id="testFailOff">Restaurar consultas</button><span id="testModeStatus" role="status"></span>
</aside><script>
document.getElementById('testFailOn').onclick=()=>fetch('/__test__/failure',{method:'POST',body:'on'}).then(()=>document.getElementById('testModeStatus').textContent='Fallo sintético activado');
document.getElementById('testFailOff').onclick=()=>fetch('/__test__/failure',{method:'POST',body:'off'}).then(()=>document.getElementById('testModeStatus').textContent='Consultas restauradas');
</script>'''
                        html = html.replace("</body>", banner + "</body>")
                        return HTMLResponse(html, headers={"Cache-Control": "no-store"})
                return await super().get_response(path, scope)

        app.mount("/__test__/web", TestWebFiles(directory=web_root), name="synthetic-web-test")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    print(json.dumps({"port": listener.getsockname()[1], "synthetic": True, "oci": "in-memory-test-double"}), flush=True)
    uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False)).run(sockets=[listener])


if __name__ == "__main__":
    run()
