# SMS to Fig Messenger Migration Tool

Converts Android SMS/MMS backup XML files to Fig messenger zip backup format.

## Usage

### Basic Usage
```bash
python convert_sms_to_fig.py "example/sms from android smart phone.xml"
```

### Test Mode (Recommended First)
```bash
# Process first 50 messages to test
python convert_sms_to_fig.py "example/sms from android smart phone.xml" --test

# Or specify custom limit
python convert_sms_to_fig.py "example/sms from android smart phone.xml" --limit 100
```

### Custom Output
```bash
python convert_sms_to_fig.py "example/sms from android smart phone.xml" --output my_backup.zip
```

### Development Mode (No Zip)
```bash
# Output files to directory instead of zip (useful for debugging)
python convert_sms_to_fig.py "example/sms from android smart phone.xml" --dev

# Or with custom directory name
python convert_sms_to_fig.py "example/sms from android smart phone.xml" --dev --output my_output_dir
```

## Output

The script creates a zip file (`fig_backup.zip` or `fig_backup_test.zip` in test mode) containing:
- `messages.ndjson` - All converted messages in NDJSON format
- `data/PART_*` - Binary attachment files extracted from MMS messages

## Features

- Converts both SMS and MMS messages
- Extracts and includes MMS attachments (images, audio, etc.)
- Normalizes phone numbers
- Groups messages into threads
- Test mode ensures both SMS and MMS types are included in sample
- Creates zip file ready for Fig messenger import

## Requirements

- Python 3.6+
- Standard library only (no external dependencies)
