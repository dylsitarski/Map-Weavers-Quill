# ADR-0008: Foundation verification and contract completion

Status: Accepted for Milestone 0.

Standardize on Node 24 and Python 3.12. Declare the Node major in .nvmrc,
package engines and CI; reject unsupported engines during npm install. Use
Biome for handwritten frontend formatting/linting and Playwright Chromium for
the shell's real-browser connection and failure paths. Browser tests start the
same development launcher used by developers and run against loopback only.

Complete structural project entities before building editor operations. Since
0.1.0 was an explicitly unreleased subset with no persisted user documents,
add required fields and update all synthetic fixtures together. Keep revision
provenance for entities; namespace extension metadata by dotted names. Full
polygon topology and foreign-key validation belong to Milestone 1, before save.

The mock remains a deliberately limited provider. Unsupported capabilities are
reported as unavailable rather than inferred from optional request fields.
