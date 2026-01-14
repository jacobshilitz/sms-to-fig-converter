# SMS to Fig Messenger Migration Tool

Converts Android SMS/MMS backup XML files to Fig messenger zip backup format.

## 📱 How to Export SMS Backup from Android

### Step 1: Install a Backup App from Play Store

**Recommended App (Tested):**
- **[SMS Backup & Restore](https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore)** (by SyncTech/Carbonite) - ⭐ **Tested & Verified**
  - 10M+ downloads
  - Backs up SMS, MMS, and call logs in XML format
  - Free with optional cloud backup to Google Drive, Dropbox, OneDrive
  - ✅ **This is the app we tested with - guaranteed to work**

**Alternative Apps (Not Tested):**
- **SMS Backup+** - [Play Store Link](https://play.google.com/store/apps/details?id=com.zegoggles.smssync) - Open source option (may work, but not tested)
- **Super Backup & Restore** - [Play Store Link](https://play.google.com/store/apps/details?id=com.idea.backup.smscontacts) - Alternative option (may work, but not tested)

**Note:** Other apps that export in the same XML format should work, but we have only tested with SMS Backup & Restore. If you use a different app and encounter issues, please report them.

### Step 2: Export Your Messages

1. Open the backup app you installed
2. Grant necessary permissions (SMS, Contacts, Storage)
3. Go to **Backup** or **Export** option
4. **Important**: Select **XML format** (not JSON or other formats)
5. Choose what to backup:
   - SMS messages ✅
   - MMS messages ✅ (if available)
   - Attachments ✅ (for MMS)
6. Save the backup file to your device storage or cloud

### Step 3: Transfer to Computer

Transfer the XML file to your computer using:
- USB cable
- Email to yourself
- Cloud storage (Google Drive, Dropbox, etc.)
- File sharing apps

The file will typically be named something like:
- `sms-YYYY-MM-DD.xml`
- `SMSBackupRestore_YYYY-MM-DD.xml`
- `backup.xml`

## 💻 Command-Line Usage (Backend)

The command-line version is the **most private** option - all processing happens on your computer.

### Installation

1. **Install Python 3.6+** if you don't have it:
   - Windows: Download from [python.org](https://www.python.org/downloads/)
   - Mac: `brew install python3` or download from python.org
   - Linux: `sudo apt install python3` (Ubuntu/Debian)

2. **Download this repository**:
   ```bash
   git clone https://github.com/jacobshilitz/sms-to-fig-converter.git
   cd sms-to-fig-converter
   ```

3. **No additional dependencies needed!** This tool uses only Python's standard library.

### Basic Usage

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

### Complete Example Workflow

```bash
# 1. First, test with a small sample (recommended)
python convert_sms_to_fig.py "backup.xml" --test

# 2. Check the output file
# This creates fig_backup_test.zip with first 50 messages

# 3. If test looks good, convert full backup
python convert_sms_to_fig.py "backup.xml"

# 4. Output will be fig_backup.zip - ready to import into Fig Messenger!
```

### Troubleshooting

**File not found error:**
```bash
# Make sure you're in the right directory or use full path
python convert_sms_to_fig.py "C:\Users\YourName\Downloads\backup.xml"
```

**Permission denied:**
```bash
# On Mac/Linux, you might need:
python3 convert_sms_to_fig.py "backup.xml"
```

**Large files taking too long:**
```bash
# Process in smaller batches first
python convert_sms_to_fig.py "backup.xml" --limit 1000
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

## Privacy & Security

### Command-Line Version (Most Private)
The command-line script (`convert_sms_to_fig.py`) processes files **entirely on your computer**. No data is sent anywhere.

### Web App Version (Streamlit)
- **Local execution**: If you run `streamlit run streamlit_app.py` on your computer, processing happens locally (private).
- **Hosted version**: If deployed to Streamlit Cloud, Railway, etc., files are uploaded to and processed on the server.
  - ⚠️ **Important**: Server administrators could potentially access your data.
  - Files are stored temporarily and should be cleaned up automatically.
  - For sensitive SMS data, **we recommend using the command-line version or running locally**.

### Best Practices
- ✅ Use command-line version for maximum privacy
- ✅ Run Streamlit locally if you want a web interface
- ✅ Self-host if you need both web interface and privacy
- ⚠️ Be cautious with hosted versions for sensitive personal data
