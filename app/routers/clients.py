from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.dependencies import get_db, require_admin
from app.schemas import (
    ClientOut,
    ClientToggleBody,
    ClientUpdateBody,
)

router = APIRouter(tags=["clients"])


@router.get("/api/clients", response_model=list[ClientOut])
def list_clients(
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> list[ClientOut]:
    clients = crud.list_clients(db)
    current_version = crud.get_playlist_revision(db)
    result = []
    for c in clients:
        data = {
            "id": c.id,
            "client_id": c.client_id,
            "name": c.name,
            "is_active": c.is_active,
            "is_online": crud.is_client_online(c),
            "last_sync": c.last_sync,
            "synced_playlist_version": c.synced_playlist_version,
            "current_playlist_version": current_version,
            "last_status": c.last_status,
        }
        result.append(ClientOut.model_validate(data))
    return result


@router.put("/api/clients/{client_id}/toggle", response_model=ClientOut)
def toggle_client(
    client_id: int,
    body: ClientToggleBody,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> ClientOut:
    client = crud.get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    updated = crud.toggle_client_active(db, client, body.is_active)
    return ClientOut.model_validate(updated)


@router.patch("/api/clients/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    body: ClientUpdateBody,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> ClientOut:
    client = crud.get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    if body.name is not None:
        client.name = body.name
        db.add(client)
        db.commit()
        db.refresh(client)
    return ClientOut.model_validate(client)


@router.delete("/api/clients/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin),
) -> dict[str, str]:
    client = crud.get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    db.delete(client)
    db.commit()
    return {"detail": "Клиент удалён"}
