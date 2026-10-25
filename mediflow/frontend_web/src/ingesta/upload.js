/* Agregado por Edil: carga real independiente del prototipo MTS conservado. */
(function (root) {
  'use strict';
  function mount(doc, options = {}) {
    const $ = s => doc.querySelector(s), client = options.client || root.MediFlowTriageApi.createClient();
    const documents = options.documents || root.MediFlowDocumentsApi;
    let storage;
    try { storage = options.storage || root.sessionStorage; } catch (_) { /* Navegador sin almacenamiento. */ }
    const key = 'mediflow-ingesta-pending-v1';
    let busy = false, locked = false, documentId = null, metadata = null, phase = 'selected';
    try {
      const pending = JSON.parse(storage?.getItem(key) || 'null');
      if (pending) {
        locked = true; documentId = pending.documentId || null;
        if (pending.file && typeof pending.file.name === 'string' && Number.isFinite(pending.file.size)) metadata = pending.file;
      }
    } catch (_) { locked = true; }
    const viewer = (options.viewer || root.MediFlowDocumentsApi.createFileViewer(doc, 'uploadLocal', {
      onError: () => message('No se puede visualizar este archivo. Reemplázalo por una copia legible.', 'error'),
    }));
    function controls() {
      $('#uploadSubmit').disabled = busy || locked;
      $('#uploadFile').disabled = busy || locked;
      $('#uploadConsent').disabled = busy || locked;
      $('#uploadRecover').disabled = busy || !documentId;
      $('#uploadNew').disabled = busy;

      $('#uploadForm').setAttribute('aria-busy', String(busy));
    }
    function message(text, state) { $('#uploadStatus').textContent = text; $('#uploadStatus').dataset.state = state; }
    function remember() { try { storage?.setItem(key, JSON.stringify({ documentId, file: metadata })); } catch (_) { /* No se persiste el contenido del archivo. */ } }
    // Agregado por Edil: el ojo apunta al original de OCI mediante la API autenticada.
    function showMetadata() {
      $('#uploadSelected').hidden = !metadata && !documentId && !locked;
      $('#uploadFileInfo').textContent = metadata ? metadata.name + ' · ' + (metadata.type || 'Archivo') + ' · ' + (metadata.size / 1024).toFixed(1) + ' KiB' : 'Documento anterior';
      $('#uploadFileInfo').title = metadata ? metadata.name : documentId || '';
      // Agregado por Edil: el formato visible procede del archivo seleccionado.
      $('#uploadFileType').textContent = metadata?.type || 'DOC';
      $('#uploadPreviewLink').hidden = true;
      $('#uploadPreviewLink').removeAttribute?.('href');
      $('#uploadFilePhase').textContent = !metadata && !locked ? 'Selecciona un archivo para ver su contenido.' : busy ? 'Enviando o consultando…' :
        phase === 'procesado' || phase === 'auditoria_humana' ? 'Subida y análisis confirmados' :
        phase === 'recibido' ? 'Subida confirmada; análisis pendiente' : locked ? 'Carga anterior: consulta su estado' : 'Archivo seleccionado; todavía sin enviar';
      if (documentId) {
        try {
          const urlFor = options.originalUrl || (id => root.MediFlowDocumentsApi.originalUrl(id));
          $('#uploadPreviewLink').href = urlFor(documentId);
          $('#uploadPreviewLink').hidden = false;
        } catch (_) { /* No ofrecer un enlace con base incorrecta. */ }
      }
    }
    async function preview(file) {
      if (busy || locked) return;
      viewer.clear(); $('#uploadLocalPanel').hidden = true; metadata = null; phase = 'selected'; showMetadata();
      if (!file) return;
      try { root.MediFlowTriageApi.validateFile(file); }
      catch (error) { message(error.message, 'error'); return; }
      const extension = file.name.split('.').pop().toLowerCase();
      const mime = { pdf: 'application/pdf', txt: 'text/plain', jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png' }[extension];
      metadata = { name: file.name, size: file.size, type: extension.toUpperCase() };
      showMetadata();
      $('#uploadLocalPanel').hidden = false;
      await viewer.show({ blob: file.slice(0, file.size, mime), mime });
    }
    function render(data) {
      documentId = data.documento_id; locked = true; phase = data.status; remember();
      showMetadata();
      const c = data.clasificacion, r = data.decision_enrutamiento;
      $('#uploadResult').hidden = false;
      $('#uploadResult').dataset.state = data.status;
      // textContent impide interpretar como HTML los datos no confiables de IA.
      $('#uploadResult').textContent = [
        'Documento: ' + documentId, 'Estado: ' + data.status,
        ...(data.status === 'recibido' ? ['Recepción confirmada; análisis pendiente.'] : [
          'Tipo: ' + c.tipo_documento, 'Prioridad orientativa: ' + c.nivel_prioridad,
          'Confianza de clasificación: ' + Math.round(c.score_confianza_clasificacion * 100) + '% (no mide seguridad clínica)',
          'Revisión humana: ' + (r.requiere_auditoria_humana ? 'Requerida' : 'No requerida por el sistema'),
          'Motivo de enrutamiento: ' + r.justificacion_enrutamiento,
        ]), 'La salida automática no sustituye la valoración profesional.',
      ].join('\n');
      message(data.status === 'recibido' ? 'Documento recibido. El análisis sigue pendiente.' :
        data.status === 'auditoria_humana' ? 'Análisis disponible; requiere revisión humana.' : 'Procesamiento completado.', data.status);
    }
    async function submit(event) {
      event?.preventDefault(); if (busy || locked) return;
      const file = $('#uploadFile').files?.[0], consent = $('#uploadConsent').checked;
      try { root.MediFlowTriageApi.validateFile(file); if (!consent) throw Error('Autoriza el envío y análisis antes de continuar.'); }
      catch (error) { message(error.message, 'error'); return; }
      metadata = { ...metadata, name: file.name, size: file.size };
      busy = true; locked = true; documentId = null; remember(); showMetadata(); controls();
      message('Enviando y analizando el documento. Espera sin repetir la carga.', 'loading');
      try { render(await client.upload(file, consent)); }
      catch (error) {
        documentId = error.documentId || null; locked = error.uncertain !== false;
        if (locked) remember(); else { try { storage?.removeItem(key); } catch (_) {} }
        message((error.name === 'TriageApiError' ? error.message : 'No se pudo confirmar el procesamiento.') +
          (documentId ? ' Documento: ' + documentId + '. Usa Consultar recepción.' : '') +
          (locked ? ' No se reenviará automáticamente; revisa el historial.' : ''), 'error');
      } finally { busy = false; showMetadata(); controls(); }
    }
    async function recover() {
      if (busy || !documentId) return;
      busy = true; controls(); message('Consultando el documento recibido…', 'loading');
      try { render(await documents.getDocument(documentId, { baseUrl: root.MEDIFLOW_API_BASE_URL })); }
      catch (_) { message('No se pudo consultar el documento. Se conserva el resultado anterior; no lo reenvíes.', 'error'); }
      finally { busy = false; showMetadata(); controls(); }
    }
    function reset() {
      if (busy) return;
      const confirm = options.confirm || (text => root.confirm(text));
      if (locked && !confirm('Antes de iniciar otra carga, comprueba el historial. Repetir un archivo puede duplicarlo. ¿Continuar?')) return;
      try { storage?.removeItem(key); } catch (_) {}
      locked = false; documentId = null; metadata = null; phase = 'selected'; viewer.clear(); $('#uploadLocalPanel').hidden = true; showMetadata();
      $('#uploadForm').reset(); $('#uploadResult').hidden = true;

      message('Selecciona un documento para comenzar.', 'idle'); controls();
    }
    $('#uploadForm').addEventListener('submit', submit);
    $('#uploadRecover').addEventListener('click', recover);
    $('#uploadNew').addEventListener('click', reset);
    $('#uploadFile').addEventListener('change', () => {
      if (!busy && !locked) preview($('#uploadFile').files?.[0]).catch(() => message('No se pudo abrir la vista previa local.', 'error'));
    });
    root.addEventListener?.('pagehide', () => viewer.clear());
    showMetadata();
    controls();
    message(locked ? 'Carga anterior encontrada. Consulta su recepción o abre el original guardado.' : 'Selecciona un documento para comenzar.', 'idle');
    return { submit, recover, reset, preview };
  }
  root.MediFlowUpload = { mount };
  if (typeof module !== 'undefined') module.exports = { mount };
  else mount(root.document);
})(typeof window !== 'undefined' ? window : globalThis);
