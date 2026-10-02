# MediFlow 🏥⚡

Sistema inteligente de triaje médico automatizado, extracción de información clínica mediante IA y auditoría en tiempo real en la nube Oracle Cloud Infrastructure (OCI).

---

## 📌 Organización Sprint 1 (G10-LATAM-EQUIPO-44)

Durante el Sprint 1, cada integrante trabaja dentro de su espacio asignado para avanzar de forma paralela:

- **Nicolás:** `data_ai/`
- **Laura:** `data_ai/docs/`
- **Flor:** `frontend_web/`
- **José, Drazen, Eliana, Brando:** `backend/`
- **Edil:** `frontend_mobile/`

---

## 👥 Células de Trabajo y Responsables

| Célula | Integrantes | Foco de Desarrollo |
| :--- | :--- | :--- |
| **🛠️ Backend** | Drazen, José, Eliana, Brando | API REST (FastAPI), Integración OCI, Manejo de errores y Esquemas Pydantic |
| **📊 Data & IA** | Nicolás, Laura | Inferencia LLM, Prompt Engineering, Dataset de evaluación y Matriz de estados |
| **🌐 Frontend Web** | Flor | Panel de auditoría clínica y maquetado Web (Streamlit / React) |
| **📱 Frontend Mobile** | Edil | Aplicación móvil Flutter para captura y seguimiento de estado |

---

## 📁 Arquitectura del Repositorio

```text
mediflow/
├── .gitignore
├── README.md
├── .env.example
├── requirements.txt
│
├── backend/                      # 🛠️ Célula Backend (Drazen, José, Eliana, Brando)
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # Servidor principal (FastAPI)
│   │   ├── api/                  # Endpoints REST (Drazen)
│   │   │   ├── __init__.py
│   │   │   └── routes.py         # POST /triage, GET /documents, PUT /approve
│   │   ├── core/                 # Lógica de OCI y Resiliencia
│   │   │   ├── __init__.py
│   │   │   ├── oci_client.py     # Módulo de conexión OCI (Eliana)
│   │   │   └── error_handler.py  # Wrapper de errores y excepciones (Brando)
│   │   └── models/               # Modelos Pydantic y Contrato de datos
│   │       ├── __init__.py
│   │       └── schemas.py        # JSON Schema oficial (Eliana)
│   └── tests/
│       └── test_oci_integration.py # Script de prueba de OCI (Brando)
│
├── data_ai/                      # 📊 Célula Data & IA (Nicolás, Laura)
│   ├── dataset/                  # Documentos de prueba (Nicolás)
│   │   ├── normal/               # Ejemplos de rutina
│   │   ├── urgente/              # Ejemplos críticos (TEP, infarto)
│   │   └── ambiguo/              # Documentos borrosos o incompletos
│   ├── docs/
│   │   └── matriz_estados.md     # Documento de Reglas y Estados (Laura)
│   ├── prompts/
│   │   └── master_prompt.txt     # Prompt maestro de extracción (Nicolás)
│   └── test_llm.py               # Script de pruebas de inferencia LLM
│
├── frontend_web/                 # 🌐 Célula Frontend Web (Flor)
│   ├── wireframes/               # Diseños estructurales del panel de auditoría (Flor)
│   └── src/                      # Código base del maquetado Web (Streamlit/React)
│       └── README.md
│
└── frontend_mobile/              # 📱 Célula Mobile (Edil)
    └── mediflow_app/             # Proyecto Base en Flutter (Edil)
        ├── lib/
        │   ├── main.dart
        │   └── screens/          # UI Selección local y Estado
        └── pubspec.yaml