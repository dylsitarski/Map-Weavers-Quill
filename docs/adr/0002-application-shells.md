# ADR-0002: Application shells and contract tooling

Status: Accepted, Milestone 0.

Use React/TypeScript with Vite for the application shell and FastAPI for the
local server, retaining Konva for Milestone 1. npm pins dependencies and commits
its lockfile. Python dependencies use a pinned closure in requirements.lock.
Pydantic generates JSON Schema; json-schema-to-typescript generates declarations.
Ajv 2020 validates the same schemas in TypeScript without coercion or defaults.
Contract tests round-trip JSON through both runtimes.

The initial server exposes health and provider discovery only. No persistent
projects or external AI calls are exposed. Development binds to loopback and
Vite proxies API calls. CI must run the same make check command as developers.
