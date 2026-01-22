"""
Prompt templates for vendor commitment extraction - MVP version.
Optimized for token efficiency and accuracy.
"""
import json

SYSTEM_PROMPT = """You are an Indian wedding planner assistant extracting structured information from vendor WhatsApp conversations.

## Hindi/Hinglish Reference

**Confirmations:** pakka, done, ho jayega, thik hai, bilkul, zaroor, confirm hai
**Negations:** nahi hoga, cancel, mushkil hai, nahi ho payega
**Time:** kal (tomorrow), parso (day after), agle hafte (next week), tak (by/until), jaldi (soon/vague)
**Numbers:** hazaar (1,000), lakh (100,000), sau (100), rupaye (rupees)
**Ignore:** ji, bhaiya, didi, sir, madam (honorifics, not names)

## Extraction Rules

1. **agreed_details**: Only include things explicitly confirmed by both parties. Include specifics: flower types, colors, quantities, locations, menu items, prices.

2. **commitments**: Things vendor promised to deliver. Set status:
   - "agreed" = confirmed but not yet done
   - "done" = explicitly mentioned as completed
   - "cancelled" = called off

3. **completed**: Simple list of things already done (past tense confirmations like "ho gaya", "bhej diya").

4. **loose_threads**: Anything discussed but not finalized—questions left unanswered, prices quoted but not accepted, items mentioned but not confirmed.

5. **pending_payment**: Only if payment was discussed. Status:
   - "mentioned" = amount discussed
   - "requested" = vendor asked for payment
   - "promised" = planner agreed to pay
   - "paid" = confirmed paid

6. **next_action**: Single most important follow-up. Be specific.

7. **risk_flag**: True if: missed deadlines, vague commitments on critical items, payment disputes, or vendor unresponsive.

## Date Resolution

Reference date: {upload_date}
- "kal" → +1 day
- "parso" → +2 days  
- "agle hafte" → +7 days
- Vague terms ("jaldi", "baad mein") → leave by_when as null, set when_confidence: "vague"

## Output

Respond with ONLY valid JSON matching the schema. No preamble or explanation."""


EXAMPLE = {
    "input": {
        "vendor_name": "Sharma Caterers",
        "vendor_category": "caterer",
        "messages": [
            {"timestamp": "2024-06-10T14:00:00", "sender": "planner", "content": "Bhaiya 200 log ke liye menu final kar lo"},
            {"timestamp": "2024-06-10T14:05:00", "sender": "vendor", "content": "Ji bilkul. 500 per plate thik rahega?"},
            {"timestamp": "2024-06-10T14:10:00", "sender": "planner", "content": "Thik hai done. Kal tak booking confirm kar dena"},
            {"timestamp": "2024-06-12T16:00:00", "sender": "vendor", "content": "Ji ho gaya confirm. 25000 advance chahiye"}
        ]
    },
    "output": {
        "vendor_name": "Sharma Caterers",
        "vendor_category": "caterer",
        "summary": "Catering confirmed for 200 guests at ₹500/plate (₹1,00,000 total). Vendor requesting ₹25,000 advance, not yet paid.",
        "agreed_details": [
            {"category": "pricing", "detail": "per plate rate", "value": "₹500"},
            {"category": "quantity", "detail": "guest count", "value": "200"}
        ],
        "commitments": [
            {"what": "Catering for 200 guests", "by_when": "null", "when_confidence": "vague", "status": "agreed"}
        ],
        "completed": ["Booking confirmed"],
        "loose_threads": [],
        "pending_payment": {"amount": 25000, "purpose": "advance", "status": "requested"},
        "next_action": "Pay ₹25,000 advance to confirm booking",
        "risk_flag": False
    }
}


def build_extraction_prompt(payload: dict, upload_date: str) -> str:
    """
    Build extraction prompt with minimal tokens.
    
    Args:
        payload: Conversation payload with vendor_name, vendor_category, messages
        upload_date: ISO date for resolving relative dates (YYYY-MM-DD)
    
    Returns:
        Complete prompt string
    """
    return f"""{SYSTEM_PROMPT.format(upload_date=upload_date)}

            ## Example

            Input:
            ``````json
            {json.dumps(EXAMPLE["input"], ensure_ascii=False)}
            ``````

            Output:
            ``````json
            {json.dumps(EXAMPLE["output"], ensure_ascii=False)}
            ``````

            ## Your Task

            Extract from this conversation:
            ``````json
            {json.dumps(payload, ensure_ascii=False, indent=2)}
            `````
        """


