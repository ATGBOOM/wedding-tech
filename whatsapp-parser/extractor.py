"""
Main extraction logic for vendor commitments using LangChain and Groq.
"""
import json
import os
from datetime import datetime, timezone
from typing import Optional

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from schemas import VendorCommitmentExtraction
from prompts import build_extraction_prompt


# Configuration
DEFAULT_MODEL = "llama-3.1-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"
TEMPERATURE = 0.1


class ExtractionError(Exception):
    """Custom exception for extraction errors."""
    pass


def build_llm_payload(parsed_conversation: dict) -> dict:
    """
    Extract only what LLM needs from parsed conversation.

    Args:
        parsed_conversation: Full output from parser.py

    Returns:
        Minimal payload for LLM processing
    """
    return {
        "vendor_name": parsed_conversation["metadata"]["vendor_name"],
        "vendor_category": parsed_conversation["metadata"]["vendor_category"],
        "conversation_date_range": {
            "start": parsed_conversation["parsing_info"]["date_range"]["earliest"],
            "end": parsed_conversation["parsing_info"]["date_range"]["latest"]
        },
        "messages": [
            {
                "id": msg["id"],
                "timestamp": msg["timestamp"],
                "sender": "planner" if msg["is_planner"] else "vendor",
                "content": msg["content"]
            }
            for msg in parsed_conversation["messages"]
            if msg["content"] and msg["content_type"] == "text"  # Skip media_omitted and non-text
        ]
    }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception_type((Exception,)),
    reraise=True
)
def call_llm_with_retry(
    llm: ChatGroq,
    prompt: str
) -> str:
    """
    Call LLM with exponential backoff retry logic.

    Args:
        llm: ChatGroq instance
        prompt: Complete prompt string

    Returns:
        Raw LLM response text

    Raises:
        Exception: If all retry attempts fail
    """
    messages = [
        HumanMessage(content=prompt)
    ]

    response = llm.invoke(messages)
    return response.content


def parse_llm_response(response_text: str) -> dict:
    """
    Parse and validate LLM response as JSON.

    Args:
        response_text: Raw response from LLM

    Returns:
        Parsed JSON dict

    Raises:
        ExtractionError: If response is not valid JSON
    """
    # Try to extract JSON from response (in case LLM adds explanation text)
    response_text = response_text.strip()

    # Find JSON content (look for outermost curly braces)
    start_idx = response_text.find('{')
    end_idx = response_text.rfind('}')

    if start_idx == -1 or end_idx == -1:
        raise ExtractionError("No JSON found in LLM response")

    json_text = response_text[start_idx:end_idx + 1]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"Invalid JSON in LLM response: {e}")


def validate_extraction(data: dict) -> VendorCommitmentExtraction:
    """
    Validate extraction output against Pydantic schema.

    Args:
        data: Parsed JSON from LLM

    Returns:
        Validated VendorCommitmentExtraction instance

    Raises:
        ExtractionError: If validation fails
    """
    try:
        return VendorCommitmentExtraction(**data)
    except Exception as e:
        raise ExtractionError(f"Schema validation failed: {e}")


def extract_vendor_commitments(
    parsed_conversation: dict,
    upload_date: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None
) -> dict:
    """
    Extract vendor commitments from parsed WhatsApp conversation.

    Args:
        parsed_conversation: Output from parser.py
        upload_date: ISO date for resolving "kal", "parso". Defaults to today.
        model: Groq model to use. Defaults to llama-3.1-70b-versatile
        api_key: Groq API key. Defaults to GROQ_API_KEY env var

    Returns:
        Dict containing structured vendor commitment data

    Raises:
        ExtractionError: If extraction fails
        ValueError: If API key not provided or found in environment
    """
    # Get API key
    if api_key is None:
        api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found. Either set GROQ_API_KEY environment variable "
            "or pass api_key parameter."
        )

    # Set upload_date to today if not provided
    if upload_date is None:
        upload_date = datetime.now(timezone.utc).astimezone().date().isoformat()

    # Build minimal payload
    llm_payload = build_llm_payload(parsed_conversation)

    # Build prompt
    prompt = build_extraction_prompt(llm_payload, upload_date)

    # Initialize LLM
    llm = ChatGroq(
        api_key=api_key,
        model=model,
        temperature=TEMPERATURE
    )

    try:
        # Call LLM with retry logic
        response_text = call_llm_with_retry(llm, prompt)

        # Parse response
        parsed_data = parse_llm_response(response_text)

        # Update metadata with actual values
        parsed_data["extraction_metadata"]["model"] = model
        parsed_data["extraction_metadata"]["extracted_at"] = datetime.now(timezone.utc).astimezone().isoformat()
        parsed_data["extraction_metadata"]["conversation_messages_count"] = len(llm_payload["messages"])
        parsed_data["extraction_metadata"]["upload_date_used"] = upload_date

        # Validate against schema
        validated = validate_extraction(parsed_data)

        # Return as dict
        return validated.model_dump()

    except Exception as e:
        # If primary model fails and we're using default, try fallback
        if model == DEFAULT_MODEL:
            try:
                print(f"Primary model failed: {e}. Trying fallback model {FALLBACK_MODEL}...")
                return extract_vendor_commitments(
                    parsed_conversation,
                    upload_date=upload_date,
                    model=FALLBACK_MODEL,
                    api_key=api_key
                )
            except Exception as fallback_error:
                raise ExtractionError(
                    f"Both primary and fallback models failed. "
                    f"Primary error: {e}. Fallback error: {fallback_error}"
                )
        else:
            raise ExtractionError(f"Extraction failed: {e}")


def extract_from_file(
    parsed_json_path: str,
    upload_date: Optional[str] = None,
    output_path: Optional[str] = None
) -> dict:
    """
    Extract vendor commitments from a parsed JSON file.

    Args:
        parsed_json_path: Path to parsed conversation JSON file
        upload_date: ISO date for resolving relative dates
        output_path: Optional path to save extraction output

    Returns:
        Dict containing structured vendor commitment data
    """
    # Read parsed conversation
    with open(parsed_json_path, 'r', encoding='utf-8') as f:
        parsed_conversation = json.load(f)

    # Extract commitments
    extraction = extract_vendor_commitments(parsed_conversation, upload_date)

    # Save to file if output_path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extraction, f, indent=2, ensure_ascii=False)
        print(f"Extraction saved to: {output_path}")

    return extraction


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python extractor.py <parsed_json_path> [upload_date] [output_path]")
        print("Example: python extractor.py sample_output.json 2024-06-15 extraction_output.json")
        sys.exit(1)

    parsed_json_path = sys.argv[1]
    upload_date = sys.argv[2] if len(sys.argv) > 2 else None
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        result = extract_from_file(parsed_json_path, upload_date, output_path)

        if not output_path:
            # Print to stdout if no output path
            print(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
