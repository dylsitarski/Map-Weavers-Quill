# ADR-0005: Initial offline image provider contract

Status: Accepted for Milestone 0.

Image providers declare capabilities. Initial typed requests, results and errors
live in Python and generate JSON Schema and TypeScript declarations. The mock
supports generation, grayscale-mask inpainting, and seeds at up to 512x512.
Mask white edits; black preserves; intermediate values blend. Source references
resolve only against an in-memory asset dictionary. No filesystem or URLs are
read. Output is deterministic RGB PNG addressed by SHA-256.

There is no job queue or advertised cancellation support yet. Language providers,
reference images, context conditioning, extension parameters and asynchronous
jobs remain subsequent contract extensions. The mock ignores semantic context;
it exists to validate dimensions, mask behavior and failure handling, not quality.
