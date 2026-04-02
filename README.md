# CodeReview: AI-Powered Auto-Fixer

**CodeReview** es una herramienta de auditoría de código avanzada que combina múltiples linters con el poder de la Inteligencia Artificial (LLMs) para encontrar y corregir problemas de forma automática y concurrente.

## Características

-   **Motor Asíncrono**: Escanea tu código con múltiples linters en paralelo usando `asyncio`.
-   **IA en Segundo Plano**: Genera sugerencias de corrección mientras revisas los hallazgos previos.
-   **Configuración Profesional**: Comando `init` para configurar proveedores (OpenAI, Anthropic, Ollama) de forma persistente.
-   **Multi-Linter**: Soporte nativo para Ruff, Pylint, Bandit, MyPy, Pyright, Semgrep y Vulture.
-   **Auto-Fixer Inteligente**: Aplica parches sugeridos por la IA con algoritmos de *Fuzzy Matching*.

## Instalación

Requiere [uv](https://github.com/astral-sh/uv) para la gestión de dependencias:

```bash
git clone <url-del-repositorio>
cd codereview
uv sync
```

## Configuración Inicial

Antes de empezar, configura tu proveedor de IA preferido:

```bash
uv run codereview init
```

Esto creará un archivo `codereview.toml` con tus preferencias y un archivo `.env` para tus API Keys.

## Uso rápido

Una vez configurado, simplemente ejecuta:

```bash
uv run codereview scan src/
```

### Overrides (opcional)

Puedes sobrescribir la configuración guardada usando flags:

```bash
uv run codereview scan . --provider openai --model gpt-4o
```

## Linters Soportados

| Linter | Especialidad |
| :--- | :--- |
| **Ruff** | Estilo y errores comunes |
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
