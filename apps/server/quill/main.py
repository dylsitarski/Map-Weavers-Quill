"""Loopback development API. No mutable or externally backed endpoints yet."""

from fastapi import FastAPI

from quill.geometry import GeometryRequest, GeometryResult, validate_geometry
from quill.providers import MockProvider, ProviderDescriptor

app = FastAPI(title="Map-Weaver's Quill", version="0.0.0")
provider = MockProvider()


@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/providers", response_model=list[ProviderDescriptor])
def providers() -> list[ProviderDescriptor]:
    return [provider.descriptor()]


@app.post("/api/geometry/validate", response_model=GeometryResult)
def geometry(request: GeometryRequest) -> GeometryResult:
    return validate_geometry(request)
