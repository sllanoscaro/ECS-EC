# Restauración003 local

2026-11-03. Ejecutado `test_restore.py -m restore` contra PostgreSQL18.3 desechable,
con PAS600_RESTORE_CONTAINER explícito y TEST_DATABASE_URL separada terminada `_test`.
Se reutilizaron `deploy/backup.sh` y `deploy/restore.sh` de009 sin modificar sus contratos.

El ensayo crea un destino vacío único terminado `_restore`, restaura el dump completo y
copia el volumen nativo a otra ruta. Compara IDs, estados y plazos de sesiones/archivos/
evaluaciones/lecturas/candidatos. Conserva sesión abortada y evaluación sellada pendiente;
no las completa por heurística ni modifica sus cuotas/retención.

El CLI export-results sobre el destino restaurado devuelve el resultado002 original y
4kWh de consumo. Al retirar deliberadamente una copia de archivo sellado, el CLI falla
con5 y conserva exactamente la exportación válida anterior. El destino restaurado se
elimina al terminar; no se modifica una aplicación o respaldo real.

En operación detener app antes de respaldar/restaurar metadatos y volumen003 como un
conjunto. Incluir abortados/pendientes, no solo publicaciones evaluadas. Mantener host key,
auth y claves privadas fuera del respaldo de informes, bajo la política externa apropiada.
Ver [procedimiento de despliegue](../../../deploy/README.md). No hay purga automática;
dependencias históricas tienen FK RESTRICT y plazos mínimos por aniversario009.
