/* Agregado por Edil: la ampliación documental conserva los consumidores existentes.
   Todas las respuestas HTTP son fixtures locales, sin OCI ni Gemini. */
const test = require("node:test");
const assert = require("node:assert/strict");
const { getDocument, getDocuments, isValidDocument } = require("../src/assets/js/documents-api.js");

const kinds = ["Receta Médica", "Informe de Laboratorio", "Informe de Estudio por Imágenes",
  "Orden / Solicitud de Procedimiento", "Epicrisis / Informe de Alta", "Certificado Médico"];
const addedFields = ["profesional_emisor", "resultados_laboratorio", "hallazgos", "conclusion",
  "procedimiento_solicitado", "indicacion_solicitud", "resumen_evolucion", "indicacion_alta",
  "destino_alta", "seguimiento", "contenido_certificacion", "periodo_certificado"];

function document(kind, { review = false, urgent = false } = {}) {
  return {
    documento_id: "DOC-SYNTHETIC-COMPAT", status: review ? "auditoria_humana" : "procesado", cargado_por: "auditor-sintetico",
    clasificacion: { tipo_documento: kind, especialidad: null, nivel_prioridad: urgent ? "Urgente" : "Rutina", score_confianza_clasificacion: 0.95 },
    datos_extraidos: {
      paciente: { nombre: "Persona ficticia", edad: null }, medico_solicitante: { nombre: null, matricula: null },
      profesional_emisor: { nombre: "Emisor ficticio", matricula: null },
      estudio_realizado: "Estudio sintético", diagnostico_principal: null, cie10_sugerido: null,
      medicamentos_recetados: kind === "Receta Médica" ? [{ medicamento: "Medicación sintética", dosis: null }] : [],
      resultados_laboratorio: kind === "Informe de Laboratorio" ? [{ examen: "Examen sintético", valor: "Negativo", unidad: null, rango_referencia: null }] : [],
      hallazgos: null, conclusion: kind === "Informe de Estudio por Imágenes" ? "Conclusión documental ficticia." : null,
      procedimiento_solicitado: kind === "Orden / Solicitud de Procedimiento" ? "Procedimiento ficticio" : null,
      indicacion_solicitud: null, resumen_evolucion: kind === "Epicrisis / Informe de Alta" ? "Resumen ficticio" : null,
      indicacion_alta: kind === "Epicrisis / Informe de Alta" ? "Cierre documental ficticio" : null,
      destino_alta: null, seguimiento: null,
      contenido_certificacion: kind === "Certificado Médico" ? "Certificación ficticia" : null, periodo_certificado: null,
    },
    decision_enrutamiento: { destino_principal: review ? "Cola_Revision_Humana" : "Cola_Historia_Clinica",
      requiere_auditoria_humana: review, justificacion_enrutamiento: "Compatibilidad de contrato con datos sintéticos." },
    notificacion_generada: null,
    almacenamiento_oci: { bucket: review ? "auditoria_humana" : "procesados", ruta_objeto: "DOC-SYNTHETIC-COMPAT.txt", status_backup: "exito" },
  };
}

for (const kind of kinds) {
  test("GET conserva todos los campos aditivos de " + kind, async () => {
    const fixture = document(kind), before = structuredClone(fixture);
    let calls = 0;
    assert.equal(isValidDocument(fixture, fixture.documento_id), true);
    const result = await getDocument(fixture.documento_id, { fetchImpl: async (url, options) => {
      calls++;
      assert.equal(url.pathname, "/api/documents/" + fixture.documento_id);
      assert.equal(options.method, "GET");
      return { ok: true, json: async () => structuredClone(fixture) };
    } });
    assert.equal(calls, 1);
    assert.deepEqual(result, before);
    assert.deepEqual(fixture, before);
    for (const key of addedFields) assert.ok(Object.prototype.hasOwnProperty.call(result.datos_extraidos, key));
  });
}

test("GET de JSON histórico permanece compatible y no inventa campos ausentes", async () => {
  const fixture = document("Informe de Laboratorio");
  delete fixture.cargado_por;
  for (const field of addedFields) delete fixture.datos_extraidos[field];
  assert.equal(isValidDocument(fixture, fixture.documento_id), true);
  const result = await getDocument(fixture.documento_id, { fetchImpl: async () => ({ ok: true, json: async () => structuredClone(fixture) }) });
  assert.deepEqual(result, fixture);
  for (const field of addedFields) assert.equal(Object.prototype.hasOwnProperty.call(result.datos_extraidos, field), false);
});

test("el listado conserva datos específicos de los seis tipos sin adaptarlos a otro significado", async () => {
  const fixtures = kinds.map(kind => document(kind));
  const result = await getDocuments({ fetchImpl: async () => ({ ok: true, json: async () => structuredClone(fixtures) }) });
  assert.deepEqual(result, fixtures);
  assert.equal(result[1].datos_extraidos.resultados_laboratorio[0].valor, "Negativo");
  assert.equal(result[3].datos_extraidos.procedimiento_solicitado, "Procedimiento ficticio");
});

for (const review of [false, true]) {
  test("la ampliación conserva urgencia y revisión del backend: review=" + review, async () => {
    const fixture = document("Informe de Estudio por Imágenes", { review, urgent: true });
    const result = await getDocument(fixture.documento_id, { fetchImpl: async () => ({ ok: true, json: async () => fixture }) });
    assert.equal(result.clasificacion.nivel_prioridad, "Urgente");
    assert.equal(result.decision_enrutamiento.requiere_auditoria_humana, review);
    assert.equal(result.datos_extraidos.conclusion, fixture.datos_extraidos.conclusion);
  });
}
