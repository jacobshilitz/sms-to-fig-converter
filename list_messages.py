import json
import datetime
import os

# Read messages
messages = []
with open(r'fig_backup\messages.ndjson', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            messages.append(json.loads(line))

# Output file
output_file = 'messages_list.txt'

# Write messages to file
with open(output_file, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("MESSAGE LIST WITH DATES AND ATTACHMENTS\n")
    f.write("=" * 80 + "\n")
    f.write("\n")
    
    for i, msg in enumerate(messages, 1):
        # Get date
        date_str = msg.get('date', '0')
        if date_str and date_str != '0':
            try:
                timestamp = int(date_str) / 1000
                readable_date = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
            except:
                readable_date = "No date"
        else:
            readable_date = "No date"
        
        # Get message body
        body = msg.get('body', '')
        if not body:
            body = "(No text message)"
        
        # Get message type
        msg_type = msg.get('type', '')
        direction = "Received" if msg_type == "1" else "Sent" if msg_type == "2" else "Unknown"
        
        # Get contact/address
        address = msg.get('address', '')
        display_name = msg.get('__display_name', '')
        contact = display_name if display_name else address
        
        # Get attachments
        attachments = []
        parts = msg.get('__parts', [])
        if parts:
            for part in parts:
                content_type = part.get('ct', '')
                filename = part.get('cl', '')
                data_path = part.get('_data', '')
                
                if filename or content_type:
                    att_info = {
                        'filename': filename or 'unnamed',
                        'content_type': content_type or 'unknown',
                        'path': data_path
                    }
                    attachments.append(att_info)
        
        # Write message info
        f.write(f"Message #{i} - {readable_date} [{direction}]\n")
        f.write(f"Contact: {contact}\n")
        f.write(f"Message: {body}\n")
        
        if attachments:
            f.write("Attachments:\n")
            for att in attachments:
                f.write(f"  - {att['filename']} ({att['content_type']})\n")
                if att['path']:
                    # Extract just the filename from path
                    path_parts = att['path'].split('/')
                    if path_parts:
                        f.write(f"    Path: {path_parts[-1]}\n")
        else:
            f.write("Attachments: None\n")
        
        f.write("-" * 80 + "\n")
        f.write("\n")

print(f"Message list saved to: {output_file}")
print(f"Total messages: {len(messages)}")
