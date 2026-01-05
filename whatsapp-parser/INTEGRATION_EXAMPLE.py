"""
Integration example: Using parser.py with extractor.py

This demonstrates the complete pipeline from WhatsApp chat text
to structured vendor commitment data.
"""
import json
from parser import parse_whatsapp_chat
from extractor import extract_vendor_commitments


def complete_pipeline_example():
    """
    Complete pipeline: Parse WhatsApp chat -> Extract commitments
    """
    # Step 1: Parse WhatsApp chat text
    print("Step 1: Parsing WhatsApp conversation...")

    chat_file_path = "sample_chat.txt"
    vendor_name = "Rajesh Flowers"
    vendor_category = "florist"
    wedding_id = "sharma-gupta-june-2024"

    parsed_conversation = parse_whatsapp_chat(
        file_path=chat_file_path,
        vendor_name=vendor_name,
        vendor_category=vendor_category,
        wedding_id=wedding_id
    )

    print(f"✓ Parsed {parsed_conversation['parsing_info']['parsed_message_count']} messages")

    # Step 2: Extract vendor commitments using LLM
    print("\nStep 2: Extracting vendor commitments with LLM...")

    extraction = extract_vendor_commitments(
        parsed_conversation,
        upload_date="2024-06-15"  # Date for resolving "kal", "parso", etc.
    )

    print(f"✓ Extraction complete using {extraction['extraction_metadata']['model']}")

    # Step 3: Display results
    print("\n" + "=" * 60)
    print("VENDOR SUMMARY")
    print("=" * 60)

    summary = extraction['vendor_summary']
    print(f"Vendor: {summary['vendor_name']} ({summary['vendor_category']})")
    print(f"Status: {summary['overall_status'].upper()}")
    print(f"Last Contact: {summary['last_contact_date']}")
    print(f"\nSummary:\n{summary['conversation_summary']}")

    if summary.get('suggested_followup'):
        followup = summary['suggested_followup']
        print(f"\n⚠️  Follow-up suggested by {followup['date']}")
        print(f"   Reason: {followup['reason']}")

    # Step 4: Display commitments
    print("\n" + "=" * 60)
    print(f"COMMITMENTS ({len(extraction['commitments'])})")
    print("=" * 60)

    for i, commitment in enumerate(extraction['commitments'], 1):
        print(f"\n{i}. {commitment['description']}")
        print(f"   Deadline: {commitment['deadline_resolved'] or 'Not specified'} "
              f"(confidence: {commitment['deadline_confidence']})")

        if commitment.get('price'):
            price = commitment['price']
            print(f"   Price: ₹{price['amount']:,.0f} ({price['type']})")

        print(f"   Status: {commitment['status']}")
        print(f"   Evidence: {commitment['status_evidence']}")

    # Step 5: Display payments
    print("\n" + "=" * 60)
    print(f"PAYMENTS ({len(extraction['payments'])})")
    print("=" * 60)

    for i, payment in enumerate(extraction['payments'], 1):
        print(f"\n{i}. {payment['type'].title()}: ₹{payment['amount']:,.0f}")
        print(f"   Status: {payment['status']}")
        print(f"   Raw text: \"{payment['raw_text']}\"")

    # Step 6: Display open items
    print("\n" + "=" * 60)
    print(f"OPEN ITEMS ({len(extraction['open_items'])})")
    print("=" * 60)

    for i, item in enumerate(extraction['open_items'], 1):
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        print(f"\n{i}. {priority_emoji[item['priority']]} {item['description']}")
        print(f"   Priority: {item['priority'].upper()}")

    # Step 7: Save outputs
    print("\n" + "=" * 60)
    print("SAVING OUTPUTS")
    print("=" * 60)

    # Save parsed conversation
    parsed_output_path = "parsed_output.json"
    with open(parsed_output_path, 'w', encoding='utf-8') as f:
        json.dump(parsed_conversation, f, indent=2, ensure_ascii=False)
    print(f"✓ Parsed conversation saved to: {parsed_output_path}")

    # Save extraction
    extraction_output_path = "extraction_output.json"
    with open(extraction_output_path, 'w', encoding='utf-8') as f:
        json.dump(extraction, f, indent=2, ensure_ascii=False)
    print(f"✓ Extraction saved to: {extraction_output_path}")

    return parsed_conversation, extraction


