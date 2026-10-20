from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """Basic liveness check. Does not touch the database."""
    return {"status": "ok"}
