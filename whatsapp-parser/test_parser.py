"""Tests for WhatsApp chat export parser."""

import os
import json
import tempfile
from datetime import datetime
from parser import parse_whatsapp_export


def create_test_file(content: str) -> str:
    """Create a temporary test file with given content."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
        f.write(content)
        return f.name


def test_basic_parsing():
    """Test basic message parsing."""
    chat_content = """15/06/24, 2:34 pm - Rajesh Flowers: Ji, 50 arrangements confirm for 20th
15/06/24, 2:45 pm - You: Thik hai, red roses only
16/06/24, 10:00 am - Rajesh Flowers: Perfect, done!"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        assert result['parsing_info']['parsed_message_count'] == 3
        assert result['parsing_info']['raw_message_count'] == 3
        assert len(result['messages']) == 3

        # Check first message
        assert result['messages'][0]['sender'] == 'Rajesh Flowers'
        assert result['messages'][0]['content'] == 'Ji, 50 arrangements confirm for 20th'
        assert result['messages'][0]['is_planner'] == False
        assert result['messages'][0]['content_type'] == 'text'

        # Check planner detection
        assert result['messages'][1]['sender'] == 'You'
        assert result['messages'][1]['is_planner'] == True

        # Check participants
        assert set(result['parsing_info']['detected_participants']) == {'Rajesh Flowers', 'You'}

        print("✓ test_basic_parsing passed")
    finally:
        os.unlink(file_path)


def test_multiline_messages():
    """Test multi-line message parsing."""
    chat_content = """15/06/24, 2:34 pm - Rajesh Flowers: Ji, details ye hai:
1. Red roses - 30
2. White lilies - 20
Total 50 arrangements
15/06/24, 2:45 pm - You: Perfect!"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        assert result['parsing_info']['parsed_message_count'] == 2

        # Check multi-line content preserved with newlines
        expected_content = "Ji, details ye hai:\n1. Red roses - 30\n2. White lilies - 20\nTotal 50 arrangements"
        assert result['messages'][0]['content'] == expected_content

        print("✓ test_multiline_messages passed")
    finally:
        os.unlink(file_path)


def test_media_omitted():
    """Test media omitted message detection."""
    chat_content = """15/06/24, 2:34 pm - Rajesh Flowers: Photo bhej raha
15/06/24, 2:35 pm - Rajesh Flowers: <Media omitted>
15/06/24, 2:36 pm - You: Dekh liya, thanks!"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        assert result['parsing_info']['parsed_message_count'] == 3
        assert result['parsing_info']['media_omitted_count'] == 1

        # Check media message
        media_msg = result['messages'][1]
        assert media_msg['content_type'] == 'media_omitted'
        assert media_msg['content'] is None

        print("✓ test_media_omitted passed")
    finally:
        os.unlink(file_path)


def test_deleted_messages():
    """Test deleted message filtering."""
    chat_content = """15/06/24, 2:34 pm - Rajesh Flowers: Original message
15/06/24, 2:35 pm - Rajesh Flowers: This message was deleted
15/06/24, 2:36 pm - You: You deleted this message
15/06/24, 2:37 pm - You: Still here"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        assert result['parsing_info']['raw_message_count'] == 4
        assert result['parsing_info']['parsed_message_count'] == 2
        assert result['parsing_info']['skipped']['deleted_messages'] == 2

        # Only non-deleted messages should remain
        assert result['messages'][0]['content'] == 'Original message'
        assert result['messages'][1]['content'] == 'Still here'

        print("✓ test_deleted_messages passed")
    finally:
        os.unlink(file_path)


def test_system_messages():
    """Test system message filtering."""
    chat_content = """15/06/24, 2:34 pm - Rajesh Flowers: Hello
15/06/24, 2:35 pm - System: You added Priya Wedding
15/06/24, 2:36 pm - System: Messages and calls are end-to-end encrypted
15/06/24, 2:37 pm - System: Amit left
15/06/24, 2:38 pm - System: You changed the group description
15/06/24, 2:39 pm - System: You created group "Wedding Planning"
15/06/24, 2:40 pm - System: Security code changed
15/06/24, 2:41 pm - Rajesh Flowers: Real message here"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        assert result['parsing_info']['raw_message_count'] == 8
        assert result['parsing_info']['skipped']['system_messages'] == 6
        assert result['parsing_info']['parsed_message_count'] == 2

        # Only real messages should remain
        assert result['messages'][0]['content'] == 'Hello'
        assert result['messages'][1]['content'] == 'Real message here'

        print("✓ test_system_messages passed")
    finally:
        os.unlink(file_path)


