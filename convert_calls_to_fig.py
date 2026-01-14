#!/usr/bin/env python3
"""
Convert Android call backup XML to Fig messenger JSON format.

Usage:
    python convert_calls_to_fig.py input.xml
    python convert_calls_to_fig.py input.xml --test
    python convert_calls_to_fig.py input.xml --limit 50
    python convert_calls_to_fig.py input.xml --output custom.json
"""

import argparse
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

# Import shared utilities
from utils import normalize_phone_number, get_xml_attr


def format_phone_number(phone):
    """Format phone number for display (e.g., +14383993949 -> +1 438-399-3949)."""
    if not phone:
        return phone
    
    # Remove all non-digits except +
    digits = re.sub(r'[^\d+]', '', phone)
    
    # If it starts with +1 and has 11 digits after +
    if digits.startswith('+1') and len(digits) == 12:
        area = digits[2:5]
        first = digits[5:8]
        last = digits[8:12]
        return f"+1 {area}-{first}-{last}"
    # If it starts with + and has 10+ digits
    elif digits.startswith('+') and len(digits) > 10:
        # Just return with some spacing - keep it simple
        return phone
    # If it's 10 digits (US/Canada without country code)
    elif len(digits) == 10:
        area = digits[0:3]
        first = digits[3:6]
        last = digits[6:10]
        return f"{area}-{first}-{last}"
    # If it's 11 digits starting with 1
    elif len(digits) == 11 and digits[0] == '1':
        area = digits[1:4]
        first = digits[4:7]
        last = digits[7:11]
        return f"+1 {area}-{first}-{last}"
    
    # Default: return as-is
    return phone


def convert_call_to_fig(call_elem, call_id, phone_normalizer):
    """Convert call XML element to Fig JSON format."""
    number = get_xml_attr(call_elem, 'number', '')
    normalized_number = phone_normalizer(number)
    formatted_number = format_phone_number(normalized_number) if normalized_number else ''
    
    date = get_xml_attr(call_elem, 'date', '0')
    duration = get_xml_attr(call_elem, 'duration', '0')
    call_type = get_xml_attr(call_elem, 'type', '2')  # 1=incoming, 2=outgoing, 3=missed
    presentation = get_xml_attr(call_elem, 'presentation', '1')
    contact_name = get_xml_attr(call_elem, 'contact_name', '')
    subscription_id = get_xml_attr(call_elem, 'subscription_id', '')
    subscription_component_name = get_xml_attr(call_elem, 'subscription_component_name', '')
    post_dial_digits = get_xml_attr(call_elem, 'post_dial_digits', '')
    
    # Build FIG call object
    fig_call = {
        '_id': str(call_id),
        'new': '1',
        'date': str(date),
        'number': normalized_number if normalized_number else number,
        'normalized_number': normalized_number if normalized_number else number,
        'formatted_number': formatted_number,
        'duration': str(duration),
        'type': str(call_type),
        'presentation': str(presentation),
        'post_dial_digits': str(post_dial_digits),
        'indicate_phone_or_sim_contact': '-1',
        'photo_id': '0',
        'block_reason': '0',
        'add_for_all_users': '1',
        'numbertype': '0',
        'features': '0',
        'phone_account_hidden': '0',
        'transcription_state': '0',
        'is_sdn_contact': '0',
        'via_number': '',
        # Optional fields that may not be in XML but should be in FIG format
        'countryiso': '',  # Not in XML, empty by default
        'geocoded_location': '',  # Not in XML, empty by default
        'lookup_uri': '',  # Not in XML, empty by default
        'photo_uri': '',  # Not in XML, empty by default
        'last_modified': str(date),  # Use call date as last_modified if not available
    }
    
    # Add contact name if available and not "(Unknown)"
    if contact_name and contact_name != '(Unknown)':
        fig_call['name'] = contact_name
        fig_call['display_name'] = contact_name
    
    # Add optional fields if present (these override defaults if in XML)
    if subscription_id:
        fig_call['subscription_id'] = str(subscription_id)
    
    if subscription_component_name:
        fig_call['subscription_component_name'] = subscription_component_name
    
    # Add matched_number (formatted version)
    if formatted_number:
        fig_call['matched_number'] = formatted_number
    
    return fig_call


def main():
    parser = argparse.ArgumentParser(
        description='Convert Android call backup XML to Fig messenger JSON format'
    )
    parser.add_argument('input_file', help='Input XML file path')
    parser.add_argument('--limit', type=int, help='Process only first N calls')
    parser.add_argument('--test', action='store_true', help='Process first 50 calls (test mode)')
    parser.add_argument('--output', help='Output JSON filename (default: calls-YYYY-MM-DD_HHMMSS.json)')
    
    args = parser.parse_args()
    
    # Determine limit
    limit = None
    if args.test:
        limit = 50
    elif args.limit:
        limit = args.limit
    
    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        # Generate timestamp-based filename
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        output_file = f'calls-{timestamp}.json'
    
    # Check input file exists
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Reading XML file: {args.input_file}")
    
    # Parse XML
    try:
        tree = ET.parse(args.input_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Check if root is <calls>
    if root.tag != 'calls':
        print(f"Error: Expected <calls> root element, found <{root.tag}>", file=sys.stderr)
        sys.exit(1)
    
    # Collect all calls
    all_calls = []
    for call in root.findall('call'):
        all_calls.append(call)
    
    # Sort by date
    def get_date(call_elem):
        date = get_xml_attr(call_elem, 'date', '0')
        try:
            return int(date)
        except:
            return 0
    
    all_calls.sort(key=get_date)
    total_calls = len(all_calls)
    
    print(f"Found {total_calls} calls")
    
    # Process calls
    print("Processing calls...")
    fig_calls = []
    call_id = 1
    
    processed = 0
    for call_elem in all_calls:
        if limit and processed >= limit:
            break
        
        try:
            fig_call = convert_call_to_fig(call_elem, call_id, normalize_phone_number)
            fig_calls.append(fig_call)
            call_id += 1
            processed += 1
            
            if processed % 100 == 0:
                print(f"  Processed {processed} calls...")
        
        except Exception as e:
            print(f"Warning: Failed to process call: {e}", file=sys.stderr)
            continue
    
    # Write JSON file
    print(f"Writing output file: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fig_calls, f, ensure_ascii=False, indent=2)
    
    print(f"\nConversion complete!")
    print(f"  Processed {processed} calls")
    print(f"  Output: {output_file}")


if __name__ == '__main__':
    main()
