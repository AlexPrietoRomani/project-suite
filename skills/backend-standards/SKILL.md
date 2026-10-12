---
name: backend-standards
description: Estándares de arquitectura por capas (Clean/Layered), APIs robustas, validación de esquemas tipados, manejo de errores de dominio, transaccionalidad y seguridad en Backend. CARGA cuando diseñes, implementes o audites APIs, controladores, servicios y acceso a datos.
when_to_use: Al construir o refactorizar endpoints, rutas, servicios de negocio, modelos de base de datos, middlewares o tests de integración y backend.
allowed-tools: Read Grep Glob Write Edit
---

# Estándares de Arquitectura e Ingeniería Backend

Como agente de IA, DEBES cumplir estrictamente estas normativas al implementar servicios backend, APIs y lógica de servidor. El objetivo es garantizar sistemas desacoplados, deterministas, seguros y con contratos de entrada y salida rigurosamente tipados.

## Flujo de Trabajo
1. **Modelado y Contrato:** Define el esquema y los contratos de entrada/salida (OpenAPI/Swagger o esquemas tipados como Pydantic, Zod o Marshmallow) antes de codificar la lógica interna.
2. **Estructura en Capas:** Respeta la dirección de dependencias: Transport/Controller ➔ Service/Use Case ➔ Repository/Data Access.
3. **Validación en el Borde:** Valida y sanitiza las entradas HTTP antes de invocar la capa de servicio.
4. **Manejo Centralizado de Errores:** Convierte excepciones en códigos de error HTTP coherentes sin filtrar detalles internos o trazas de ejecución.
5. **Transaccionalidad y Pruebas:** Asegura transacciones atómicas de base de datos y ejecuta pruebas unitarias y de integración antes de certificar la tarea.

---

## 1. Arquitectura por Capas (Clean / Layered Architecture)

- **Capa de Transporte (*Controller / Router / Handler*):**
  - Responsabilidad única: Recibir solicitudes HTTP/RPC, validar esquemas de entrada, delegar a la capa de servicio y devolver la respuesta con el código de estado adecuado (`200`, `201`, `204`, etc.).
  - Prohibido incluir lógica de negocio compleja o consultas SQL directas en los controladores.
- **Capa de Servicio (*Service / Use Case*):**
  - Contiene la lógica de negocio pura, reglas de validación de dominio y orquestación de flujos.
  - Es agnóstica al protocolo HTTP; puede ejecutarse desde una API REST, un job en cola o un comando CLI sin cambios.
- **Capa de Acceso a Datos (*Repository / Data Access Layer*):**
  - Encapsula la comunicación con bases de datos (SQL/NoSQL) y sistemas de almacenamiento externo.
  - Provee métodos semánticos (`findById`, `save`, `findActiveUsers`) y aísla al resto del sistema de detalles del ORM o dialecto SQL.

---

## 2. Diseño de APIs y Contratos de Comunicación

- **REST Semántico:** 
  - `GET` (idempotente y seguro, solo lectura).
  - `POST` (creación de recursos o mutaciones no idempotentes, devuelve `201 Created` o `202 Accepted`).
  - `PUT` (reemplazo completo e idempotente).
  - `PATCH` (actualización parcial de campos).
  - `DELETE` (eliminación de recurso, devuelve `204 No Content` o `200 OK`).
- **Paginación y Filtrado Estándar:** Toda consulta de colecciones debe soportar paginación (basada en cursores o `limit`/`offset`) y límites máximos por defecto para prevenir denegación de servicio o sobrecarga de memoria.
- **Idempotencia:** En endpoints críticos de mutación (ej. cobros, transferencias, procesamiento de pedidos), acepta y valida cabeceras `Idempotency-Key`.

---

## 3. Validación Estricta de Entradas (Edge Validation)

- **Tipado Fuerte y Esquemas:** Toda entrada (query params, path params, headers y JSON body) DEBE validarse mediante esquemas declarativos (Pydantic en Python, Zod/Joi en Node/TS, Serde en Rust).
- **Fallo Temprano (*Fail-Fast*):** Si los datos recibidos no cumplen con el esquema requerido, responde inmediatamente con `400 Bad Request` o `422 Unprocessable Entity`, detallando los campos inválidos sin ejecutar llamadas adicionales a la base de datos.
- **Sanitización:** Limpia y normaliza cadenas de texto para evitar ataques de inyección (SQL, NoSQL, comandos OS, Cross-Site Scripting).

---

## 4. Manejo de Errores y Excepciones de Dominio

- **Excepciones de Dominio Tipadas:** Define clases de error semánticas (ej. `NotFoundError`, `ConflictError`, `UnauthorizedError`, `ValidationError`).
- **Middleware / Filtro Global de Excepciones:** Un interceptor centralizado captura los errores de dominio y los transforma a la respuesta JSON estándar del proyecto:
  ```json
  {
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "El recurso solicitado no existe o fue dado de baja.",
      "details": []
    }
  }
  ```
- **Seguridad en Respuestas:** NUNCA envíes *stack traces*, consultas SQL crudas o rutas del sistema operativo en respuestas al cliente.

---

## 5. Transacciones y Resiliencia en Base de Datos

- **Atomicidad Transaccional:** Cuando una operación de negocio involucre múltiples escrituras o dependencias cruzadas, ejecuta el bloque dentro de una transacción atómica explícita con rollback automático ante fallo.
- **Prevención de Problemas N+1:** Utiliza carga impaciente (*eager loading* / `JOIN`) o batching para relaciones en ORMs.
- **Pool de Conexiones:** Ajusta límites de conexiones concurrentes y timeouts de consulta para evitar agotar recursos del motor de base de datos.

---

## 6. Seguridad y Observabilidad

- **Autenticación y Autorización:** Valida tokens (JWT/PASETO/Session) y permisos granulares (RBAC/ABAC) en capas tempranas de middleware.
- **Secretos Fuera del Código:** Cero credenciales o claves API en el código fuente. Usa variables de entorno validadas al arranque (`.env` con validación estricta).
- **Logging Estructurado:** Genera logs en formato JSON que incluyan timestamp ISO, nivel de severidad, identificador de traza (`correlation_id` / `request_id`) y mensaje explicativo.

---

## 7. Referencias Canónicas y Herramientas del Ecosistema

- **obra/superpowers (Depuración Sistemática y TDD):**
  - Aplica depuración metódica basada en evidencia: 1) Reproducir el problema con un test automatizado determinista (rojo), 2) Aislar la causa raíz con trazas y pruebas de hipótesis, 3) Aplicar el cambio mínimo necesario, 4) Confirmar que el test pasa a verde sin regresiones.
- **anthropics/courses (Evaluación Estructurada y Contratos Deterministas):**
  - Define contratos de entrada/salida y evaluación formal de comportamiento sin ambigüedad en servicios y flujos asíncronos.
- **modelcontextprotocol/servers (Introspección de Base de Datos y Core Tools):**
  - Para inspección directa de esquemas, consultas exploratorias y verificación de migraciones, aprovecha los servidores MCP oficiales (PostgreSQL, SQLite, Filesystem) para evitar desincronización entre la base de datos y el código.
- **prisma / ORM Introspection (Modelado y Cero Drift):**
  - Utiliza herramientas de introspección y generación de tipos para sincronizar el diseño de datos (`diseno_db.md`) con las entidades reales de la base de datos de forma reproducible.