def test_hinglish_content():
    """Test Hinglish (Hindi-English mixed) content."""
    chat_content = """15/06/24, 2:34 pm - Rajesh Flowers: Ji haan, sab ready hai
15/06/24, 2:35 pm - You: Accha, aur decoration ka kya scene hai?
15/06/24, 2:36 pm - Rajesh Flowers: Woh bhi confirm ho gaya, don't worry!"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        assert result['parsing_info']['parsed_message_count'] == 3

        # Check Hinglish content preserved
        assert result['messages'][0]['content'] == 'Ji haan, sab ready hai'
        assert result['messages'][1]['content'] == 'Accha, aur decoration ka kya scene hai?'
        assert result['messages'][2]['content'] == "Woh bhi confirm ho gaya, don't worry!"

        print("✓ test_hinglish_content passed")
    finally:
        os.unlink(file_path)


def test_date_filtering():
    """Test start_date filtering."""
    chat_content = """10/06/24, 2:34 pm - Rajesh Flowers: Old message 1
11/06/24, 2:35 pm - You: Old message 2
15/06/24, 2:36 pm - Rajesh Flowers: New message 1
16/06/24, 2:37 pm - You: New message 2"""

    file_path = create_test_file(chat_content)
    try:
        # Filter to only include messages from June 15 onwards
        result = parse_whatsapp_export(file_path, start_date='2024-06-15')

        assert result['parsing_info']['raw_message_count'] == 4
        assert result['parsing_info']['skipped']['before_start_date'] == 2
        assert result['parsing_info']['parsed_message_count'] == 2

        # Check filter metadata
        assert result['metadata']['filter_applied']['start_date'] == '2024-06-15'
        assert result['metadata']['filter_applied']['reason'] is not None

        # Only messages from 15th onwards
        assert result['messages'][0]['content'] == 'New message 1'
        assert result['messages'][1]['content'] == 'New message 2'

        print("✓ test_date_filtering passed")
    finally:
        os.unlink(file_path)


def test_500_message_limit():
    """Test 500 message truncation (keeps most recent)."""
    # Generate 550 messages with sequential timestamps
    messages = []
    for i in range(550):
        # Create sequential timestamps: increment minutes, then hours, then days
        total_minutes = i
        day = 1 + (total_minutes // 1440)  # 1440 minutes per day
        remaining_minutes = total_minutes % 1440
        hour = (remaining_minutes // 60) % 12
        if hour == 0:
            hour = 12
        minute = remaining_minutes % 60
        am_pm = 'am' if (remaining_minutes // 60) < 12 else 'pm'

        messages.append(f"{day:02d}/06/24, {hour}:{minute:02d} {am_pm} - Vendor: Message {i+1}")

    chat_content = '\n'.join(messages)

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        assert result['parsing_info']['raw_message_count'] == 550
        assert result['parsing_info']['parsed_message_count'] == 500
        assert result['parsing_info']['skipped']['over_limit'] == 50

        # Should keep most recent 500 (messages 51-550)
        assert result['messages'][0]['content'] == 'Message 51'
        assert result['messages'][-1]['content'] == 'Message 550'

        print("✓ test_500_message_limit passed")
    finally:
        os.unlink(file_path)


def test_message_ids():
    """Test sequential message ID generation."""
    chat_content = """15/06/24, 2:34 pm - Vendor: Message 1
15/06/24, 2:35 pm - You: Message 2
15/06/24, 2:36 pm - Vendor: Message 3"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        assert result['messages'][0]['id'] == 'msg_001'
        assert result['messages'][1]['id'] == 'msg_002'
        assert result['messages'][2]['id'] == 'msg_003'

        print("✓ test_message_ids passed")
    finally:
        os.unlink(file_path)


def test_timestamp_format():
    """Test ISO timestamp with IST timezone."""
    chat_content = """15/06/24, 2:34 pm - Vendor: Test message"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        timestamp = result['messages'][0]['timestamp']

        # Check ISO format with timezone
        assert '+05:30' in timestamp  # IST timezone
        assert timestamp.startswith('2024-06-15T14:34:00')  # 2:34 PM in 24hr

        print("✓ test_timestamp_format passed")
    finally:
        os.unlink(file_path)


def test_date_range():
    """Test date range calculation."""
    chat_content = """10/06/24, 2:34 pm - Vendor: First
15/06/24, 2:35 pm - You: Middle
20/06/24, 2:36 pm - Vendor: Last"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        date_range = result['parsing_info']['date_range']

        assert date_range['earliest'] is not None
        assert date_range['latest'] is not None
        assert '2024-06-10' in date_range['earliest']
        assert '2024-06-20' in date_range['latest']

        print("✓ test_date_range passed")
    finally:
        os.unlink(file_path)


def test_file_hash():
    """Test SHA256 hash generation."""
    chat_content = """15/06/24, 2:34 pm - Vendor: Test"""

    file_path = create_test_file(chat_content)
    try:
        result1 = parse_whatsapp_export(file_path)
        result2 = parse_whatsapp_export(file_path)

        # Same file should produce same hash
        assert result1['metadata']['file_hash'] == result2['metadata']['file_hash']
        assert len(result1['metadata']['file_hash']) == 64  # SHA256 is 64 hex chars

        print("✓ test_file_hash passed")
    finally:
        os.unlink(file_path)


