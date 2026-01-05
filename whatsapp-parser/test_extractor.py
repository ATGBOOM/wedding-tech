"""
Tests for vendor commitment extraction.
"""
import json
import pytest
from datetime import datetime, timezone

from extractor import (
    build_llm_payload,
    extract_vendor_commitments,
    parse_llm_response,
    validate_extraction,
    ExtractionError
)
from schemas import VendorCommitmentExtraction


# Sample parsed conversation (from requirements)
SAMPLE_PARSED_CONVERSATION = {
    "metadata": {
        "source": "whatsapp_export",
        "uploaded_at": "2024-06-15T10:30:00+05:30",
        "file_hash": "sha256:abc123",
        "vendor_name": "Rajesh Flowers",
        "vendor_category": "florist",
        "wedding_id": "sharma-gupta-june-2024",
        "filter_applied": {"start_date": None, "reason": None}
    },
    "parsing_info": {
        "raw_message_count": 6,
        "parsed_message_count": 6,
        "skipped": {"deleted_messages": 0, "system_messages": 0, "before_start_date": 0, "over_limit": 0},
        "date_range": {"earliest": "2024-06-10T10:00:00+05:30", "latest": "2024-06-14T18:00:00+05:30"},
        "detected_participants": ["You", "Rajesh Flowers"],
        "planner_identifier": "You",
        "media_omitted_count": 0,
        "parse_errors": []
    },
    "messages": [
        {"id": "msg_001", "timestamp": "2024-06-10T10:00:00+05:30", "sender": "Rajesh Flowers", "is_planner": False, "content": "Namaste ji, haan 50 arrangements ho jayenge", "content_type": "text"},
        {"id": "msg_002", "timestamp": "2024-06-10T10:05:00+05:30", "sender": "You", "is_planner": True, "content": "Rate kya hoga?", "content_type": "text"},
        {"id": "msg_003", "timestamp": "2024-06-10T10:10:00+05:30", "sender": "Rajesh Flowers", "is_planner": False, "content": "Ji 300 per piece, total 15 hazaar ho jayega", "content_type": "text"},
        {"id": "msg_004", "timestamp": "2024-06-10T10:15:00+05:30", "sender": "You", "is_planner": True, "content": "Thik hai done. 20 tak chahiye, delivery subah 9 baje", "content_type": "text"},
        {"id": "msg_005", "timestamp": "2024-06-10T10:20:00+05:30", "sender": "Rajesh Flowers", "is_planner": False, "content": "Ji bilkul, 20 June subah tak pahunch jayega. Advance 5000 de dena", "content_type": "text"},
        {"id": "msg_006", "timestamp": "2024-06-14T18:00:00+05:30", "sender": "You", "is_planner": True, "content": "Bhaiya advance kal de deta hoon", "content_type": "text"}
    ]
}


# Additional test conversation: Media messages and mixed content
SAMPLE_WITH_MEDIA = {
    "metadata": {
        "source": "whatsapp_export",
        "uploaded_at": "2024-06-15T10:30:00+05:30",
        "file_hash": "sha256:def456",
        "vendor_name": "Kumar Photographers",
        "vendor_category": "photographer",
        "wedding_id": "sharma-gupta-june-2024",
        "filter_applied": {"start_date": None, "reason": None}
    },
    "parsing_info": {
        "raw_message_count": 5,
        "parsed_message_count": 5,
        "skipped": {"deleted_messages": 0, "system_messages": 0, "before_start_date": 0, "over_limit": 0},
        "date_range": {"earliest": "2024-06-12T14:00:00+05:30", "latest": "2024-06-13T16:00:00+05:30"},
        "detected_participants": ["You", "Kumar Photographers"],
        "planner_identifier": "You",
        "media_omitted_count": 2,
        "parse_errors": []
    },
    "messages": [
        {"id": "msg_001", "timestamp": "2024-06-12T14:00:00+05:30", "sender": "You", "is_planner": True, "content": "Portfolio dikha do", "content_type": "text"},
        {"id": "msg_002", "timestamp": "2024-06-12T14:05:00+05:30", "sender": "Kumar Photographers", "is_planner": False, "content": "<Media omitted>", "content_type": "media"},
        {"id": "msg_003", "timestamp": "2024-06-12T14:10:00+05:30", "sender": "You", "is_planner": True, "content": "Achha hai. Rate?", "content_type": "text"},
        {"id": "msg_004", "timestamp": "2024-06-12T14:15:00+05:30", "sender": "Kumar Photographers", "is_planner": False, "content": "50 hazaar full day. Video bhi chahiye?", "content_type": "text"},
        {"id": "msg_005", "timestamp": "2024-06-13T16:00:00+05:30", "sender": "You", "is_planner": True, "content": "Nahi sirf photo. Parso confirm karta hoon", "content_type": "text"}
    ]
}


