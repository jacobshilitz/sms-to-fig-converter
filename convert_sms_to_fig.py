#!/usr/bin/env python3
"""
Convert Android SMS/MMS backup XML to Fig messenger zip backup format.

Usage:
    python convert_sms_to_fig.py input.xml
    python convert_sms_to_fig.py input.xml --test
    python convert_sms_to_fig.py input.xml --limit 50
    python convert_sms_to_fig.py input.xml --output custom.zip
    python convert_sms_to_fig.py input.xml --dev  # Development mode: output to directory
"""

import argparse
import base64
import html
import json
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path


def normalize_phone_number(phone):
    """Normalize phone number to consistent format."""
    if not phone:
        return phone
    
    # Remove common separators
    phone = re.sub(r'[\s\-\(\)]', '', phone)
    
    # Ensure leading + if it's an international number
    if phone and not phone.startswith('+') and len(phone) >= 10:
        # If it looks like a US/Canada number without country code, add +
        if phone[0] == '1' and len(phone) == 11:
            phone = '+' + phone
        elif len(phone) == 10:
            # Assume US/Canada, add +1
            phone = '+1' + phone
    
    return phone


def decode_xml_entities(text):
    """Decode XML/HTML entities in text."""
    if not text:
        return text
    
    # Decode HTML entities
    text = html.unescape(text)
    
    # Handle numeric entities like &#10; (newline)
    text = re.sub(r'&#(\d+);', lambda m: chr(int(m.group(1))), text)
    text = re.sub(r'&#x([0-9a-fA-F]+);', lambda m: chr(int(m.group(1), 16)), text)
    
    return text


def get_xml_attr(element, attr, default=None):
    """Safely get XML attribute, handling 'null' strings."""
    value = element.get(attr, default)
    if value == 'null' or value is None:
        return default
    return value


def convert_sms_to_fig(sms_elem, msg_id, thread_id, phone_normalizer):
    """Convert SMS XML element to Fig JSON format."""
    address = get_xml_attr(sms_elem, 'address', '')
    normalized_address = phone_normalizer(address)
    
    date = get_xml_attr(sms_elem, 'date', '0')
    date_sent = get_xml_attr(sms_elem, 'date_sent', '0')
    if date_sent == '0' or not date_sent:
        date_sent = '0'
    
    msg_type = get_xml_attr(sms_elem, 'type', '1')
    body = get_xml_attr(sms_elem, 'body', '')
    body = decode_xml_entities(body)
    
    contact_name = get_xml_attr(sms_elem, 'contact_name', '')
    
    fig_msg = {
        '_id': str(msg_id),
        'thread_id': str(thread_id),
        'address': normalized_address,
        'date': str(date),
        'date_sent': str(date_sent),
        'protocol': get_xml_attr(sms_elem, 'protocol', '0'),
        'read': get_xml_attr(sms_elem, 'read', '1'),
        'status': get_xml_attr(sms_elem, 'status', '-1'),
        'type': msg_type,
        'reply_path_present': get_xml_attr(sms_elem, 'reply_path_present', '0'),
        'body': body,
        'service_center': get_xml_attr(sms_elem, 'service_center', ''),
        'locked': get_xml_attr(sms_elem, 'locked', '0'),
        'sub_id': get_xml_attr(sms_elem, 'sub_id', '1'),
        'error_code': get_xml_attr(sms_elem, 'error_code', '-1'),
        'creator': 'com.figmessenger',
        'seen': get_xml_attr(sms_elem, 'seen', '1'),
        'ipmsg_id': get_xml_attr(sms_elem, 'ipmsg_id', '0'),
    }
    
    # Add display name if contact name is not "(Unknown)"
    if contact_name and contact_name != '(Unknown)':
        fig_msg['__display_name'] = contact_name
    
    return fig_msg


