# ADR-0024: Server-only image provider configuration

Status: Accepted; Milestone 3 foundation implemented. Hosted-first sequencing is
superseded by ADR-0025: local ComfyUI/SDXL comes first.

## Decision

All image generation and provider discovery use one server-side factory. Each operation
gets its own adapter and temporary asset dictionary, preventing accidental cross-job
asset sharing. The internal ImageProvider protocol includes put(bytes) and its asset
store, which the existing background and masked-room pipelines already require.
Generation records take providerId from the adapter result. Public JSON contracts,
project schema and existing mock output are unchanged.

Configuration is loaded once per API process before starting its durable queue. Restart
the API to apply configuration changes. MWQ_IMAGE_PROVIDER defaults to mock; unknown or
unimplemented values fail startup with a fixed message rather than silently falling back.
Only mock is implemented in this increment. There are no remote calls or new dependencies.

Credentials may be supplied through MWQ_IMAGE_API_KEY or MWQ_IMAGE_API_KEY_FILE, never
both. File input is bounded to 8192 bytes, decoded as UTF-8, and stripped of surrounding
whitespace. Empty, oversized and control-character-containing values fail validation.
The in-memory secret uses SecretStr and is excluded from the configuration repr. Errors
do not echo input values, filenames or underlying OS exceptions. Credentials are unused
by mock; no key is needed for ordinary development or tests. This prepares the credential
boundary without claiming that a hosted provider can already be configured.

Configuration is not a Pydantic project/API contract and has no public serialization
endpoint. Provider discovery returns only the existing descriptor allowlist. Job payloads
continue to contain authoring requests, not server configuration. Never copy credentials
into prompts, parameters, extensions, provenance or job errors. Future adapters must map
remote failures to safe messages without logging raw headers, responses or credentials.
Secrets cannot be protected from someone with access to the server process itself.

The development launcher passes MWQ_IMAGE_* variables only to the API child; it strips
them from the npm/Vite child. No VITE_* secret variables, browser credential settings or
automatic dotenv loading are introduced. A key file should live outside the repository
and data directory, with owner-only permissions on Linux (Windows ACLs later). Environment
and secret-file settings are operator inputs, not project-controlled paths.

## Verification and next work

Offline tests cover default selection, isolated asset stores, env/file loading and
redaction, malformed/oversized inputs, startup failure before queue initialization,
configuration snapshot behavior, discovery allowlisting and frontend-child isolation.
Existing generation, persistence and job tests continue to exercise the factory path.

Original next step (deferred by ADR-0025): choose one hosted image-edit provider, document its model/capabilities, dimension
and mask conversions, timeout/retry behavior, data handling and cost expectations; then
implement it behind this factory with mocked HTTP contract tests. Do not enable billing
or send user maps as part of automated verification. Layout conditioning and explicit
building/open-air intent remain planned under ADR-0023, not implemented by this change.
