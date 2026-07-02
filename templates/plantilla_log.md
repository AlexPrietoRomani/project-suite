# Bitácora de Incidencias y Diagnóstico — [Nombre del Proyecto]

> **Propósito:** Registro histórico y cronológico de bugs, hipótesis de diagnóstico, resoluciones técnicas y lecciones aprendidas.
> **Ámbito:** Cualquier aplicación con arquitectura modular desacoplada (Frontend, Backend/API, Workers/Queues, Base de Datos, Caché).
> **Instrucciones:** Agrega una nueva entrada al principio del documento (orden cronológico inverso) por cada incidente, bug crítico o refactor de arquitectura resuelto.

---

## [Plantilla Vacía - Copiar para Nuevas Entradas]

## AAAA-MM-DD — [Título corto del Incidente o Feature] — [Componentes Afectados, ej: Gateway / Worker / DB]

### 1. Síntoma Observado / Reporte
*Describe el error tal como lo reportó el usuario o cómo se detectó en los sistemas de monitoreo.*
*   **Qué falló:** [Ej. El usuario ve un error 504 Gateway Timeout al intentar procesar un reporte]
*   **Entorno:** [Ej. Local / Staging / Producción]
*   **Logs / Traza de Error:**
    ```text
    [Traza de error de consola, logs del servidor o payload fallido]
    ```

### 2. Hipótesis de Diagnóstico
*¿Qué teorías se investigaron y cómo se validaron o descartaron?*
1.  **Hipótesis 1:** [Teoría...] → *Resultado:* [Descartada porque...]
2.  **Hipótesis 2:** [Teoría...] → *Resultado:* [Confirmada mediante...]

### 3. Causa Raíz
*Explicación técnica detallada de por qué ocurrió el problema en la arquitectura (ej. condiciones de carrera, desalineación de contratos de API, problemas de concurrencia en la DB, fallos de red en llamadas síncronas).*
*   [Ej. "El microservicio X asumía que la base de datos respondía en menos de 2s, pero bajo alta carga la query demoraba 5s, haciendo que el API Gateway cortara la conexión por timeout antes de recibir la respuesta."]

### 4. Resolución e Implementación
*Pasos exactos y cambios realizados en el código. Lista los archivos editados o refactorizados.*
1.  **[Servicio/Componente 1]:** [Descripción del cambio...]
2.  **[Servicio/Componente 2]:** [Descripción del cambio...]
*   **Cambios en el código (Diff de referencia):**
    ```diff
    - código_antiguo
    + código_nuevo
    ```

### 5. Verificación y Mediciones
*Pruebas ejecutadas para certificar que el bug está resuelto y no causa regresiones. Si aplica, incluye telemetría o tiempos antes/después.*
*   **Pruebas unitarias/integración:** [Ej. Ejecución de suite de test local o de integración]
*   **Tiempos de ejecución / Latencia:**
    *   **Antes:** [Ej. 5.4s por petición]
    *   **Después:** [Ej. 120ms (reducción del 97% mediante indexación/caché)]

### 6. Lecciones Aprendidas (Retroalimentación)
*¿Cómo podemos evitar que este error vuelva a ocurrir? ¿Qué patrones de diseño o guardarrailes defensivos deberíamos añadir?*
*   [Ej. "No confiar en que el cliente valide los payloads; el backend debe implementar validaciones robustas de esquema."]
*   [Ej. "Configurar políticas de reintentos (retries con exponential backoff) y disyuntores (circuit breakers) en llamadas externas."]

---

## [Ejemplo de Entrada Completada para Referencia]

## 2026-06-03 — Error de concurrencia al actualizar estado de procesamiento — Worker / Database

### 1. Síntoma Observado / Reporte
Varios usuarios reportaron que tras subir un archivo masivo para procesamiento asíncrono, la barra de progreso se quedaba colgada en "99%", a pesar de que el backend había terminado de procesar todos los registros.
*   **Qué falló:** El estado final de la tarea en la tabla `tasks` no se actualizaba a `COMPLETED`.
*   **Entorno:** Staging y Producción.
*   **Logs / Traza de Error:**
    ```text
    sqlalchemy.exc.OperationalError: (psycopg2.errors.DeadlockDetected) deadlock detected
    DETAIL:  Process 432 waits for ShareLock on transaction 10452; blocked by process 433.
    Process 433 waits for ShareLock on transaction 10451; blocked by process 432.
    ```

### 2. Hipótesis de Diagnóstico
1.  **Hipótesis 1:** El worker no enviaba la señal de finalización al Message Broker. → *Resultado:* Descartada. Los logs de RabbitMQ confirmaron la entrega del mensaje de éxito.
2.  **Hipótesis 2:** Múltiples hilos del Worker intentaban actualizar la misma fila de la tabla `tasks` de forma simultánea, causando un deadlock en la base de datos al bloquear índices cruzados. → *Resultado:* Confirmada. La transacción de actualización no estaba optimizada y bloqueaba la fila completa durante operaciones de escritura concurrentes.

### 3. Causa Raíz
Cada hilo de procesamiento reportaba el progreso individual del bloque. Cuando los últimos hilos terminaban simultáneamente, ambos intentaban hacer un `UPDATE tasks SET progress = 100, status = 'COMPLETED' WHERE id = :id` mientras mantenían bloqueos compartidos en filas hijas de auditoría relacional, generando un deadlock en el gestor de base de datos.

### 4. Resolución e Implementación
Se implementó un bloqueo optimista en base de datos (`SELECT FOR UPDATE` controlado) y se centralizó la actualización del estado de progreso a través de un agregador en memoria (Redis) que solo persiste en la base de datos principal de manera periódica (throttle) o cuando realmente el contador de elementos pendientes llega a cero.
*   **Cambios en el código (Diff de referencia):**
    ```diff
    # services/task_manager.py
    - db.session.query(Task).filter_by(id=task_id).update({"progress": new_progress})
    + # Se utiliza Redis para contar elementos de forma atómica
    + redis_client.incrby(f"task:{task_id}:progress", increment)
    ```

### 5. Verificación y Mediciones
*   **Pruebas unitarias/integración:** Se ejecutó una prueba de carga simulando 100 workers concurrentes escribiendo sobre la misma tarea. Cero deadlocks detectados.
*   **Tiempos de ejecución / Latencia:** El tiempo bloqueado en base de datos bajó de ~250ms por transacción a menos de 5ms gracias a la delegación a Redis.

### 6. Lecciones Aprendidas (Retroalimentación)
*   **Nunca realizar actualizaciones de base de datos OLTP de alta frecuencia desde múltiples hilos o procesos distribuidos concurrentes.**
*   Utilizar almacenes en memoria rápidos (como Redis) para estados transicionales de alta concurrencia, y consolidar en la base de datos SQL de manera diferida.