def extract_mms_part_data(part_elem, temp_data_dir, message_date, part_seq):
    """Extract MMS part data and save as binary file."""
    data_attr = get_xml_attr(part_elem, 'data')
    
    if not data_attr:
        return None
    
    try:
        # Decode base64 data
        binary_data = base64.b64decode(data_attr)
        
        # Generate filename using message timestamp (like existing Fig format)
        # Format: PART_{timestamp} where timestamp is in milliseconds from message date
        try:
            timestamp = int(message_date) if message_date else 0
        except (ValueError, TypeError):
            timestamp = 0
        
        # Use timestamp directly - if multiple parts exist, they'll overwrite each other
        # but typically each part with data has unique characteristics
        # For uniqueness with multiple parts, append sequence if seq > 0
        filename = f'PART_{timestamp}'
        
        # If sequence is provided and > 0, append it for uniqueness
        if part_seq:
            try:
                seq_num = int(part_seq)
                if seq_num > 0:
                    filename = f'PART_{timestamp}{seq_num}'
            except (ValueError, TypeError):
                pass
        
        filepath = os.path.join(temp_data_dir, filename)
        
        # Write binary file
        with open(filepath, 'wb') as f:
            f.write(binary_data)
        
        return filename
    except Exception as e:
        print(f"Warning: Failed to extract MMS part data: {e}", file=sys.stderr)
        return None


def convert_mms_to_fig(mms_elem, msg_id, thread_id, phone_normalizer, temp_data_dir, global_part_counter):
    """Convert MMS XML element to Fig JSON format."""
    date = get_xml_attr(mms_elem, 'date', '0')
    date_sent = get_xml_attr(mms_elem, 'date_sent', '0')
    if not date_sent or date_sent == '0':
        date_sent = '0'
    
    # Get addresses
    addrs = mms_elem.find('addrs')
    sender_address = None
    recipient_addresses = []
    address_counter = global_part_counter
    
    if addrs is not None:
        for addr in addrs.findall('addr'):
            addr_type = get_xml_attr(addr, 'type', '')
            addr_value = get_xml_attr(addr, 'address', '')
            normalized_addr = phone_normalizer(addr_value)
            
            if addr_type == '137':  # From/Sender
                sender_address = {
                    '_id': str(address_counter),
                    'msg_id': str(msg_id),
                    'address': normalized_addr,
                    'type': '137',
                    'charset': get_xml_attr(addr, 'charset', '106'),
                }
                contact_name = get_xml_attr(mms_elem, 'contact_name', '')
                if contact_name and contact_name != '(Unknown)':
                    sender_address['__display_name'] = contact_name
                address_counter += 1
            elif addr_type == '151':  # To/Recipient
                recipient_addresses.append({
                    '_id': str(address_counter),
                    'msg_id': str(msg_id),
                    'address': normalized_addr,
                    'type': '151',
                    'charset': get_xml_attr(addr, 'charset', '106'),
                })
                address_counter += 1
    
    # Default sender if not found
    if not sender_address:
        address = get_xml_attr(mms_elem, 'address', '')
        normalized_address = phone_normalizer(address)
        sender_address = {
            '_id': str(address_counter),
            'msg_id': str(msg_id),
            'address': normalized_address,
            'type': '137',
            'charset': '106',
        }
        address_counter += 1
    
    # Update global counter
    global_part_counter = address_counter
    
    # Process parts
    parts = mms_elem.find('parts')
    fig_parts = []
    part_id_base = global_part_counter
    
    if parts is not None:
        for idx, part in enumerate(parts.findall('part')):
            part_seq = get_xml_attr(part, 'seq', str(idx))
            ct = get_xml_attr(part, 'ct', '')
            name = get_xml_attr(part, 'name', '')
            text = get_xml_attr(part, 'text')
            
            fig_part = {
                '_id': str(part_id_base + idx),
                'mid': str(msg_id),
                'seq': part_seq,
                'ct': ct,
            }
            
            if name:
                fig_part['name'] = name
            
            # Handle text content
            if text:
                text = decode_xml_entities(text)
                fig_part['text'] = text
            
            # Handle binary data
            data_attr = get_xml_attr(part, 'data')
            if data_attr:
                filename = extract_mms_part_data(part, temp_data_dir, date, part_seq)
                if filename:
                    # Use Android-style path format
                    fig_part['_data'] = f'/data/user_de/0/com.android.providers.telephony/app_parts/{filename}'
            
            # Add other part attributes
            chset = get_xml_attr(part, 'chset')
            if chset:
                fig_part['chset'] = chset
            
            cid = get_xml_attr(part, 'cid')
            if cid:
                fig_part['cid'] = cid
            
            cl = get_xml_attr(part, 'cl')
            if cl:
                fig_part['cl'] = cl
            
            fig_parts.append(fig_part)
        
        # Update global counter after processing parts
        global_part_counter = part_id_base + len(fig_parts)
    
    # Build MMS message
    fig_msg = {
        '_id': str(msg_id),
        'thread_id': str(thread_id),
        'date': str(date),
        'date_sent': str(date_sent),
        'msg_box': get_xml_attr(mms_elem, 'msg_box', '1'),
        'read': get_xml_attr(mms_elem, 'read', '1'),
        'm_id': get_xml_attr(mms_elem, 'm_id', ''),
        'ct_t': get_xml_attr(mms_elem, 'ct_t', ''),
        'exp': get_xml_attr(mms_elem, 'exp', ''),
        'm_cls': get_xml_attr(mms_elem, 'm_cls', 'personal'),
        'm_type': get_xml_attr(mms_elem, 'm_type', '132'),
        'v': get_xml_attr(mms_elem, 'v', '18'),
        'pri': get_xml_attr(mms_elem, 'pri', '129'),
        'tr_id': get_xml_attr(mms_elem, 'tr_id', ''),
        'retr_st': get_xml_attr(mms_elem, 'retr_st', '128'),
        'retr_txt': get_xml_attr(mms_elem, 'retr_txt', '1000:OK'),
        'retr_txt_cs': get_xml_attr(mms_elem, 'retr_txt_cs', '106'),
        'd_rpt': get_xml_attr(mms_elem, 'd_rpt', '129'),
        'locked': get_xml_attr(mms_elem, 'locked', '0'),
        'sub_id': get_xml_attr(mms_elem, 'sub_id', '1'),
        'seen': get_xml_attr(mms_elem, 'seen', '1'),
        'creator': get_xml_attr(mms_elem, 'creator', 'com.figmessenger'),
        'text_only': get_xml_attr(mms_elem, 'text_only', '0'),
        '__sender_address': sender_address,
        '__recipient_addresses': recipient_addresses,
        '__parts': fig_parts,
    }
    
    return fig_msg, global_part_counter


