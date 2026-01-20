"""
Prompt templates and few-shot examples for vendor commitment extraction.
"""

SYSTEM_PROMPT = """You are an experienced Indian wedding planner assistant who specializes in extracting structured information from vendor communications in Hindi/Hinglish.

Your task is to analyze WhatsApp conversations between wedding planners and vendors, and extract key commitments, payments, and action items.

## Common Hindi/Hinglish Vocabulary

**Confirmations:** "pakka", "done", "ho jayega", "thik hai", "bilkul", "zaroor", "ban jayega", "confirm hai"

**Negations:** "nahi hoga", "cancel", "mushkil hai", "nahi ho payega", "impossible"

**Temporal expressions:**
- "kal" = tomorrow (upload_date + 1 day)
- "parso" = day after tomorrow (upload_date + 2 days)
- "agle hafte" = next week (upload_date + 7 days)
- "tak" = by/until
- "pehle" = before
- "baad mein" = later
- "jaldi" = soon (vague)

**Numbers/Prices:**
- "hazaar" = thousand (1,000)
- "lakh" = 100,000
- "sau" = hundred (100)
- "rupaye" = rupees

**Honorifics:** "ji", "bhaiya", "didi", "sir", "madam" (signs of polite conversation, not names)

## Date Resolution Rules

Use the provided upload_date as reference for relative date resolution:
- Explicit dates like "20 June" or "15/06/2024" → deadline_confidence: "high"
- Relative dates like "kal", "parso", "agle hafte" → deadline_confidence: "medium"
- Vague references like "jaldi", "baad mein", "soon" → deadline_confidence: "low", keep deadline_resolved as null

## Status Inference Rules

When determining commitment status:
1. First, quote the relevant message evidence
2. Then make the inference based on:
   - "pakka", "done", "ho jayega", "bilkul" → suggests confirmation/in_progress
   - Questions or pending responses → pending
   - Past tense confirmations → completed
   - "cancel", "nahi hoga" → cancelled

## Payment Status Rules

- Vendor mentions amount without commitment → "discussed"
- Vendor asks for payment → "requested"
- Planner says they paid or will pay → "paid"
- Vendor confirms receiving payment → "confirmed_received"

## Overall Status Assessment

- "on_track": All commitments clear, deadlines reasonable, no major pending items
- "needs_attention": Some clarifications needed, minor pending items, or approaching deadlines
- "at_risk": Vague commitments, missed deadlines, payment issues, or major uncertainties

## Graceful Uncertainty

If something is ambiguous or unclear:
- Extract with low confidence rather than guessing
- Use null for fields you cannot determine
- Surface uncertainty in status_evidence or open_items
- It's better to indicate uncertainty than fabricate information

## Output Format

You must respond with valid JSON matching the exact schema provided. Include all required fields."""


