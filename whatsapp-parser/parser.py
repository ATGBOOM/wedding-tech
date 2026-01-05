"""WhatsApp chat export parser for Indian format exports."""

import re
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional


# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# Regex pattern for WhatsApp message format
# Format: [DD/MM/YYYY, HH:MM:SS] Sender: Message (24-hour format)
MESSAGE_PATTERN = re.compile(
    r'^\[(\d{1,2}/\d{1,2}/\d{4}),\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+):\s*(.*)$'
)

# System message patterns to skip
SYSTEM_MESSAGE_PATTERNS = [
    r'added',
    r'left',
    r'changed',
    r'created group',
    r'security code changed',
    r'joined using',
    r'removed',
    r'Messages and calls are end-to-end encrypted',
    r'Group call',
    r'‎'  # Special invisible character in WhatsApp system messages
]

# Deleted message patterns
DELETED_MESSAGE_PATTERNS = [
    'This message was deleted',
    'You deleted this message'
]


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of the file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """Parse WhatsApp format date and time to ISO datetime with IST timezone."""
    # Combine date and time
    datetime_str = f"{date_str}, {time_str}"

    # Parse format: DD/MM/YYYY, HH:MM:SS (24-hour)
    try:
        dt = datetime.strptime(datetime_str, '%d/%m/%Y, %H:%M:%S')
        # Add IST timezone
        return dt.replace(tzinfo=IST)
    except ValueError as e:
        raise ValueError(f"Could not parse datetime: {datetime_str}") from e


def is_system_message(content: str, sender: str) -> bool:
    """Check if message is a system message."""
    # Don't filter media messages
    content_lower = content.lower().strip().lstrip('\u200e\u200f\u202a\u202b\u202c\u202d\u202e')
    if ("omitted" in content_lower and
        ("image" in content_lower or "video" in content_lower or
         "audio" in content_lower or "document" in content_lower or
         "sticker" in content_lower or "gif" in content_lower or
         "contact" in content_lower or "media" in content_lower)):
        return False

    for pattern in SYSTEM_MESSAGE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True
        if re.search(pattern, sender, re.IGNORECASE):
            return True
    return False


def is_deleted_message(content: str) -> bool:
    """Check if message is deleted."""
    for pattern in DELETED_MESSAGE_PATTERNS:
        if pattern.lower() in content.lower():
            return True
    return False