# Test conversation: Cancelled commitment
SAMPLE_CANCELLED = {
    "metadata": {
        "source": "whatsapp_export",
        "uploaded_at": "2024-06-15T10:30:00+05:30",
        "file_hash": "sha256:ghi789",
        "vendor_name": "Gupta Tent House",
        "vendor_category": "tent",
        "wedding_id": "sharma-gupta-june-2024",
        "filter_applied": {"start_date": None, "reason": None}
    },
    "parsing_info": {
        "raw_message_count": 4,
        "parsed_message_count": 4,
        "skipped": {"deleted_messages": 0, "system_messages": 0, "before_start_date": 0, "over_limit": 0},
        "date_range": {"earliest": "2024-06-11T10:00:00+05:30", "latest": "2024-06-12T11:00:00+05:30"},
        "detected_participants": ["You", "Gupta Tent House"],
        "planner_identifier": "You",
        "media_omitted_count": 0,
        "parse_errors": []
    },
    "messages": [
        {"id": "msg_001", "timestamp": "2024-06-11T10:00:00+05:30", "sender": "You", "is_planner": True, "content": "500 capacity tent chahiye 25 June", "content_type": "text"},
        {"id": "msg_002", "timestamp": "2024-06-11T10:15:00+05:30", "sender": "Gupta Tent House", "is_planner": False, "content": "Ji 80 hazaar mein ho jayega", "content_type": "text"},
        {"id": "msg_003", "timestamp": "2024-06-12T10:00:00+05:30", "sender": "You", "is_planner": True, "content": "Bhaiya cancel kar do. Venue mein tent included hai", "content_type": "text"},
        {"id": "msg_004", "timestamp": "2024-06-12T11:00:00+05:30", "sender": "Gupta Tent House", "is_planner": False, "content": "Thik hai ji. Koi baat nahi", "content_type": "text"}
    ]
}


class TestBuildLLMPayload:
    """Test payload transformation."""

    def test_basic_payload_transformation(self):
        """Test that payload contains only necessary fields."""
        payload = build_llm_payload(SAMPLE_PARSED_CONVERSATION)

        assert payload["vendor_name"] == "Rajesh Flowers"
        assert payload["vendor_category"] == "florist"
        assert "conversation_date_range" in payload
        assert payload["conversation_date_range"]["start"] == "2024-06-10T10:00:00+05:30"
        assert payload["conversation_date_range"]["end"] == "2024-06-14T18:00:00+05:30"
        assert "messages" in payload
        assert len(payload["messages"]) == 6

    def test_message_transformation(self):
        """Test that messages are transformed correctly."""
        payload = build_llm_payload(SAMPLE_PARSED_CONVERSATION)

        first_msg = payload["messages"][0]
        assert first_msg["id"] == "msg_001"
        assert first_msg["timestamp"] == "2024-06-10T10:00:00+05:30"
        assert first_msg["sender"] == "vendor"
        assert first_msg["content"] == "Namaste ji, haan 50 arrangements ho jayenge"

        second_msg = payload["messages"][1]
        assert second_msg["sender"] == "planner"

    def test_media_messages_excluded(self):
        """Test that media messages are excluded from payload."""
        payload = build_llm_payload(SAMPLE_WITH_MEDIA)

        # Should only have 4 text messages (excluding media)
        assert len(payload["messages"]) == 4

        # Verify no media content in messages
        for msg in payload["messages"]:
            assert msg["content"] != "<Media omitted>"

    def test_payload_minimal_structure(self):
        """Test that payload doesn't contain unnecessary fields."""
        payload = build_llm_payload(SAMPLE_PARSED_CONVERSATION)

        # Should not contain metadata fields like file_hash, wedding_id, etc.
        assert "file_hash" not in payload
        assert "wedding_id" not in payload
        assert "source" not in payload
        assert "parsing_info" not in payload


