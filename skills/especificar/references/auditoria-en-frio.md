# Auditoría en Frío (Zero-Context Review con Ejecutores)

> Protocolo de referencia para `especificar`, `planificar`, `/nueva-fase` y `/review`. Lo ejecutan **Ejecutores de Nivel 3** (`haiku`, `luna`, `flash_lite`) lanzados por el **Orquestador** sin ningún contexto de la conversación previa (ver `skills/construir/references/orquestacion-3-niveles.md`).

## 1. Principio

Quien diseña o implementa acumula contexto implícito y sufre del **sesgo de autor**: relee sus frases con la intención que tenía, no con lo que están escritas. Antes de aprobar una especificación (`especificar`), un plan (`planificar` / `/nueva-fase`) o un diff de código (`/review`), el **Orquestador** lanza de 1 a 3 subagentes **Ejecutores** (Nivel 3) **en frío —cero contexto de la conversación previa—**, pasándoles únicamente los documentos o el `git diff` a evaluar.

Coste: una fracción del presupuesto de tokens del Orquestador. Beneficio: detección inmediata de ambigüedades, huecos de especificación y sobre-ingeniería.

## 2. Las 3 Lentes de Auditoría en Frío

Despachar una lente por Ejecutor (prompts listos para copiar en la invocación del subagente):

### Lente 1 — `zoom-out` (Simplicidad y YAGNI)

> Prompt para el Ejecutor: *"Lee este documento/plan sin contexto previo. Identifica sobre-ingeniería, capas innecesarias o abstracciones prematuras. ¿Cómo se lograría el mismo objetivo con la mitad de piezas?"*

### Lente 2 — `comprehension` (Lectura Literal en Frío)

> Prompt para el Ejecutor: *"Explica con tus propias palabras qué construye este documento/plan, cómo fluye el dato y qué asume cada componente. Señala cualquier frase donde tuviste que adivinar la intención."*

**Regla:** si el Ejecutor interpreta algo distinto a lo que el Orquestador quiso decir, el documento es **ambiguo** y debe aclararse antes de codear.

### Lente 3 — `design-critic` (Fallas, Bordes e Invariantes)

> Prompt para el Ejecutor: *"Busca condiciones de carrera, fallos silenciosos, invariantes de datos rotos, rutas o contratos incompatibles y casos borde no cubiertos por los tests declarados."*

## 3. Matriz de Triage del Orquestador

El Orquestador recibe los hallazgos de los Ejecutores y clasifica cada punto en una de tres decisiones:

| Decisión | Cuándo aplica | Acción |
|---|---|---|
| **`fix-now`** (Corregir ahora) | Ambigüedad real, contradicción arquitectónica o hueco de seguridad/datos bloqueante. | Se corrige en el documento/código **antes de avanzar**. |
| **`fix-in-fase`** (Diferir al plan) | Mejora válida que pertenece a una Sub fase o Tarea posterior del plan. | Se anota como Tarea/AC en la Fase correspondiente. |
| **`descartar`** (Falso positivo) | Duda causada solo porque el Ejecutor no leyó un módulo fuera de su alcance pero ya cubierto en otra parte, verificado por el Orquestador. | Se registra y no se actúa. |