def parse_whatsapp_export(
    file_path: str,
    start_date: Optional[str] = None
) -> dict:
    """
    Parse WhatsApp chat export file.

    Args:
        file_path: Path to WhatsApp .txt export file
        start_date: Optional ISO date string (YYYY-MM-DD) to filter older messages

    Returns:
        Dictionary containing metadata, parsing_info, and messages
    """
    # Calculate file hash
    file_hash = calculate_file_hash(file_path)

    # Parse start_date filter if provided
    start_date_filter = None
    filter_reason = None
    if start_date:
        start_date_filter = datetime.fromisoformat(start_date).replace(tzinfo=IST)
        filter_reason = f"Messages before {start_date} excluded"

    # Initialize counters and collections
    raw_message_count = 0
    skipped_deleted = 0
    skipped_system = 0
    skipped_before_date = 0
    skipped_over_limit = 0
    parse_errors = []
    participants = set()
    media_omitted_count = 0

    messages = []
    current_message = None

    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, 1):
        line = line.rstrip('\n')
        # Strip invisible characters (left-to-right mark, etc.)
        line = line.lstrip('\u200e\u200f\u202a\u202b\u202c\u202d\u202e')

        # Try to match message pattern
        match = MESSAGE_PATTERN.match(line)

        if match:
            # Save previous message if exists
            if current_message:
                raw_message_count += 1

                # Apply filters
                skip = False
                skip_reason = None

                # Check if deleted
                if is_deleted_message(current_message['content']):
                    skipped_deleted += 1
                    skip = True
                    skip_reason = "deleted"

                # Check if system message
                elif is_system_message(current_message['content'], current_message['sender']):
                    skipped_system += 1
                    skip = True
                    skip_reason = "system"

                # Check date filter
                elif start_date_filter and current_message['timestamp'] < start_date_filter:
                    skipped_before_date += 1
                    skip = True
                    skip_reason = "before_start_date"

                if not skip:
                    messages.append(current_message)
            # Start new message
            date_str, time_str, sender, content = match.groups()

            try:
                timestamp = parse_datetime(date_str, time_str)

                # Track participants
                participants.add(sender)

                current_message = {
                    'timestamp': timestamp,
                    'sender': sender.strip(),
                    'content': content,
                }
            except Exception as e:
                parse_errors.append({
                    'line': line_num,
                    'error': str(e),
                    'content': line[:100]
                })
                current_message = None

        else:
            # Continuation of previous message (multi-line)
            if current_message:
                if current_message['content']:
                    current_message['content'] += '\n' + line
                else:
                    current_message['content'] = line

    # Don't forget the last message
    if current_message:
        raw_message_count += 1

        skip = False
        if is_deleted_message(current_message['content']):
            skipped_deleted += 1
            skip = True
        elif is_system_message(current_message['content'], current_message['sender']):
            skipped_system += 1
            skip = True
        elif start_date_filter and current_message['timestamp'] < start_date_filter:
            skipped_before_date += 1
            skip = True

        if not skip:
            messages.append(current_message)

    # Sort messages by timestamp (most recent last)
    messages.sort(key=lambda m: m['timestamp'])

    # Apply 500 message limit (keep most recent)
    if len(messages) > 500:
        skipped_over_limit = len(messages) - 500
        messages = messages[-500:]

    # Process messages for final output
    formatted_messages = []
    for idx, msg in enumerate(messages, 1):
        message_id = f"msg_{idx:03d}"

        # Check for media omitted
        content_type = "text"
        content = msg['content']

        # Check for various media omitted patterns
        content_lower = content.lower().strip()
        if ("<media omitted>" in content_lower or
            "image omitted" in content_lower or
            "video omitted" in content_lower or
            "audio omitted" in content_lower or
            "document omitted" in content_lower or
            "sticker omitted" in content_lower or
            "gif omitted" in content_lower or
            "contact card omitted" in content_lower):
            content_type = "media_omitted"
            content = None
            media_omitted_count += 1

        # Detect if sender is planner (identified as "You")
        is_planner = msg['sender'].lower() == "you"

        formatted_messages.append({
            'id': message_id,
            'timestamp': msg['timestamp'].isoformat(),
            'sender': msg['sender'],
            'is_planner': is_planner,
            'content': content,
            'content_type': content_type
        })

    # Calculate date range
    earliest = None
    latest = None
    if formatted_messages:
        earliest = formatted_messages[0]['timestamp']
        latest = formatted_messages[-1]['timestamp']

    # Build output
    result = {
        'metadata': {
            'source': 'whatsapp_export',
            'uploaded_at': datetime.now(IST).isoformat(),
            'file_hash': file_hash,
            'vendor_name': None,
            'vendor_category': None,
            'wedding_id': None,
            'filter_applied': {
                'start_date': start_date,
                'reason': filter_reason
            }
        },
        'parsing_info': {
            'raw_message_count': raw_message_count,
            'parsed_message_count': len(formatted_messages),
            'skipped': {
                'deleted_messages': skipped_deleted,
                'system_messages': skipped_system,
                'before_start_date': skipped_before_date,
                'over_limit': skipped_over_limit
            },
            'date_range': {
                'earliest': earliest,
                'latest': latest
            },
            'detected_participants': sorted(list(participants)),
            'planner_identifier': 'You',
            'media_omitted_count': media_omitted_count,
            'parse_errors': parse_errors
        },
        'messages': formatted_messages
    }

    return result