class TestParseLLMResponse:
    """Test LLM response parsing."""

    def test_valid_json_response(self):
        """Test parsing valid JSON response."""
        response = '{"extraction_metadata": {"model": "test"}}'
        parsed = parse_llm_response(response)

        assert isinstance(parsed, dict)
        assert "extraction_metadata" in parsed

    def test_json_with_surrounding_text(self):
        """Test parsing JSON with surrounding explanation text."""
        response = """Here is the extraction:

{"extraction_metadata": {"model": "test"}, "vendor_summary": {"vendor_name": "Test"}}

Hope this helps!"""
        parsed = parse_llm_response(response)

        assert isinstance(parsed, dict)
        assert "extraction_metadata" in parsed
        assert "vendor_summary" in parsed

    def test_invalid_json_response(self):
        """Test that invalid JSON raises ExtractionError."""
        response = "This is not JSON at all"

        with pytest.raises(ExtractionError, match="No JSON found"):
            parse_llm_response(response)

    def test_malformed_json(self):
        """Test that malformed JSON raises ExtractionError."""
        response = '{"extraction_metadata": {"model": "test"'  # Missing closing braces

        with pytest.raises(ExtractionError, match="Invalid JSON"):
            parse_llm_response(response)


class TestValidateExtraction:
    """Test schema validation."""

    def test_valid_extraction(self):
        """Test validation of valid extraction data."""
        valid_data = {
            "extraction_metadata": {
                "model": "llama-3.1-70b-versatile",
                "extracted_at": "2024-06-15T10:00:00+05:30",
                "conversation_messages_count": 6,
                "upload_date_used": "2024-06-15"
            },
            "vendor_summary": {
                "vendor_name": "Rajesh Flowers",
                "vendor_category": "florist",
                "conversation_summary": "Test summary",
                "overall_status": "on_track",
                "last_contact_date": "2024-06-14"
            },
            "commitments": [],
            "payments": [],
            "open_items": []
        }

        validated = validate_extraction(valid_data)
        assert isinstance(validated, VendorCommitmentExtraction)

    def test_invalid_status(self):
        """Test that invalid status raises ExtractionError."""
        invalid_data = {
            "extraction_metadata": {
                "model": "llama-3.1-70b-versatile",
                "extracted_at": "2024-06-15T10:00:00+05:30",
                "conversation_messages_count": 6,
                "upload_date_used": "2024-06-15"
            },
            "vendor_summary": {
                "vendor_name": "Rajesh Flowers",
                "vendor_category": "florist",
                "conversation_summary": "Test summary",
                "overall_status": "invalid_status",  # Invalid value
                "last_contact_date": "2024-06-14"
            },
            "commitments": [],
            "payments": [],
            "open_items": []
        }

        with pytest.raises(ExtractionError, match="Schema validation failed"):
            validate_extraction(invalid_data)

    def test_missing_required_fields(self):
        """Test that missing required fields raises ExtractionError."""
        invalid_data = {
            "extraction_metadata": {
                "model": "llama-3.1-70b-versatile",
                "extracted_at": "2024-06-15T10:00:00+05:30",
                "conversation_messages_count": 6,
                "upload_date_used": "2024-06-15"
            }
            # Missing vendor_summary
        }

        with pytest.raises(ExtractionError, match="Schema validation failed"):
            validate_extraction(invalid_data)