def main():
    parser = argparse.ArgumentParser(
        description='Convert Android SMS/MMS backup XML to Fig messenger zip backup format'
    )
    parser.add_argument('input_file', help='Input XML file path')
    parser.add_argument('--limit', type=int, help='Process only first N messages')
    parser.add_argument('--test', action='store_true', help='Process first 50 messages (test mode)')
    parser.add_argument('--output', help='Output zip filename (default: fig_backup.zip or fig_backup_test.zip)')
    parser.add_argument('--dev', '--no-zip', action='store_true', dest='dev_mode', help='Development mode: output files to directory instead of zip')
    
    args = parser.parse_args()
    
    # Determine limit
    limit = None
    if args.test:
        limit = 50
    elif args.limit:
        limit = args.limit
    
    # Determine output filename or directory
    if args.dev_mode:
        # Development mode: output to directory
        if args.output:
            output_dir = args.output
        else:
            output_dir = 'fig_backup'
    else:
        # Normal mode: output to zip
        if args.output:
            output_file = args.output
        else:
            output_file = 'fig_backup.zip'
    
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
    
    # Create working directory (temporary for zip mode, permanent for dev mode)
    if args.dev_mode:
        # Development mode: use permanent directory
        work_dir = output_dir
        os.makedirs(work_dir, exist_ok=True)
        temp_data_dir = os.path.join(work_dir, 'data')
        os.makedirs(temp_data_dir, exist_ok=True)
        messages_file = os.path.join(work_dir, 'messages.ndjson')
        temp_dir_context = None
    else:
        # Normal mode: use temporary directory
        temp_dir_context = tempfile.TemporaryDirectory()
        work_dir = temp_dir_context.name
        temp_data_dir = os.path.join(work_dir, 'data')
        os.makedirs(temp_data_dir, exist_ok=True)
        messages_file = os.path.join(work_dir, 'messages.ndjson')
    
    try:
        
        # Track threads by normalized phone number
        thread_map = {}
        thread_counter = 1
        
        # Message counters
        msg_id = 1
        global_part_counter = 1  # Global counter for addresses and parts
        sms_count = 0
        mms_count = 0
        found_sms = False
        found_mms = False
        
        # Process messages
        print("Processing messages...")
        
        with open(messages_file, 'w', encoding='utf-8') as f:
            # Process all SMS and MMS elements
            all_messages = []
            
            # Collect SMS messages
            for sms in root.findall('sms'):
                all_messages.append(('sms', sms))
            
            # Collect MMS messages
            for mms in root.findall('mms'):
                all_messages.append(('mms', mms))
            
            # Sort by date if available
            def get_date(msg_tuple):
                msg_type, msg_elem = msg_tuple
                date = get_xml_attr(msg_elem, 'date', '0')
                try:
                    return int(date)
                except:
                    return 0
            
            all_messages.sort(key=get_date)
            
            # Process messages
            processed = 0
            for msg_type, msg_elem in all_messages:
                # Check limit
                if limit and processed >= limit:
                    # If we haven't found both types yet, continue
                    if not (found_sms and found_mms):
                        # Continue processing to find missing type
                        pass
                    else:
                        break
                
                try:
                    # Get address for thread ID
                    address = get_xml_attr(msg_elem, 'address', '')
                    normalized_address = normalize_phone_number(address)
                    
                    # Get or create thread ID
                    if normalized_address not in thread_map:
                        thread_map[normalized_address] = thread_counter
                        thread_counter += 1
                    thread_id = thread_map[normalized_address]
                    
                    if msg_type == 'sms':
                        found_sms = True
                        fig_msg = convert_sms_to_fig(msg_elem, msg_id, thread_id, normalize_phone_number)
                        f.write(json.dumps(fig_msg, ensure_ascii=False) + '\n')
                        sms_count += 1
                        msg_id += 1
                        processed += 1
                    elif msg_type == 'mms':
                        found_mms = True
                        fig_msg, global_part_counter = convert_mms_to_fig(
                            msg_elem, msg_id, thread_id, normalize_phone_number,
                            temp_data_dir, global_part_counter
                        )
                        f.write(json.dumps(fig_msg, ensure_ascii=False) + '\n')
                        mms_count += 1
                        msg_id += 1
                        processed += 1
                
                except Exception as e:
                    print(f"Warning: Failed to process message: {e}", file=sys.stderr)
                    continue
        
        # Create output (zip or directory)
        if args.dev_mode:
            # Development mode: files already in place, just report
            attachment_count = len([f for f in os.listdir(temp_data_dir) if os.path.isfile(os.path.join(temp_data_dir, f))])
            print(f"\nConversion complete!")
            print(f"  Processed {sms_count} SMS messages")
            print(f"  Processed {mms_count} MMS messages")
            print(f"  Total: {sms_count + mms_count} messages")
            print(f"  Output directory: {output_dir}/")
            print(f"    - messages.ndjson")
            print(f"    - data/ (with {attachment_count} attachment files)")
        else:
            # Normal mode: create zip file
            print(f"Creating zip file: {output_file}")
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Add messages.ndjson
                zf.write(messages_file, 'messages.ndjson')
                
                # Add all data files
                for filename in os.listdir(temp_data_dir):
                    filepath = os.path.join(temp_data_dir, filename)
                    zf.write(filepath, f'data/{filename}')
            
            print(f"\nConversion complete!")
            print(f"  Processed {sms_count} SMS messages")
            print(f"  Processed {mms_count} MMS messages")
            print(f"  Total: {sms_count + mms_count} messages")
            print(f"  Output: {output_file}")
    
    finally:
        # Clean up temporary directory if needed
        if temp_dir_context:
            temp_dir_context.cleanup()


if __name__ == '__main__':
    main()
