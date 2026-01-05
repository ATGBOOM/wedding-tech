# Vendor Commitment Extraction Layer

LLM-powered extraction of structured vendor commitment data from parsed WhatsApp conversations using LangChain and Groq.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Groq API Key

```bash
export GROQ_API_KEY="your-api-key-here"
```

### 3. Run Extraction

#### From Python

```python
from extractor import extract_vendor_commitments
import json

# Load parsed conversation
with open('sample_output.json', 'r') as f:
    parsed_conversation = json.load(f)

# Extract commitments
result = extract_vendor_commitments(
    parsed_conversation,
    upload_date="2024-06-15"  # Optional, defaults to today
)

# Use the results
print(result['vendor_summary']['conversation_summary'])
print(f"Found {len(result['commitments'])} commitments")
print(f"Found {len(result['payments'])} payments")
```

#### From Command Line

```bash
python extractor.py sample_output.json 2024-06-15 extraction_output.json
```

## File Structure

```
├── schemas.py          # Pydantic models for output validation
├── prompts.py          # Prompt templates and few-shot examples
├── extractor.py        # Main extraction logic
├── test_extractor.py   # Comprehensive test suite
└── requirements.txt    # Dependencies
```

## Architecture

### 1. Payload Transformer (`build_llm_payload`)

Transforms parsed conversation into minimal payload containing only:
- Vendor metadata (name, category)
- Conversation date range
- Messages (text only, excluding media)

This reduces token usage and focuses the LLM on relevant information.

### 2. Prompt Engineering (`prompts.py`)

Uses evidence-based prompting techniques:

- **Role + Context**: Sets role as Indian wedding planner assistant
- **Structured Output**: Defines exact JSON schema with Pydantic
- **Few-Shot Examples**: 3 examples covering:
  - Hinglish conversation with implicit confirmations
  - Price negotiation in Indian format (hazaar, lakh)
  - Vague deadline resolution
  - Completed transactions
- **Chain of Thought**: Instructs model to quote evidence before inference
- **Hindi/Hinglish Vocabulary**: Reference guide for common phrases
- **Relative Date Resolution**: Rules for "kal", "parso", etc.
- **Graceful Uncertainty**: Encourages null/low-confidence over guessing

### 3. LLM Integration (`extractor.py`)

Features:
- **Model**: `llama-3.1-70b-versatile` (fallback: `llama-3.1-8b-instant`)
- **Temperature**: 0.1 for consistency
- **Retry Logic**: Exponential backoff (2s, 4s, 8s) for rate limits
- **Validation**: Pydantic schema validation on output
- **Error Handling**: Graceful fallback to smaller model

### 4. Output Schema

```json
{
  "extraction_metadata": {
    "model": "llama-3.1-70b-versatile",
    "extracted_at": "<ISO timestamp>",
    "conversation_messages_count": 47,
    "upload_date_used": "2024-06-15"
  },

  "vendor_summary": {
    "vendor_name": "Rajesh Flowers",
    "vendor_category": "florist",
    "conversation_summary": "...",
    "overall_status": "on_track|needs_attention|at_risk",
    "last_contact_date": "2024-06-14",
    "suggested_followup": {
      "date": "2024-06-18",
      "reason": "..."
    }
  },

  "commitments": [...],
  "payments": [...],
  "open_items": [...]
}
```

## Testing

### Run Unit Tests

```bash
pytest test_extractor.py -v
```

### Run Integration Tests (requires GROQ_API_KEY)

```bash
pytest test_extractor.py --run-llm -v
```

### Test Coverage

- ✅ Payload transformation
- ✅ Media message filtering
- ✅ LLM response parsing
- ✅ Schema validation
- ✅ Error handling
- ✅ Integration with sample conversations

## Hindi/Hinglish Support

The system understands common Hindi/Hinglish expressions:

**Confirmations**: "pakka", "done", "ho jayega", "thik hai", "bilkul", "zaroor"

**Temporal**:
- "kal" → tomorrow (upload_date + 1 day)
- "parso" → day after tomorrow (upload_date + 2 days)
- "agle hafte" → next week (upload_date + 7 days)

**Numbers**: "hazaar" (1,000), "lakh" (100,000), "sau" (100)

## Date Resolution

The system resolves relative dates using the `upload_date` parameter:

- **Explicit dates** (e.g., "20 June", "15/06/2024") → `confidence: "high"`
- **Relative dates** (e.g., "kal", "parso") → `confidence: "medium"`
- **Vague references** (e.g., "jaldi", "baad mein") → `confidence: "low"`, `deadline_resolved: null`

## Status Assessment

**overall_status** is determined by:

- `on_track`: Clear commitments, reasonable deadlines, no major issues
- `needs_attention`: Some clarifications needed, minor pending items
- `at_risk`: Vague commitments, missed deadlines, payment issues

## Example Usage

```python
from extractor import extract_from_file

# Extract from file
result = extract_from_file(
    parsed_json_path='sample_output.json',
    upload_date='2024-06-15',
    output_path='extraction.json'
)

# Access extracted data
for commitment in result['commitments']:
    print(f"Commitment: {commitment['description']}")
    print(f"Deadline: {commitment['deadline_resolved']} (confidence: {commitment['deadline_confidence']})")
    if commitment['price']:
        print(f"Price: ₹{commitment['price']['amount']} ({commitment['price']['type']})")
    print(f"Status: {commitment['status']}")
    print(f"Evidence: {commitment['status_evidence']}")
    print()

for payment in result['payments']:
    print(f"Payment: ₹{payment['amount']} ({payment['type']})")
    print(f"Status: {payment['status']}")
    print()

for item in result['open_items']:
    print(f"Open Item ({item['priority']}): {item['description']}")
    print()
```

## Error Handling

The system includes robust error handling:

1. **Missing API Key**: Raises `ValueError` with clear message
2. **LLM Failures**: Automatic fallback to smaller model
3. **Invalid JSON**: Extracts JSON from response text
4. **Schema Validation**: Validates all outputs against Pydantic models
5. **Rate Limits**: Exponential backoff retry (3 attempts)

## Performance

- **Token Optimization**: Minimal payload reduces costs
- **Model Selection**: 70B for accuracy, 8B for fallback
- **Caching**: Consider implementing for repeated queries
- **Batch Processing**: Process multiple conversations sequentially

## Future Enhancements

- [ ] Support for multi-vendor conversations
- [ ] Confidence scoring for entire extraction
- [ ] Custom model selection per vendor category
- [ ] Conversation threading/grouping
- [ ] Multi-language support beyond Hindi/Hinglish
