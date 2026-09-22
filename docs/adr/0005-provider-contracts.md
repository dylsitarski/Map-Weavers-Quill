# ADR-0005: Initial offline image provider contract

Status: Accepted for Milestone 0.

Image providers declare capabilities. Initial typed requests, results and errors
live in Python and generate JSON Schema and TypeScript declarations. The mock
supports generation, grayscale-mask inpainting, and seeds at up to 512x512.
Mask white edits; black preserves; intermediate values blend. Source references
resolve only against an in-memory asset dictionary. No filesystem or URLs are
read. Output is deterministic RGB PNG addressed by SHA-256.

The unreleased 0.1.0 contract now names all initial image capabilities and exposes
optional reference images, negative prompts, neutral steps/guidance parameters,
and dotted-namespace JSON extensions. These contain non-secret request options;
credentials belong to separate server configuration. Generic dimensions allow up
to 16384 pixels per axis; each adapter must enforce its own advertised limits
before allocating images. The mock stays limited to 512x512 and rejects every
unsupported option explicitly. It ignores semantic context, which is advisory
prompt context rather than a guarantee of image quality.

Requests, results and descriptors carry contractVersion. Typed failures cover
invalid input/output, authentication, rate limiting, timeouts and cancellation.
The cancel method returns an unsupported-capability failure for the mock. There is
no queue or asynchronous capability advertised. Job lifecycle implementation is
Milestone 2 and the separate language operation contract is Milestone 7.

Repeated identical mock requests produce identical results without a job store.
Request IDs are diagnostic correlation, not a persistent idempotency guarantee;
orchestrator deduplication belongs to Milestone 2.

Cross-runtime tests exposed JSON Schema's permissive fallback for pattern-keyed
dictionaries. Namespaced dictionaries explicitly forbid additional properties so
Ajv enforces the same namespace restriction as Python, including scene metadata.
