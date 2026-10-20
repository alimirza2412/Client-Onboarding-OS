import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_tenant_db, require_staff_or_above
from app.models.client import Client, Contact
from app.schemas.client import ClientCreate, ClientOut, ClientUpdate

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(
    db: Session = Depends(get_tenant_db),
    _=Depends(require_staff_or_above),
) -> list[Client]:
    return (
        db.query(Client)
        .options(joinedload(Client.contacts))
        .order_by(Client.created_at.desc())
        .all()
    )


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_tenant_db),
    membership=Depends(require_staff_or_above),
) -> Client:
    client = Client(organization_id=membership.organization_id, name=payload.name)
    db.add(client)
    db.flush()

    contact = Contact(
        organization_id=membership.organization_id,
        client_id=client.id,
        name=payload.contact.name,
        email=payload.contact.email,
        is_primary=payload.contact.is_primary,
    )
    db.add(contact)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_tenant_db),
    _=Depends(require_staff_or_above),
) -> Client:
    client = (
        db.query(Client)
        .options(joinedload(Client.contacts))
        .filter(Client.id == client_id)
        .first()
    )
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")
    return client


@router.patch("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdate,
    db: Session = Depends(get_tenant_db),
    _=Depends(require_staff_or_above),
) -> Client:
    client = db.query(Client).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")

    if payload.name is not None:
        client.name = payload.name
    if payload.status is not None:
        client.status = payload.status

    db.commit()
    db.refresh(client)
    return client