def test_metadata_structure():
    """Test metadata structure."""
    chat_content = """15/06/24, 2:34 pm - Vendor: Test"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        metadata = result['metadata']

        assert metadata['source'] == 'whatsapp_export'
        assert metadata['uploaded_at'] is not None
        assert metadata['file_hash'] is not None
        assert metadata['vendor_name'] is None
        assert metadata['vendor_category'] is None
        assert metadata['wedding_id'] is None

        print("✓ test_metadata_structure passed")
    finally:
        os.unlink(file_path)


def test_edge_cases():
    """Test edge cases and special characters."""
    chat_content = """15/06/24, 2:34 pm - Vendor: Message with: colon in content
15/06/24, 2:35 pm - You: Multiple  spaces   here
15/06/24, 2:36 pm - Vendor Name With Spaces: Message content
15/06/24, 2:37 pm - Vendor:
15/06/24, 2:38 pm - You: Special chars !@#$%^&*()"""

    file_path = create_test_file(chat_content)
    try:
        result = parse_whatsapp_export(file_path)

        assert result['parsing_info']['parsed_message_count'] == 5

        # Check colon handling
        assert result['messages'][0]['content'] == 'Message with: colon in content'

        # Check spaces preserved
        assert result['messages'][1]['content'] == 'Multiple  spaces   here'

        # Check sender with spaces
        assert result['messages'][2]['sender'] == 'Vendor Name With Spaces'

        # Check empty content
        assert result['messages'][3]['content'] == ''

        # Check special characters
        assert result['messages'][4]['content'] == 'Special chars !@#$%^&*()'

        print("✓ test_edge_cases passed")
    finally:
        os.unlink(file_path)


def test_complex_scenario():
    """Test complex real-world scenario with all features."""
    chat_content = """10/06/24, 9:00 am - Wedding Decor India: Namaste! Main Rahul bol raha hoon
10/06/24, 9:05 am - You: Hi Rahul, wedding venue decoration ke liye quote chahiye
10/06/24, 9:10 am - Wedding Decor India: Sure! Kitne guests hai?
Aur theme kya prefer karenge?
Budget kya hai approximately?
10/06/24, 9:15 am - You: 500 guests
Royal theme chahiye - red and gold
Budget 5 lakhs tak
10/06/24, 9:20 am - Wedding Decor India: Perfect! Let me send some photos
10/06/24, 9:20 am - Wedding Decor India: <Media omitted>
10/06/24, 9:21 am - Wedding Decor India: <Media omitted>
10/06/24, 9:22 am - You: Wow! First wala amazing hai
10/06/24, 9:25 am - Wedding Decor India: This message was deleted
10/06/24, 9:30 am - System: You added Priya Singh
10/06/24, 9:35 am - Wedding Decor India: Quote bhej raha hoon:
- Stage decoration: 1.5L
- Mandap: 2L
- Entry gate: 50k
- Table decorations: 1L
Total: 5L
15/06/24, 2:00 pm - You: Priya se discuss kar liya, let's proceed
15/06/24, 2:05 pm - Wedding Decor India: Great! Advance 50% chahiye - 2.5L
15/06/24, 2:10 pm - You: You deleted this message
15/06/24, 2:11 pm - You: Payment details bhejo"""

    file_path = create_test_file(chat_content)
    try:
        # Test without date filter
        result = parse_whatsapp_export(file_path)

        # Should skip: 1 system message, 2 deleted messages
        # Should parse: 12 messages (including 2 media omitted)
        assert result['parsing_info']['raw_message_count'] == 15
        assert result['parsing_info']['skipped']['deleted_messages'] == 2
        assert result['parsing_info']['skipped']['system_messages'] == 1
        assert result['parsing_info']['parsed_message_count'] == 12
        assert result['parsing_info']['media_omitted_count'] == 2

        # Test with date filter
        result_filtered = parse_whatsapp_export(file_path, start_date='2024-06-15')
        assert result_filtered['parsing_info']['skipped']['before_start_date'] == 9
        assert result_filtered['parsing_info']['parsed_message_count'] == 3

        # Check participants (includes System from system message)
        assert set(result['parsing_info']['detected_participants']) == {'Wedding Decor India', 'You', 'System'}

        # Check multi-line message preserved
        quote_msg = next(m for m in result['messages'] if m['content'] and 'Quote bhej raha hoon' in m['content'])
        assert '\n' in quote_msg['content']
        assert '- Stage decoration: 1.5L' in quote_msg['content']

        print("✓ test_complex_scenario passed")
    finally:
        os.unlink(file_path)


def run_all_tests():
    """Run all tests."""
    print("\n🧪 Running WhatsApp Parser Tests\n")

    test_basic_parsing()
    test_multiline_messages()
    test_media_omitted()
    test_deleted_messages()
    test_system_messages()
    test_hinglish_content()
    test_date_filtering()
    test_500_message_limit()
    test_message_ids()
    test_timestamp_format()
    test_date_range()
    test_file_hash()
    test_metadata_structure()
    test_edge_cases()
    test_complex_scenario()

    print("\n✅ All tests passed!\n")


if __name__ == '__main__':
    run_all_tests()
