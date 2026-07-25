from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from database import get_db
from models import Account, SimpleFinConnection
from services import simplefin, transfers

router = APIRouter(prefix="/api/simplefin", tags=["simplefin"])


class ClaimRequest(BaseModel):
    setup_token: str


class LinkRequest(BaseModel):
    simplefin_account_id: str
    account_id: Optional[int] = None      # link to this existing account
    create_as: Optional[str] = None       # or create a new account of this type
    name: Optional[str] = None


@router.get("/status")
def status(db: Session = Depends(get_db)):
    """Whether a connection exists, and which local accounts are linked."""
    access_url = simplefin.resolve_access_url(db)
    connection = simplefin.get_connection(db)
    linked = db.query(Account).filter(Account.simplefin_account_id.isnot(None)).all()
    return {
        "connected": access_url is not None,
        "org_name": connection.org_name if connection else None,
        "endpoint": simplefin.redact(access_url) if access_url else None,
        "last_synced_at": connection.last_synced_at if connection else None,
        "linked_accounts": [
            {
                "account_id": a.id,
                "name": a.name,
                "account_type": a.account_type,
                "simplefin_account_id": a.simplefin_account_id,
                "last_synced_at": a.last_synced_at,
            }
            for a in linked
        ],
    }


@router.post("/claim")
def claim(payload: ClaimRequest, db: Session = Depends(get_db)):
    """Exchange a one-time setup token for an access URL and store it."""
    try:
        access_url = simplefin.claim_setup_token(payload.setup_token)
    except simplefin.SimpleFinError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Confirm the URL works and grab the org name before persisting.
    try:
        probe = simplefin.fetch_accounts(access_url, balances_only=True)
    except simplefin.SimpleFinError as exc:
        raise HTTPException(status_code=400, detail=f"Claimed URL did not work: {exc}")

    connections = probe.get("connections") or []
    org_name = connections[0].get("org_name", "") if connections else ""

    simplefin.store_access_url(db, access_url, org_name)

    return {
        "message": "Connected to SimpleFIN",
        "org_name": org_name,
        "endpoint": simplefin.redact(access_url),
        "remote_accounts": _remote_account_summaries(probe, db),
    }


@router.get("/accounts")
def remote_accounts(db: Session = Depends(get_db)):
    """List accounts visible through SimpleFIN and their local link status."""
    access_url = _require_access_url(db)
    try:
        payload = simplefin.fetch_accounts(access_url, balances_only=True)
    except simplefin.SimpleFinError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {
        "accounts": _remote_account_summaries(payload, db),
        "errors": payload.get("errlist") or [],
    }


@router.post("/link")
def link(payload: LinkRequest, db: Session = Depends(get_db)):
    """Point a local account at a remote SimpleFIN account, or create one."""
    existing = db.query(Account).filter(
        Account.simplefin_account_id == payload.simplefin_account_id
    ).first()
    if existing and existing.id != payload.account_id:
        raise HTTPException(
            status_code=400,
            detail=f"Already linked to account '{existing.name}'. Unlink it first.",
        )

    if payload.account_id is not None:
        account = db.query(Account).filter(Account.id == payload.account_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
    else:
        if not payload.create_as or not payload.name:
            raise HTTPException(
                status_code=400,
                detail="Provide account_id, or both create_as and name to create an account",
            )
        if db.query(Account).filter(Account.name == payload.name).first():
            raise HTTPException(status_code=400, detail="An account with that name already exists")
        account = Account(name=payload.name, account_type=payload.create_as)
        db.add(account)

    account.simplefin_account_id = payload.simplefin_account_id
    db.commit()
    db.refresh(account)

    return {
        "message": f"Linked '{account.name}' to {payload.simplefin_account_id}",
        "account_id": account.id,
    }


@router.delete("/link/{account_id}")
def unlink(account_id: int, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.simplefin_account_id = None
    db.commit()
    return {"message": f"Unlinked '{account.name}'"}


@router.post("/sync")
def sync(
    days: int = 30,
    pending: bool = True,
    anchor_balances: bool = True,
    db: Session = Depends(get_db),
):
    """Pull recent transactions for every linked account.

    `days` may be any length -- the request is split into 45-day windows, since
    SimpleFIN silently caps long ranges instead of erroring.
    """
    access_url = _require_access_url(db)
    try:
        result = simplefin.sync(
            db, access_url, days=days, pending=pending,
            anchor_balances=anchor_balances,
        )
    except simplefin.SimpleFinError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    from datetime import datetime
    connection = simplefin.get_connection(db)
    if not connection:
        # The access URL came from .env with no database row behind it; create
        # one so "last synced" has somewhere to live.
        connection = SimpleFinConnection(access_url=access_url)
        db.add(connection)
    connection.last_synced_at = datetime.utcnow()
    db.commit()

    return result.as_dict()


@router.post("/detect-transfers")
def detect_transfers(db: Session = Depends(get_db)):
    """Find money moved between the user's own accounts and flag both legs.

    Runs automatically after each sync; exposed separately to backfill
    transactions that were imported from CSV before this existed.
    """
    matched = transfers.detect_internal_transfers(db)
    return {
        "message": f"Flagged {len(matched)} internal transfer(s)",
        "count": len(matched),
        "transfers": matched,
    }


def _require_access_url(db: Session) -> str:
    access_url = simplefin.resolve_access_url(db)
    if not access_url:
        raise HTTPException(
            status_code=400,
            detail=(
                "No SimpleFIN connection. Run `uv run python scripts/simplefin_setup.py` "
                "or POST a setup token to /api/simplefin/claim."
            ),
        )
    return access_url


def _remote_account_summaries(payload: dict, db: Session) -> list[dict]:
    links = {
        a.simplefin_account_id: a
        for a in db.query(Account).filter(Account.simplefin_account_id.isnot(None)).all()
    }
    summaries = []
    for remote in payload.get("accounts", []):
        linked_account = links.get(remote.get("id"))
        summaries.append({
            "simplefin_account_id": remote.get("id"),
            "name": remote.get("name"),
            "balance": remote.get("balance"),
            "currency": remote.get("currency"),
            "org": (remote.get("org") or {}).get("name") if isinstance(remote.get("org"), dict) else None,
            "linked_account_id": linked_account.id if linked_account else None,
            "linked_account_name": linked_account.name if linked_account else None,
        })
    return summaries