FEW_SHOT_EXAMPLES = [
    {
        "description": "Hinglish conversation with implicit confirmation and relative date",
        "input": {
            "vendor_name": "Sharma Caterers",
            "vendor_category": "caterer",
            "conversation_date_range": {
                "start": "2024-06-10T14:00:00+05:30",
                "end": "2024-06-12T16:00:00+05:30"
            },
            "messages": [
                {
                    "id": "msg_001",
                    "timestamp": "2024-06-10T14:00:00+05:30",
                    "sender": "planner",
                    "content": "Bhaiya 200 log ke liye menu final kar lo"
                },
                {
                    "id": "msg_002",
                    "timestamp": "2024-06-10T14:05:00+05:30",
                    "sender": "vendor",
                    "content": "Ji bilkul. 500 per plate thik rahega?"
                },
                {
                    "id": "msg_003",
                    "timestamp": "2024-06-10T14:10:00+05:30",
                    "sender": "planner",
                    "content": "Thik hai done. Kal tak booking confirm kar dena"
                },
                {
                    "id": "msg_004",
                    "timestamp": "2024-06-12T16:00:00+05:30",
                    "sender": "vendor",
                    "content": "Ji ho gaya confirm. 25000 advance chahiye"
                }
            ]
        },
        "output": {
            "extraction_metadata": {
                "model": "llama-3.1-70b-versatile",
                "extracted_at": "2024-06-15T10:00:00+05:30",
                "conversation_messages_count": 4,
                "upload_date_used": "2024-06-15"
            },
            "vendor_summary": {
                "vendor_name": "Sharma Caterers",
                "vendor_category": "caterer",
                "conversation_summary": "Caterer confirmed 200 plate booking at ₹500 per plate. Total ₹100,000. Booking confirmed on June 12. Advance of ₹25,000 requested but not yet paid.",
                "overall_status": "needs_attention",
                "last_contact_date": "2024-06-12",
                "suggested_followup": {
                    "date": "2024-06-16",
                    "reason": "Pay advance amount of ₹25,000 to secure booking"
                }
            },
            "commitments": [
                {
                    "id": "commit_001",
                    "description": "Catering for 200 people",
                    "deadline_raw": "kal tak",
                    "deadline_resolved": "2024-06-16",
                    "deadline_confidence": "medium",
                    "price": {
                        "amount": 500,
                        "currency": "INR",
                        "type": "per_unit",
                        "raw_text": "500 per plate"
                    },
                    "status": "in_progress",
                    "status_evidence": "Vendor said 'ho gaya confirm' indicating booking is confirmed",
                    "source_message_ids": ["msg_001", "msg_002", "msg_004"]
                }
            ],
            "payments": [
                {
                    "id": "pay_001",
                    "type": "advance",
                    "amount": 25000,
                    "currency": "INR",
                    "status": "requested",
                    "date": "2024-06-12",
                    "raw_text": "25000 advance chahiye",
                    "source_message_ids": ["msg_004"]
                }
            ],
            "open_items": [
                {
                    "id": "open_001",
                    "description": "Advance payment of ₹25,000 pending",
                    "priority": "high",
                    "source_message_ids": ["msg_004"]
                }
            ]
        }
    },
    {
        "description": "Price negotiation in Indian format with vague deadline",
        "input": {
            "vendor_name": "Mehta Decorators",
            "vendor_category": "decorator",
            "conversation_date_range": {
                "start": "2024-06-08T10:00:00+05:30",
                "end": "2024-06-09T15:00:00+05:30"
            },
            "messages": [
                {
                    "id": "msg_001",
                    "timestamp": "2024-06-08T10:00:00+05:30",
                    "sender": "planner",
                    "content": "Stage decoration ka rate batao"
                },
                {
                    "id": "msg_002",
                    "timestamp": "2024-06-08T10:30:00+05:30",
                    "sender": "vendor",
                    "content": "Ji premium package 2 lakh mein ho jayega"
                },
                {
                    "id": "msg_003",
                    "timestamp": "2024-06-08T11:00:00+05:30",
                    "sender": "planner",
                    "content": "Bahut zyada hai. 1.5 lakh final?"
                },
                {
                    "id": "msg_004",
                    "timestamp": "2024-06-08T11:30:00+05:30",
                    "sender": "vendor",
                    "content": "Thik hai 1 lakh 75 hazaar mein kar deta hoon"
                },
                {
                    "id": "msg_005",
                    "timestamp": "2024-06-09T15:00:00+05:30",
                    "sender": "planner",
                    "content": "Done. Jaldi setup kar dena shaadi se ek din pehle"
                }
            ]
        },
        "output": {
            "extraction_metadata": {
                "model": "llama-3.1-70b-versatile",
                "extracted_at": "2024-06-15T10:00:00+05:30",
                "conversation_messages_count": 5,
                "upload_date_used": "2024-06-15"
            },
            "vendor_summary": {
                "vendor_name": "Mehta Decorators",
                "vendor_category": "decorator",
                "conversation_summary": "Stage decoration negotiated from ₹200,000 to ₹175,000. Setup needs to be done one day before wedding, but exact date not specified.",
                "overall_status": "needs_attention",
                "last_contact_date": "2024-06-09",
                "suggested_followup": {
                    "date": "2024-06-16",
                    "reason": "Confirm exact wedding date and setup date/time"
                }
            },
            "commitments": [
                {
                    "id": "commit_001",
                    "description": "Premium stage decoration setup",
                    "deadline_raw": "shaadi se ek din pehle",
                    "deadline_resolved": None,
                    "deadline_confidence": "low",
                    "price": {
                        "amount": 175000,
                        "currency": "INR",
                        "type": "total",
                        "raw_text": "1 lakh 75 hazaar"
                    },
                    "status": "pending",
                    "status_evidence": "Planner said 'Done' but wedding date not specified, so setup date unclear",
                    "source_message_ids": ["msg_002", "msg_004", "msg_005"]
                }
            ],
            "payments": [],
            "open_items": [
                {
                    "id": "open_001",
                    "description": "Wedding date not mentioned - cannot determine exact setup date",
                    "priority": "high",
                    "source_message_ids": ["msg_005"]
                },
                {
                    "id": "open_002",
                    "description": "Payment terms not discussed",
                    "priority": "medium",
                    "source_message_ids": []
                }
            ]
        }
    }
]


def build_extraction_prompt(payload: dict, upload_date: str) -> str:
    """
    Build the complete prompt for vendor commitment extraction.

    Args:
        payload: Minimal conversation payload
        upload_date: ISO date string for resolving relative dates (e.g., "2024-06-15")

    Returns:
        Complete prompt string
    """
    prompt = f"""{SYSTEM_PROMPT}

## Upload Date for Relative Date Resolution

Today's date (upload_date): {upload_date}

Use this date to resolve relative temporal expressions:
- "kal" (tomorrow) → {upload_date} + 1 day
- "parso" (day after tomorrow) → {upload_date} + 2 days
- "agle hafte" (next week) → {upload_date} + 7 days

## Few-Shot Examples

Here are examples of how to extract information:

"""

    # Add few-shot examples
    for i, example in enumerate(FEW_SHOT_EXAMPLES, 1):
        prompt += f"\n### Example {i}: {example['description']}\n\n"
        prompt += "**Input:**\n```json\n"
        import json
        prompt += json.dumps(example['input'], indent=2, ensure_ascii=False)
        prompt += "\n```\n\n**Output:**\n```json\n"
        prompt += json.dumps(example['output'], indent=2, ensure_ascii=False)
        prompt += "\n```\n\n"

    prompt += f"""
## Your Task

Now extract structured information from the following conversation:

```json
{json.dumps(payload, indent=2, ensure_ascii=False)}
```

Remember:
1. Copy vendor_name and vendor_category from the input to vendor_summary
2. Quote message evidence before making inferences
3. Use null for fields you cannot determine
4. Mark confidence appropriately (high/medium/low)
5. Resolve relative dates using upload_date: {upload_date}
6. Surface uncertainty rather than guessing

Respond with ONLY valid JSON matching the schema. Do not include any explanatory text before or after the JSON."""

    return prompt
