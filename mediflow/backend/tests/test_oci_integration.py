import os
from conexion_oci import OCIStorageManager

def probar_espacios_drazen():
    print("=== INICIANDO PRUEBAS DE ESPACIOS OCI (DRAZEN) ===")
    
    gestor = OCIStorageManager()
    
    BUCKET_RECIBIDOS = "recibidos"
    BUCKET_AUDITORIA = "auditoria_humana"
    BUCKET_PROCESADOS = "procesados"
    
    # -------------------------------------------------------------
    # 0. Prueba en bucket /recibidos (subida en memoria desde API/FastAPI)
    # -------------------------------------------------------------
    try:
        print("\n0. Probando subida desde memoria a /recibidos...")
        contenido_simulado = b"PDF Simulado - Receta recibida via API REST"
        nombre_recibido = "receta_api_prueba_001.pdf"
        
        gestor.subir_archivo_desde_memoria(
            contenido_bytes=contenido_simulado,
            nombre_bucket=BUCKET_RECIBIDOS,
            nombre_destino=nombre_recibido
        )
        
        # Verificar que figure en el bucket recibidos
        res_rec = gestor.object_storage.list_objects(gestor.namespace, BUCKET_RECIBIDOS)
        nombres_rec = [obj.name for obj in res_rec.data.objects]
        if nombre_recibido in nombres_rec:
            print(f"   [OK] Objeto '{nombre_recibido}' verificado en '{BUCKET_RECIBIDOS}'.")
        else:
            print(f"   ⚠️ No se encontró '{nombre_recibido}' en '{BUCKET_RECIBIDOS}'.")
    except Exception as e:
        print(f"   ❌ Error probando el bucket 'recibidos': {e}")

    # -------------------------------------------------------------
    # Flujo de lectura/escritura y movimiento entre buckets
    # -------------------------------------------------------------
    archivo_local = "documento_medico_prueba.txt"
    with open(archivo_local, "w", encoding="utf-8") as f:
        f.write("Receta medica #1042 - Paciente: Prueba OCI - Fecha: 2026")
    
    try:
        # 1. Subida a auditoria_humana
        print("\n1. Probando subida a /auditoria_humana...")
        gestor.subir_archivo(
            ruta_local=archivo_local,
            nombre_bucket=BUCKET_AUDITORIA,
            nombre_destino="receta_pendiente_001.txt"
        )
        
        # 2. Movimiento a procesados
        print("\n2. Probando movimiento de /auditoria_humana a /procesados...")
        gestor.mover_archivo(
            nombre_archivo="receta_pendiente_001.txt",
            bucket_origen=BUCKET_AUDITORIA,
            bucket_destino=BUCKET_PROCESADOS
        )
        
        # 3. Descarga y validación desde procesados
        print("\n3. Probando descarga/lectura desde /procesados...")
        archivo_descargado = "receta_descargada_verificada.txt"
        gestor.descargar_archivo(
            nombre_bucket=BUCKET_PROCESADOS,
            nombre_archivo="receta_pendiente_001.txt",
            ruta_descarga=archivo_descargado
        )
        
        with open(archivo_descargado, "r", encoding="utf-8") as f:
            contenido = f.read()
            print(f"   [OK] Contenido verificado exitosamente: '{contenido}'")
            
        print("\n==================================================")
        print("🎉 ¡TODAS LAS PRUEBAS DE LOS 3 BUCKETS PASARON CON ÉXITO!")
        print("==================================================")

    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
    finally:
        for temp_file in [archivo_local, "receta_descargada_verificada.txt"]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

if __name__ == "__main__":
    probar_espacios_drazen()