from fastapi import Query

async def pagination_params(
    skip: int = Query(0, ge=0, description="Сколько пропустить"),
    limit: int = Query(10, ge=1, le=100, description="Сколько вернуть")
) -> dict:
    return {"skip": skip, "limit": limit}