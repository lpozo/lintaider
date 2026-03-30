# CodeReview: AI-Powered Auto-Fixer

**CodeReview** es una herramienta de auditoría de código avanzada que combina múltiples linters con el poder de la Inteligencia Artificial (LLMs) para encontrar y corregir problemas de forma automática y concurrente.

## Características

-   **Motor Asíncrono**: Escanea tu código con múltiples linters en paralelo usando `asyncio`.
-   **IA en Segundo Plano**: Genera sugerencias de corrección mientras revisas los hallazgos previos.
-   **Multi-Linter**: Soporte nativo para Ruff, Pylint, Bandit, MyPy, Pyright, Semgrep y Vulture.
-   **Auto-Fixer Inteligente**: Aplica parches sugeridos por la IA con algoritmos de *Fuzzy Matching* que respetan el contexto de tu código.
-   **Universal**: Compatible con Ollama (`local`) y cualquier proveedor soportado por LiteLLM (`cloud`, como OpenAI o Anthropic).

## Instalación

Requiere [uv](https://github.com/astral-sh/uv) para la gestión de dependencias:

```bash
git clone <url-del-repositorio>
cd codereview
uv sync
```

## Uso rápido

Escanea tu código usando el modo local (modelo por defecto `llama3` vía Ollama):

```bash
uv run codereview scan src/
```

Especificar proveedor y modelo (ej. Cloud via OpenAI):

```bash
uv run codereview scan . --provider cloud --model gpt-4o
```

### Opciones de filtrado

```bash
# Ejecutar solo un linter específico
uv run codereview scan src/ --only ruff

# Saltar ciertos linters
uv run codereview scan src/ --skip bandit,semgrep
```

## Linters Soportados

| Linter | Especialidad |
| :--- | :--- |
| **Ruff** | Estilo y errores comunes (Ultra-rápido) |
| **Pylint** | Análisis estático profundo |
| **Bandit** | Vulnerabilidades de seguridad |
| **MyPy** | Chequeo de tipos estático |
| **Pyright** | Chequeo de tipos ultra-rápido |
| **Semgrep** | Patrones de código y seguridad |
| **Vulture** | Código muerto y funciones sin uso |

## Testing

```bash
uv run pytest
```

---
*Desarrollado con arquitectura asíncrona avanzada para una experiencia instantánea.*
