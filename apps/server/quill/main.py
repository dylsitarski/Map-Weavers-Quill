"""Loopback development API. No mutable or externally backed endpoints yet."""

from fastapi import FastAPI, HTTPException

from quill.geometry import GeometryRequest, GeometryResult, validate_geometry
from quill.providers import MockProvider, ProviderDescriptor
from quill.walls import WallDerivationRequest, WallDerivationResult, derive_walls

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


@app.post("/api/geometry/walls", response_model=WallDerivationResult)
def walls(request: WallDerivationRequest) -> WallDerivationResult:
    try:
        return derive_walls(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
