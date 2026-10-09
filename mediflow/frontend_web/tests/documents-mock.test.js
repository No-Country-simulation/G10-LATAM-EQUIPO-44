"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { documents, toRow } = require("../src/assets/js/documents-mock.js");

test("el listado preserva identificador, tipo, estado, prioridad y ubicación", () => {
  const source = documents.find((doc) => doc.clasificacion.nivel_prioridad === "Urgente");
  const row = toRow(source);
  assert.equal(row.id, source.documento_id);
  assert.equal(row.tipo, source.clasificacion.tipo_documento);
  assert.equal(row.prioridad, "urgente");
  assert.equal(row.estado, source.status);
  assert.equal(row.ruta, "procesados/" + source.almacenamiento_oci.ruta_objeto);
  assert.deepEqual(row.documento, source);
});
test("recibido conserva estado y muestra prioridad pendiente", () => {
  const row = toRow(documents[0]);
  assert.equal(row.estado, "recibido");
  assert.equal(row.prioridad, "pendiente");
  assert.equal(row.fecha, null);
});
test("auditoria_humana se adapta explícitamente al filtro de auditoría", () => {
  const row = toRow(documents.find((doc) => doc.status === "auditoria_humana"));
  assert.equal(row.estado, "auditoria");
  assert.equal(row.documento.status, "auditoria_humana");
});
test("rechaza una fila ajena al contrato", () => {
  assert.throws(() => toRow({ id: "legacy" }), /incompatible/);
});