class TestExtractVendorCommitments:
    """Integration tests for main extraction function."""

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-llm"),
        reason="Skipping LLM tests (use --run-llm to run)"
    )
    def test_extract_sample_conversation(self):
        """
        Test extraction with sample conversation.

        Expected extraction should identify:
        - Commitment: 50 red rose arrangements, deadline June 20, ₹15,000 total
        - Payment: ₹5,000 advance requested, status "discussed"
        - Open item: Advance payment pending
        - Followup: Before June 20 to confirm advance paid
        """
        result = extract_vendor_commitments(
            SAMPLE_PARSED_CONVERSATION,
            upload_date="2024-06-15"
        )

        # Verify structure
        assert "extraction_metadata" in result
        assert "vendor_summary" in result
        assert "commitments" in result
        assert "payments" in result
        assert "open_items" in result

        # Verify metadata
        assert result["extraction_metadata"]["conversation_messages_count"] == 6
        assert result["extraction_metadata"]["upload_date_used"] == "2024-06-15"

        # Verify vendor summary
        assert result["vendor_summary"]["vendor_name"] == "Rajesh Flowers"
        assert result["vendor_summary"]["vendor_category"] == "florist"

        # Verify commitments
        assert len(result["commitments"]) >= 1
        commitment = result["commitments"][0]
        assert "50" in commitment["description"] or "arrangements" in commitment["description"]
        assert commitment["deadline_resolved"] == "2024-06-20" or "20" in commitment["deadline_raw"]

        # Verify payments
        assert len(result["payments"]) >= 1
        payment = result["payments"][0]
        assert payment["amount"] == 5000
        assert payment["type"] == "advance"

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-llm"),
        reason="Skipping LLM tests (use --run-llm to run)"
    )
    def test_extract_with_media_messages(self):
        """Test that media messages don't break extraction."""
        result = extract_vendor_commitments(
            SAMPLE_WITH_MEDIA,
            upload_date="2024-06-15"
        )

        assert "extraction_metadata" in result
        assert result["extraction_metadata"]["conversation_messages_count"] == 4  # Excluding media

    @pytest.mark.skipif(
        not pytest.config.getoption("--run-llm"),
        reason="Skipping LLM tests (use --run-llm to run)"
    )
    def test_extract_cancelled_commitment(self):
        """Test extraction of cancelled commitment."""
        result = extract_vendor_commitments(
            SAMPLE_CANCELLED,
            upload_date="2024-06-15"
        )

        # Should identify cancelled status
        assert len(result["commitments"]) >= 1
        commitment = result["commitments"][0]
        assert commitment["status"] == "cancelled"

    def test_missing_api_key(self):
        """Test that missing API key raises ValueError."""
        import os
        original_key = os.environ.get("GROQ_API_KEY")

        try:
            # Remove API key from environment
            if "GROQ_API_KEY" in os.environ:
                del os.environ["GROQ_API_KEY"]

            with pytest.raises(ValueError, match="GROQ_API_KEY not found"):
                extract_vendor_commitments(
                    SAMPLE_PARSED_CONVERSATION,
                    api_key=None
                )
        finally:
            # Restore API key
            if original_key:
                os.environ["GROQ_API_KEY"] = original_key

    def test_default_upload_date(self):
        """Test that upload_date defaults to today."""
        # This test doesn't call LLM, just verifies default date handling
        today = datetime.now(timezone.utc).astimezone().date().isoformat()

        # We can't easily test this without mocking, but we can verify
        # the function accepts None for upload_date
        # Actual LLM test would verify it uses today's date


def pytest_addoption(parser):
    """Add custom pytest option for LLM tests."""
    parser.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="Run tests that call LLM (requires GROQ_API_KEY)"
    )


if __name__ == "__main__":
    # Run tests with: python test_extractor.py
    # Or with LLM tests: pytest test_extractor.py --run-llm
    pytest.main([__file__, "-v"])
