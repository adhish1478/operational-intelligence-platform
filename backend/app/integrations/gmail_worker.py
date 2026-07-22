import asyncio
import logging
import time
from datetime import datetime, timezone
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decrypt_credentials, encrypt_credentials
from app.db.session import AsyncSessionLocal
from app.db.mongo import get_mongo_db
from app.integrations.models import Integration
from app.ingest.services import IngestService

logger = logging.getLogger("gmail_worker")


async def refresh_google_token(integration: Integration, creds: dict, db: AsyncSession) -> str:
    """
    Exchanges the refresh_token for a fresh Google access_token.
    Saves the updated credential payload back to PostgreSQL.
    """
    refresh_token = creds.get("refresh_token")
    if not refresh_token:
        raise ValueError("Missing refresh_token, cannot refresh access_token")

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

    if response.status_code != 200:
        raise Exception(f"Failed to refresh Google token: {response.text}")

    data = response.json()
    new_access_token = data.get("access_token")
    if not new_access_token:
        raise Exception("Google refresh token response did not contain access_token")

    # Update credentials dict
    creds["access_token"] = new_access_token
    # If Google sends a new refresh_token, save it as well
    if data.get("refresh_token"):
        creds["refresh_token"] = data["refresh_token"]

    integration.credentials_encrypted = encrypt_credentials(creds)
    db.add(integration)
    await db.commit()
    logger.info(f"Successfully refreshed Google OAuth token for integration {integration.id}")
    return new_access_token


async def fetch_gmail_messages(access_token: str, query: str) -> list[dict]:
    """
    Calls Google's Gmail API list endpoint to fetch messages matching the query.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"q": query, "maxResults": 10},
        )

    if response.status_code == 401:
        # Trigger retry flow in the caller by throwing 401 error
        raise httpx.HTTPStatusError(
            "Unauthorized",
            request=response.request,
            response=response,
        )

    if response.status_code != 200:
        logger.error(f"Gmail list API failed with code {response.status_code}: {response.text}")
        return []

    data = response.json()
    return data.get("messages", [])


async def fetch_gmail_message_details(access_token: str, message_id: str) -> dict | None:
    """
    Fetches full email headers, subject, and snippet for a specific message ID.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if response.status_code != 200:
        logger.error(f"Failed to fetch Gmail message detail for {message_id}: {response.text}")
        return None

    return response.json()


async def sync_gmail_integration(integration: Integration, db: AsyncSession) -> None:
    """
    Synchronizes a single Gmail integration workspace.
    Refreshes tokens if needed, fetches emails matching query, and ingests them.
    """
    # 1. Decrypt credentials
    try:
        creds = decrypt_credentials(integration.credentials_encrypted)
        access_token = creds.get("access_token")
    except Exception as e:
        logger.error(f"Failed to decrypt credentials for integration {integration.id}: {e}")
        return

    if not access_token:
        logger.error(f"Missing access_token for Gmail integration {integration.id}")
        return

    # 2. Build search query
    user_query = integration.config.get("query", "")
    last_checked_time = integration.config.get("last_checked_time")

    current_time = int(time.time())

    if last_checked_time:
        q = f"{user_query} after:{last_checked_time}"
    else:
        # First sync: default to checking only the past 1 hour of emails to prevent flooding
        one_hour_ago = current_time - 3600
        q = f"{user_query} after:{one_hour_ago}"

    logger.debug(f"Gmail query for integration {integration.id}: '{q}'")

    # 3. Fetch messages list (supporting OAuth 2.0 automatic token refresh)
    try:
        messages = await fetch_gmail_messages(access_token, q)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            try:
                # Refresh token and retry
                access_token = await refresh_google_token(integration, creds, db)
                messages = await fetch_gmail_messages(access_token, q)
            except Exception as ref_err:
                logger.error(f"Gmail token refresh retry failed for {integration.id}: {ref_err}")
                return
        else:
            logger.error(f"Gmail sync HTTP error for {integration.id}: {e}")
            return
    except Exception as e:
        logger.error(f"Gmail sync unexpected error for {integration.id}: {e}")
        return

    # 4. Ingest new emails
    mongo_db = get_mongo_db()

    for msg in messages:
        msg_id = msg.get("id")
        if not msg_id:
            continue

        details = await fetch_gmail_message_details(access_token, msg_id)
        if not details:
            continue

        # Extract headers (subject, from)
        headers = details.get("payload", {}).get("headers", [])
        subject = "No Subject"
        sender = "Unknown Sender"

        for h in headers:
            name = h.get("name", "").lower()
            if name == "subject":
                subject = h.get("value", "No Subject")
            elif name == "from":
                sender = h.get("value", "Unknown Sender")

        snippet = details.get("snippet", "")

        # Format payload to match IngestService expectations
        payload = {
            "email": {
                "id": msg_id,
                "subject": subject,
                "from": sender,
                "snippet": snippet,
            }
        }

        # Correlate and process the email
        try:
            res = await IngestService.correlate_and_process(db, mongo_db, integration, payload)
            logger.info(f"Gmail message {msg_id} processed: {res}")
        except Exception as ingest_err:
            logger.error(f"Failed to ingest Gmail message {msg_id}: {ingest_err}")

    # 5. Update last checked time
    new_config = dict(integration.config or {})
    new_config["last_checked_time"] = current_time
    integration.config = new_config
    db.add(integration)
    await db.commit()


async def start_gmail_polling_worker() -> None:
    """
    Polling worker loop. Runs continuously in the background.
    """
    logger.info("Starting background Gmail Sync Worker loop...")
    # Wait a few seconds for the app to initialize before starting first loop
    await asyncio.sleep(5.0)

    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Fetch all active Gmail integrations
                statement = select(Integration).where(
                    Integration.platform == "gmail",
                    Integration.status == "active"
                )
                res = await db.execute(statement)
                integrations = res.scalars().all()

                for integration in integrations:
                    try:
                        await sync_gmail_integration(integration, db)
                    except Exception as single_err:
                        logger.error(f"Error syncing Gmail integration {integration.id}: {single_err}")

        except Exception as e:
            logger.error(f"Error in Gmail worker loop: {e}")

        # Sleep for 60 seconds (1 minute polling interval)
        await asyncio.sleep(60.0)
