"""Main script to parse WhatsApp chat and output to JSON."""

import json
import sys
from parser import parse_whatsapp_export
from extractor import extract_vendor_commitments


def main():
    """Parse sample_chat.txt and write to sample_output.json."""
    input_file = 'sample_chat.txt'
    output_file = 'sample_output.json'
    extraction_output_file = 'extraction_output.json'

    try:
        print(f'Reading WhatsApp chat from {input_file}...')
        result = parse_whatsapp_export(input_file)

        print(f'\n=== Parsing Summary ===')
        print(f'Raw messages: {result["parsing_info"]["raw_message_count"]}')
        print(f'Parsed messages: {result["parsing_info"]["parsed_message_count"]}')
        print(f'Deleted messages: {result["parsing_info"]["skipped"]["deleted_messages"]}')
        print(f'System messages: {result["parsing_info"]["skipped"]["system_messages"]}')
        print(f'Media omitted: {result["parsing_info"]["media_omitted_count"]}')
        print(f'Participants: {", ".join(result["parsing_info"]["detected_participants"])}')

        if result["parsing_info"]["date_range"]["earliest"]:
            print(f'Date range: {result["parsing_info"]["date_range"]["earliest"][:10]} to {result["parsing_info"]["date_range"]["latest"][:10]}')

        print(f'\nWriting output to {output_file}...')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f'✓ Successfully parsed {result["parsing_info"]["parsed_message_count"]} messages')
        print(f'✓ Output saved to {output_file}')

        # Extract vendor commitments
        print(f'\n=== Extracting Vendor Commitments ===')
        print('Calling LLM to extract structured data...')
        extraction_result = extract_vendor_commitments(result)

        print(f'\nWriting extraction output to {extraction_output_file}...')
        with open(extraction_output_file, 'w', encoding='utf-8') as f:
            json.dump(extraction_result, f, indent=2, ensure_ascii=False)

        print(f'✓ Successfully extracted vendor commitments')
        print(f'✓ Extraction saved to {extraction_output_file}')

        # Display extraction summary
        print(f'\n=== Extraction Summary ===')
        print(f'Vendor: {extraction_result["vendor_summary"]["vendor_name"]}')
        print(f'Category: {extraction_result["vendor_summary"]["vendor_category"]}')
        print(f'Overall status: {extraction_result["vendor_summary"]["overall_status"]}')
        print(f'Commitments found: {len(extraction_result["commitments"])}')
        print(f'Payments discussed: {len(extraction_result["payments"])}')
        print(f'Open items: {len(extraction_result["open_items"])}')

    except FileNotFoundError:
        print(f'Error: {input_file} not found')
        sys.exit(1)
    except Exception as e:
        print(f'Error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
