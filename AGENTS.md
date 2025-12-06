# Project Structure

This monorepo keeps product surfaces, shared libraries, and infrastructure concerns in dedicated workspaces. Use this guide to understand where to place new code and how the pieces fit together.
If there as a ./docs/ARCHITECTURE.md file, refer to it for deeper architectural insights.
## Basic Layout

### Full-stack Application
- `apps/` – End-user applications.
  - `mobile/` – Flutter client placeholder; bootstrap the app with `flutter create` and keep platform-specific configuration here.
  - `web/` – frontend stuff...
- `docs/` – Planning and reference material for the project.
  - `tasks/` – Task-focused notes and checklists (e.g., `init.md` for onboarding steps).
- `infra/` – Developer and deployment infrastructure.
  - `docker/` – Dockerfiles and Compose configurations.
    - `docker-compose.yml` – Local development environment definition.
  - `environments/` – Environment variable templates such as `dev.env.example`, consumed by Docker Compose and deployment pipelines.
- `services/` – Backend and worker codebases exposed via APIs or background jobs.
  - `backend/` – FastAPI service packaged for Docker.
    - `src/` – Service source code.
      - `app_name/` – Application module with the FastAPI app and entrypoints.
    - `tests/` – Pytest suite (currently `test_health.py`) covering service behavior.

### Backend only Application
Modern backend that follows a strict ports-and-adapters layout. The
project separates domain logic from infrastructure so adapters (database, HTTP,
etc.) remain swappable.

## Layout

```
src/package-name/
├── core/          # Config, logging, uuid helpers
├── domain/        # Pydantic models, ports, and async services
├── adapters/db/   # SQLAlchemy ORM models and repositories
└── entrypoints/   # FastAPI wiring
tests/             # Mirrors the src structure
docs/              # Architecture and design docs
infra/             # Docker and deployment configs
...
```


# Code guidelines

1. Write Valid Code: Your code must be syntactically valid and compile without errors.
2. Fix Root Causes: Never use hacks to hide errors.
   1. Forbidden: Using try/catch to silence errors, using setTimeout to fix timing issues, commenting out broken code, or returning null just to satisfy the type checker.
3. No Incomplete Code: All submitted code must be production-ready.
    Forbidden: Do not submit code with TODO, FIXME, or other placeholder comments or mock implementations.
4. TypeScript: 100% Type-Safety
   1. Zero any: The any type is strictly forbidden. Use specific interfaces, unknown, or generics.
   2. No Type Assertions: Do not use as Type or value as unknown as Type. If TypeScript is complaining, your types are wrong. Fix the types.
   3. Trust Type Inference: Do not add explicit types when TypeScript can infer them.
        Wrong: array.map((item: MyType, index: number) => ...)
        Right: array.map((item, index) => ...)
   4. Remove Unused Parameters: If a function parameter is not used, remove it from the signature.

# Language specific guidelines
## Python
- **Consistency:** Strictly adhere to the existing project's coding style, naming conventions, and architectural patterns.
- **Dependency Management:** Check whether a dependency already exists before changing anything. Use `uv add <package>` to add/upgrade and `uv remove <package>` to drop unused deps; **never** edit `pyproject.toml` manually or use `pip`.
- **Environment:** Always activate the virtual environment (`source .venv/bin/activate`) before running commands.
- **Reusability:** Search the codebase first. Do not reinvent existing methods, classes, or logic.
- **Modularity:** Favor composable modules. Define Python Protocols/ABCs for providers to ensure loosely coupled integrations.
- **Async First:** Default to `async/await` for all I/O (LLM, storage, media) to minimize latency.
- **Robustness:** Wrap external calls with timeouts, retries (with jitter), and structured logging.
- **Purity:** Prioritize deterministic pure domain functions. Isolate side effects.
- **Code Integrity:** Fix root causes, never use hacks. **Never** use `cast` to silence type checkers; fix the underlying issue.
- Never use `# type: ignore` or `# noqa` comments; resolve the issues instead. If absolutely necessary, request user approval first.
- **Data Access:** Stick to SQLAlchemy latest ORM constructs, eagerly load required relationships (e.g., `selectinload`), and keep DB interactions within async context-managed sessions including pagination/transactions when applicable.
- **Dependency Injection:** Prefer FastAPI `Depends`/`Annotated` wiring for runtime adapters and design explicit provider overrides for testing/mocking scenarios.
- **Validation:** Post-implementation, strictly run `make lint`, `make type`, and `make test`.
- **Standards:** Enforce strict `mypy` and `ruff` rules.
- **Testing:** Write `pytest-asyncio` unit tests for new features, utilizing mocks for providers.

## TypeScript
- **Consistency:** Strictly adhere to the existing project's coding style, naming conventions, and architectural
- patterns.
- **Dependency Management:** Use `pnpm` to manage dependencies. Always run `pnpm install` after pulling new changes.
- **Environment:** Ensure Node.js version matches the project's `.nvmrc` file. Use `nvm use` to switch versions if necessary.
- **Reusability:** Search the codebase first. Do not reinvent existing methods, classes, or logic.
- **Modularity:** Favor composable modules. Define TypeScript interfaces for providers to ensure loosely coupled integrations.
- **Async First:** Default to `async/await` for all I/O (LLM, storage, media) to minimize latency.
- **Robustness:** Wrap external calls with timeouts, retries (with jitter), and structured logging.
- **Purity:** Prioritize deterministic pure domain functions. Isolate side effects.
- **Code Integrity:** Fix root causes, never use hacks. **Never** use type assertions (e.g., `as Type`) to silence type checkers; fix the underlying issue.
- Never use `// @ts-ignore` comments; resolve the issues instead. If absolutely necessary, request user approval first.
- **Validation:** Post-implementation, strictly run `pnpm lint`, `pnpm type`, and `pnpm test`.
- **Standards:** Enforce strict ESLint and TypeScript rules.
- **Testing:** Write `jest` unit tests for new features, utilizing mocks for providers.