def batch_processing_example():
    """
    Example: Process multiple vendor conversations
    """
    vendors = [
        {
            "file": "chats/florist_chat.txt",
            "name": "Rajesh Flowers",
            "category": "florist"
        },
        {
            "file": "chats/caterer_chat.txt",
            "name": "Sharma Caterers",
            "category": "caterer"
        },
        {
            "file": "chats/photographer_chat.txt",
            "name": "Kumar Photography",
            "category": "photographer"
        }
    ]

    wedding_id = "sharma-gupta-june-2024"
    upload_date = "2024-06-15"

    all_extractions = []

    for vendor in vendors:
        print(f"\nProcessing {vendor['name']}...")

        # Parse
        parsed = parse_whatsapp_chat(
            file_path=vendor['file'],
            vendor_name=vendor['name'],
            vendor_category=vendor['category'],
            wedding_id=wedding_id
        )

        # Extract
        extraction = extract_vendor_commitments(parsed, upload_date)

        all_extractions.append({
            "vendor": vendor['name'],
            "category": vendor['category'],
            "status": extraction['vendor_summary']['overall_status'],
            "commitments_count": len(extraction['commitments']),
            "payments_count": len(extraction['payments']),
            "open_items_count": len(extraction['open_items']),
            "extraction": extraction
        })

    # Generate summary report
    print("\n" + "=" * 60)
    print("BATCH PROCESSING SUMMARY")
    print("=" * 60)

    for result in all_extractions:
        status_emoji = {
            "on_track": "✅",
            "needs_attention": "⚠️",
            "at_risk": "🔴"
        }
        emoji = status_emoji.get(result['status'], "❓")

        print(f"\n{emoji} {result['vendor']} ({result['category']})")
        print(f"   Status: {result['status']}")
        print(f"   Commitments: {result['commitments_count']}")
        print(f"   Payments: {result['payments_count']}")
        print(f"   Open Items: {result['open_items_count']}")

    return all_extractions


def filtering_example():
    """
    Example: Extract only specific information
    """
    # Parse conversation
    parsed = parse_whatsapp_chat(
        file_path="sample_chat.txt",
        vendor_name="Rajesh Flowers",
        vendor_category="florist",
        wedding_id="sharma-gupta-june-2024"
    )

    # Extract commitments
    extraction = extract_vendor_commitments(parsed, upload_date="2024-06-15")

    # Filter: Only high-priority open items
    high_priority_items = [
        item for item in extraction['open_items']
        if item['priority'] == 'high'
    ]

    print(f"High-priority open items: {len(high_priority_items)}")
    for item in high_priority_items:
        print(f"  - {item['description']}")

    # Filter: Only pending/requested payments
    pending_payments = [
        payment for payment in extraction['payments']
        if payment['status'] in ['discussed', 'requested']
    ]

    print(f"\nPending payments: ₹{sum(p['amount'] for p in pending_payments):,.0f}")
    for payment in pending_payments:
        print(f"  - {payment['type']}: ₹{payment['amount']:,.0f} ({payment['status']})")

    # Filter: Commitments approaching deadline
    from datetime import datetime, timedelta

    today = datetime.fromisoformat("2024-06-15")
    week_from_now = today + timedelta(days=7)

    approaching_deadlines = []
    for commitment in extraction['commitments']:
        if commitment['deadline_resolved']:
            deadline = datetime.fromisoformat(commitment['deadline_resolved'])
            if today <= deadline <= week_from_now:
                approaching_deadlines.append(commitment)

    print(f"\nCommitments due within 7 days: {len(approaching_deadlines)}")
    for commitment in approaching_deadlines:
        print(f"  - {commitment['description']} (due: {commitment['deadline_resolved']})")


if __name__ == "__main__":
    import sys

    print("WhatsApp Chat Parser + LLM Extractor Integration Examples")
    print("=" * 60)

    # Check for GROQ_API_KEY
    import os
    if not os.getenv("GROQ_API_KEY"):
        print("\n⚠️  Warning: GROQ_API_KEY not set in environment")
        print("Set it with: export GROQ_API_KEY='your-key-here'\n")
        sys.exit(1)

    # Run complete pipeline
    print("\n### EXAMPLE 1: Complete Pipeline ###\n")
    try:
        parsed, extraction = complete_pipeline_example()
        print("\n✓ Complete pipeline example finished successfully")
    except Exception as e:
        print(f"\n✗ Error: {e}")

    # Uncomment to run other examples:
    # print("\n\n### EXAMPLE 2: Batch Processing ###\n")
    # all_extractions = batch_processing_example()

    # print("\n\n### EXAMPLE 3: Filtering and Analysis ###\n")
    # filtering_example()
