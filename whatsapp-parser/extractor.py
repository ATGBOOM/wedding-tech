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
DEFAULT_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"
TEMPERATURE = 0.1


class ExtractionError(Exception):
    """Custom exception for extraction errors."""
    pass


def is_relevant_message(content: str) -> bool:
    """
    Filter out low-value messages to reduce token usage.

    Args:
        content: Message text content

    Returns:
        True if message should be included in LLM payload
    """
    if not content:
        return False

    content_lower = content.lower()

    # Skip standalone greetings/acknowledgments (1-2 words with no substance)
    standalone_fillers = ["ok", "okay", "ji", "yes", "ha", "han", "haan", "thik", "theek"]
    if content_lower.strip() in standalone_fillers:
        return False

    # Keep messages with commitment/business keywords
    commitment_keywords = [
        # Confirmations
        "pakka", "done", "confirm", "ho jayega", "thik hai", "bilkul", "zaroor", "ban jayega",
        # Negations/Issues
        "nahi", "cancel", "mushkil", "impossible", "problem",
        # Temporal
        "kal", "parso", "hafte", "tak", "pehle", "baad", "jaldi", "date", "time",
        # Money/Numbers
        "rupaye", "rs", "₹", "hazaar", "lakh", "sau", "price", "rate", "advance", "payment", "pay",
        # Questions (usually important)
        "?", "kya", "kab", "kitna", "kaise", "kahan", "kaun",
        # Business terms
        "book", "booking", "menu", "setup", "deliver", "service"
    ]

    # Keep if contains any commitment keyword
    if any(keyword in content_lower for keyword in commitment_keywords):
        return True

    # Keep if contains numbers (prices, dates, quantities)
    if any(char.isdigit() for char in content):
        return True

    # Skip if too short and didn't match above (likely just filler)
    if len(content.split()) <= 2:
        return False

    # Keep everything else that's substantial
    return True


def build_llm_payload(parsed_conversation: dict, max_messages: int = 20) -> dict:
    """
    Extract only what LLM needs from parsed conversation.
    Filters messages to reduce token usage while preserving key information.

    Args:
        parsed_conversation: Full output from parser.py
        max_messages: Maximum number of messages to include (default: 20)

    Returns:
        Minimal payload for LLM processing with filtered messages
    """
    # Filter messages for relevance
    all_messages = [
        {
            "id": msg["id"],
            "timestamp": msg["timestamp"],
            "sender": "planner" if msg["is_planner"] else "vendor",
            "content": msg["content"]
        }
        for msg in parsed_conversation["messages"]
        if msg["content"] and msg["content_type"] == "text"  # Skip media_omitted and non-text
    ]

    # Apply relevance filter
    filtered_messages = [
        msg for msg in all_messages
        if is_relevant_message(msg["content"])
    ]

    # Limit to most recent N messages if conversation is too long
    if len(filtered_messages) > max_messages:
        filtered_messages = filtered_messages[-max_messages:]

    return {
        "vendor_name": parsed_conversation["metadata"]["vendor_name"],
        "vendor_category": parsed_conversation["metadata"]["vendor_category"],
        "conversation_date_range": {
            "start": parsed_conversation["parsing_info"]["date_range"]["earliest"],
            "end": parsed_conversation["parsing_info"]["date_range"]["latest"]
        },
        "messages": filtered_messages
    }


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=4),
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
    try:
        print("Sending request to LLM...")
        messages = [
            HumanMessage(content=prompt)
        ]

        response = llm.invoke(messages)
        print(f"Received response from LLM (length: {len(response.content)} chars)")
        return response.content
    except Exception as e:
        print(f"LLM call failed: {type(e).__name__}: {e}")
        raise


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
        model=model,
        api_key=api_key,
        temperature=TEMPERATURE
    )

    try:
        # Call LLM with retry logic
        print(f"\nCalling LLM (model: {model}, messages: {len(llm_payload['messages'])})...")
        response_text = call_llm_with_retry(llm, prompt)

        # Parse response
        print("Parsing LLM response...")
        parsed_data = parse_llm_response(response_text)

        # Update metadata with actual values
        parsed_data["extraction_metadata"]["model"] = model
        parsed_data["extraction_metadata"]["extracted_at"] = datetime.now(timezone.utc).astimezone().isoformat()
        parsed_data["extraction_metadata"]["conversation_messages_count"] = len(llm_payload["messages"])
        parsed_data["extraction_metadata"]["upload_date_used"] = upload_date

        # Validate against schema
        print("Validating against schema...")
        validated = validate_extraction(parsed_data)

        print("✓ Extraction completed successfully")
        # Return as dict
        return validated.model_dump()

    except Exception as e:
        print(f"\n✗ Error during extraction: {type(e).__name__}: {e}")

        # If primary model fails and we're using default, try fallback
        if model == DEFAULT_MODEL and model != FALLBACK_MODEL:
            try:
                print(f"\nRetrying with fallback model: {FALLBACK_MODEL}...")
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
