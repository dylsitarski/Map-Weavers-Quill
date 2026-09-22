# ADR-0006: Foundry export boundary

Status: Accepted architecture; implementation in Milestone 4.

Native documents remain independent of Foundry. A versioned bundle and companion
importer will map deterministic scene entities through one tested, version-specific
adapter. The owner selects the first supported Foundry major version in Milestone 4.
No compatibility is claimed by the current coordinate tests. Imports must validate
bundle data and never evaluate scripts supplied in it.
