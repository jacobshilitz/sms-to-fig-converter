import json
import datetime
from collections import Counter

# Read messages
messages = []
with open(r'fig_backup\messages.ndjson', 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            messages.append(json.loads(line))

# Extract dates
dates = []
for m in messages:
    date_str = m.get('date', '0')
    if date_str and date_str != '0':
        try:
            dates.append(int(date_str))
        except:
            pass

dates.sort()

# Convert to readable dates
if dates:
    first_date = datetime.datetime.fromtimestamp(dates[0] / 1000)
    last_date = datetime.datetime.fromtimestamp(dates[-1] / 1000)
else:
    first_date = None
    last_date = None

# Count threads and addresses
threads = set(m.get('thread_id') for m in messages if m.get('thread_id'))
addresses = set(m.get('address') for m in messages if m.get('address'))

# Count messages by type
type_counter = Counter(m.get('type', 'unknown') for m in messages)

print("=" * 60)
print("BACKUP VERIFICATION SUMMARY")
print("=" * 60)
print(f"Total Messages: {len(messages)}")
print(f"\nDate Range:")
if first_date and last_date:
    print(f"  First Message: {first_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Last Message:  {last_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Span: {len(dates)} days")
else:
    print("  No valid dates found")

print(f"\nUnique Threads: {len(threads)}")
print(f"Thread IDs: {sorted([int(t) for t in threads if t and t.isdigit()])}")

print(f"\nUnique Contacts/Addresses: {len(addresses)}")

print(f"\nMessage Types:")
for msg_type, count in sorted(type_counter.items()):
    type_name = {1: "Received", 2: "Sent"}.get(int(msg_type) if str(msg_type).isdigit() else 0, f"Type {msg_type}")
    print(f"  {type_name}: {count}")

print("\n" + "=" * 60)
