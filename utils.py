"""
Shared utility functions for SMS and Call backup conversion.
"""

import html
import re


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
