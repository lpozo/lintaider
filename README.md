# CodeReview: AI-Powered Auto-Fixer

**CodeReview** es una herramienta de auditoría de código avanzada que combina múltiples linters con el poder de la Inteligencia Artificial (LLMs) para encontrar y corregir problemas de forma automática y concurrente.

## Características

-   **Motor Asíncrono**: Escanea tu código con múltiples linters en paralelo usando `asyncio`.
-   **IA en Segundo Plano**: Genera sugerencias de corrección mientras revisas los hallazgos previos.
-   **Configuración Profesional**: Comando `init` para configurar proveedores (OpenAI, Anthropic, Ollama, Gemini) de forma persistente.
-   **Multi-Linter**: Soporte nativo para Ruff, Pylint, Bandit, MyPy, Pyright, Semgrep, Vulture, Radon y Safety.
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

### 1. Escanear el código
Detecta problemas en archivos o directorios:

```bash
uv run codereview scan src/ -v
```

### 2. Aplicar correcciones
Inicia el flujo interactivo. Si no has corrido `scan` antes, puedes pasar el target directamente:

```bash
# Escanea y luego inicia la corrección en un solo paso
uv run codereview fix src/
```

Si ya tienes un archivo `scan-result.json`, simplemente ejecuta:

```bash
uv run codereview fix
```

### Opciones de filtrado
Puedes ejecutar linters específicos o excluir algunos:

```bash
# Solo ejecutar Ruff y MyPy
uv run codereview scan . --only ruff,mypy

# Omitir Safety (escaneo de dependencias)
uv run codereview scan . --skip safety
```

## Linters Soportados

| Linter | Especialidad |
| :--- | :--- |
| **Ruff** | Estilo y errores comunes (Súper rápido) |
| **Pylint** | Análisis estático profundo y mantenibilidad |
| **Bandit** | Vulnerabilidades de seguridad en el código |
| **MyPy** | Chequeo de tipos estático oficial |
| **Pyright** | Chequeo de tipos ultra-rápido de Microsoft |
| **Semgrep** | Análisis semántico y seguridad avanzada |
| **Vulture** | Detección de código muerto y funciones sin uso |
| **Radon** | Métrica de Complejidad Ciclomática (Mantenibilidad) |
| **Safety** | Escaneo de vulnerabilidades en dependencias instaladas |

## Testing

```bash
uv run pytest
```

---
*Desarrollado con arquitectura asíncrona avanzada para una experiencia instantánea.*
