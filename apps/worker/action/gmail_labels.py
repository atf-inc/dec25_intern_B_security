"""
Gmail Label Management Utilities for Action Agent.

Handles:
- Creating MailShield labels if they don't exist
- Applying labels to messages based on security verdicts
- Handling race conditions during label creation
"""

import logging
import asyncio
from typing import Optional
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Label cache to avoid repeated API calls
# Maps label_name -> label_id
_label_cache: dict[str, str] = {}

# MailShield label definitions
MAILSHIELD_LABELS = {
    "MailShield/MALICIOUS": {
        "name": "MailShield/MALICIOUS",
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
        "color": {"backgroundColor": "#cc3a21", "textColor": "#ffffff"}  # Red
    },
    "MailShield/CAUTIOUS": {
        "name": "MailShield/CAUTIOUS",
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
        "color": {"backgroundColor": "#f2a600", "textColor": "#ffffff"}  # Orange
    },
    "MailShield/SAFE": {
        "name": "MailShield/SAFE",
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
        "color": {"backgroundColor": "#16a766", "textColor": "#ffffff"}  # Green
    },
}

# Verdict to label mapping
VERDICT_TO_LABEL = {
    "malicious": "MailShield/MALICIOUS",
    "suspicious": "MailShield/CAUTIOUS",
    "clean": "MailShield/SAFE",
    "safe": "MailShield/SAFE",  # Alias for Gemini response
}


def _fetch_label_blocking(service: Resource, label_name: str) -> Optional[str]:
    """
    Fetch a label ID by name (blocking call).
    Returns label_id if found, None otherwise.
    """
    try:
        result = service.users().labels().list(userId='me').execute()
        labels = result.get('labels', [])
        for label in labels:
            if label['name'] == label_name:
                return label['id']
        return None
    except HttpError as e:
        logger.error(f"Failed to list labels: {e}")
        return None


def _create_label_blocking(service: Resource, label_name: str) -> Optional[str]:
    """
    Create a new Gmail label (blocking call).
    Returns the new label_id, or None on failure.
    Handles 409 Conflict (label already exists) gracefully.
    """
    label_config = MAILSHIELD_LABELS.get(label_name, {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show",
    })
    
    try:
        result = service.users().labels().create(
            userId='me',
            body=label_config
        ).execute()
        label_id = result.get('id')
        logger.info(f"Created label '{label_name}' with ID: {label_id}")
        return label_id
    except HttpError as e:
        if e.resp.status == 409:
            # Label already exists (race condition with another process)
            logger.warning(f"Label '{label_name}' already exists (409 Conflict). Fetching ID...")
            return _fetch_label_blocking(service, label_name)
        logger.error(f"Failed to create label '{label_name}': {e}")
        return None


async def get_or_create_label(service: Resource, label_name: str) -> Optional[str]:
    """
    Get a label ID by name, creating it if it doesn't exist.
    Uses an in-memory cache to minimize API calls.
    
    Args:
        service: Gmail API service resource
        label_name: Full label name (e.g., "MailShield/MALICIOUS")
        
    Returns:
        Label ID string, or None if creation failed
    """
    # Check cache first
    if label_name in _label_cache:
        return _label_cache[label_name]
    
    # Run blocking calls in thread pool
    loop = asyncio.get_running_loop()
    
    # Try to fetch existing label
    label_id = await loop.run_in_executor(
        None, _fetch_label_blocking, service, label_name
    )
    
    if not label_id:
        # Create the label
        label_id = await loop.run_in_executor(
            None, _create_label_blocking, service, label_name
        )
    
    if label_id:
        _label_cache[label_name] = label_id
        
    return label_id


async def ensure_labels_exist(service: Resource) -> dict[str, str]:
    """
    Pre-create all MailShield labels at agent startup.
    This avoids race conditions when processing multiple emails.
    
    Args:
        service: Gmail API service resource
        
    Returns:
        Dict mapping label names to their IDs
    """
    results = {}
    for label_name in MAILSHIELD_LABELS:
        label_id = await get_or_create_label(service, label_name)
        if label_id:
            results[label_name] = label_id
        else:
            logger.error(f"Failed to ensure label exists: {label_name}")
    
    logger.info(f"Ensured {len(results)}/{len(MAILSHIELD_LABELS)} MailShield labels exist")
    return results


def _modify_message_blocking(
    service: Resource,
    message_id: str,
    add_label_ids: list[str],
    remove_label_ids: Optional[list[str]] = None
) -> bool:
    """
    Modify message labels (blocking call).
    
    Args:
        service: Gmail API service
        message_id: Gmail message ID
        add_label_ids: List of label IDs to add
        remove_label_ids: Optional list of label IDs to remove
        
    Returns:
        True on success, False on failure
    """
    body = {"addLabelIds": add_label_ids}
    if remove_label_ids:
        body["removeLabelIds"] = remove_label_ids
    
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body=body
        ).execute()
        return True
    except HttpError as e:
        logger.error(f"Failed to modify message {message_id}: {e}")
        return False


async def apply_labels(
    service: Resource,
    message_id: str,
    verdict: str,
    move_to_spam: bool = False
) -> bool:
    """
    Apply the appropriate MailShield label based on verdict.
    
    Args:
        service: Gmail API service
        message_id: Gmail message ID
        verdict: Security verdict ("malicious", "suspicious", "clean", "safe")
        move_to_spam: If True, move message to Spam (for malicious emails)
        
    Returns:
        True on success, False on failure
    """
    label_name = VERDICT_TO_LABEL.get(verdict.lower())
    if not label_name:
        logger.warning(f"Unknown verdict '{verdict}', defaulting to CAUTIOUS")
        label_name = "MailShield/CAUTIOUS"
    
    # Get or create the label
    label_id = await get_or_create_label(service, label_name)
    if not label_id:
        logger.error(f"Could not get label ID for {label_name}")
        return False
    
    # Prepare label modifications
    add_labels = [label_id]
    remove_labels = []
    
    if move_to_spam:
        # Get SPAM label ID (it's a system label, always exists)
        add_labels.append("SPAM")
        remove_labels.append("INBOX")
    
    # Apply modifications
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(
        None,
        _modify_message_blocking,
        service,
        message_id,
        add_labels,
        remove_labels if remove_labels else None
    )
    
    if success:
        logger.info(
            f"Applied label '{label_name}' to message {message_id}",
            extra={"move_to_spam": move_to_spam}
        )
    
    return success


def get_label_for_verdict(verdict: str) -> str:
    """
    Get the MailShield label name for a verdict.
    
    Args:
        verdict: Security verdict string
        
    Returns:
        Label name (e.g., "MailShield/MALICIOUS")
    """
    return VERDICT_TO_LABEL.get(verdict.lower(), "MailShield/CAUTIOUS")


def clear_label_cache() -> None:
    """Clear the label cache (useful for testing)."""
    _label_cache.clear()

