"""
Streamlit Web App for SMS and Call Backup to Fig Messenger Conversion
Simple web interface for non-technical users to convert Android SMS and call backups.
"""

import streamlit as st
import tempfile
import os
import zipfile
from pathlib import Path
import sys
from datetime import datetime
import re

# Import shared utilities
from utils import normalize_phone_number, decode_xml_entities, get_xml_attr

# Import conversion functions from the main script
from convert_sms_to_fig import (
    convert_sms_to_fig,
    convert_mms_to_fig,
    extract_mms_part_data
)
from convert_calls_to_fig import convert_call_to_fig
import xml.etree.ElementTree as ET
import json

# Page configuration
st.set_page_config(
    page_title="SMS & Call Backup Converter",
    page_icon="📱",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .info-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def convert_calls_xml_to_fig_streamlit(uploaded_file, limit=None, progress_bar=None, status_text=None):
    """Convert calls XML file to Fig JSON format - adapted for Streamlit."""
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Parse XML
        tree = ET.parse(tmp_path)
        root = tree.getroot()
        
        # Check if root is <calls>
        if root.tag != 'calls':
            raise ValueError(f"Expected <calls> root element, found <{root.tag}>")
        
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
        
        # Process calls
        fig_calls = []
        call_id = 1
        processed = 0
        
        for call_elem in all_calls:
            if limit and processed >= limit:
                break
            
            # Update progress
            if progress_bar:
                progress = min(processed / total_calls, 1.0)
                progress_bar.progress(progress)
            if status_text:
                status_text.text(f"Processing call {processed + 1} of {min(limit or total_calls, total_calls)}...")
            
            try:
                fig_call = convert_call_to_fig(call_elem, call_id, normalize_phone_number)
                fig_calls.append(fig_call)
                call_id += 1
                processed += 1
            except Exception as e:
                st.warning(f"Warning: Failed to process call: {e}")
                continue
        
        # Convert to JSON string
        json_data = json.dumps(fig_calls, ensure_ascii=False, indent=2)
        
        return json_data.encode('utf-8'), processed
    
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def convert_xml_to_fig_streamlit(uploaded_file, limit=None, progress_bar=None, status_text=None):
    """Convert XML file to Fig format - adapted for Streamlit."""
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    
    try:
        # Parse XML
        tree = ET.parse(tmp_path)
        root = tree.getroot()
        
        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_data_dir = os.path.join(temp_dir, 'data')
            os.makedirs(temp_data_dir, exist_ok=True)
            messages_file = os.path.join(temp_dir, 'messages.ndjson')
            
            # Track threads
            thread_map = {}
            thread_counter = 1
            msg_id = 1
            global_part_counter = 1
            sms_count = 0
            mms_count = 0
            
            # Collect all messages
            all_messages = []
            for sms in root.findall('sms'):
                all_messages.append(('sms', sms))
            for mms in root.findall('mms'):
                all_messages.append(('mms', mms))
            
            # Sort by date
            def get_date(msg_tuple):
                msg_type, msg_elem = msg_tuple
                date = get_xml_attr(msg_elem, 'date', '0')
                try:
                    return int(date)
                except:
                    return 0
            
            all_messages.sort(key=get_date)
            total_messages = len(all_messages)
            
            # Process messages
            with open(messages_file, 'w', encoding='utf-8') as f:
                processed = 0
                for msg_type, msg_elem in all_messages:
                    if limit and processed >= limit:
                        break
                    
                    # Update progress
                    if progress_bar:
                        progress = min(processed / total_messages, 1.0)
                        progress_bar.progress(progress)
                    if status_text:
                        status_text.text(f"Processing message {processed + 1} of {min(limit or total_messages, total_messages)}...")
                    
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
                            fig_msg = convert_sms_to_fig(msg_elem, msg_id, thread_id, normalize_phone_number)
                            f.write(json.dumps(fig_msg, ensure_ascii=False) + '\n')
                            sms_count += 1
                            msg_id += 1
                            processed += 1
                        elif msg_type == 'mms':
                            fig_msg, global_part_counter = convert_mms_to_fig(
                                msg_elem, msg_id, thread_id, normalize_phone_number,
                                temp_data_dir, global_part_counter
                            )
                            f.write(json.dumps(fig_msg, ensure_ascii=False) + '\n')
                            mms_count += 1
                            msg_id += 1
                            processed += 1
                    
                    except Exception as e:
                        st.warning(f"Warning: Failed to process message: {e}")
                        continue
            
            # Create zip file
            zip_path = os.path.join(temp_dir, 'fig_backup.zip')
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(messages_file, 'messages.ndjson')
                for filename in os.listdir(temp_data_dir):
                    filepath = os.path.join(temp_data_dir, filename)
                    zf.write(filepath, f'data/{filename}')
            
            # Read zip file for download
            with open(zip_path, 'rb') as zf:
                zip_data = zf.read()
            
            return zip_data, sms_count, mms_count
    
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

def main():
    # Header
    st.markdown('<div class="main-header">📱 SMS & Call Backup to Fig Messenger Converter</div>', unsafe_allow_html=True)
    
    # Info section
    st.markdown("""
    <div class="info-box">
        <strong>What does this tool do?</strong><br>
        Convert your Android SMS/MMS and call backup XML files into a format compatible with Fig Messenger.
    </div>
    """, unsafe_allow_html=True)
    
    # Privacy warning section - concise
    st.markdown("""
    <div style="background-color: #fff3cd; padding: 0.75rem; border-radius: 0.5rem; border-left: 4px solid #ffc107; margin: 1rem 0;">
        <strong>🔒 Privacy Notice:</strong> Files are uploaded to the server and processed there. 
        Files are stored in memory (RAM) and automatically deleted when you close the tab or upload a new file. 
        <strong>For maximum privacy:</strong> Use the <a href="https://github.com/jacobshilitz/sms-to-fig-converter#-command-line-usage-backend" target="_blank">command-line version</a> or run locally.
        <a href="https://docs.streamlit.io/knowledge-base/using-streamlit/where-file-uploader-store-when-deleted" target="_blank" style="font-size: 0.85em;">(Learn more)</a>
    </div>
    """, unsafe_allow_html=True)
    
    # ============================================
    # SECTION 1: SMS/MMS CONVERTER
    # ============================================
    st.header("📨 SMS/MMS Converter")
    
    # File upload
    st.subheader("📤 Upload Your SMS Backup File")
    sms_uploaded_file = st.file_uploader(
        "Choose your Android SMS backup XML file",
        type=['xml'],
        help="Upload the XML file exported from your Android SMS backup app",
        key="sms_uploader"
    )
    
    # Options
    col1, col2 = st.columns(2)
    with col1:
        sms_test_mode = st.checkbox("Test Mode (First 50 messages only)", value=False, 
                                help="Process only the first 50 messages to test the conversion",
                                key="sms_test_mode")
    with col2:
        sms_custom_limit = st.number_input("Custom Message Limit (optional)", 
                                       min_value=1, value=None, 
                                       help="Limit the number of messages to process",
                                       key="sms_limit")
    
    # Convert button
    if sms_uploaded_file is not None:
        if st.button("🔄 Convert SMS/MMS to Fig Format", type="primary", use_container_width=True, key="sms_convert"):
            # Determine limit
            limit = None
            if sms_test_mode:
                limit = 50
            elif sms_custom_limit:
                limit = int(sms_custom_limit)
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Convert
                zip_data, sms_count, mms_count = convert_xml_to_fig_streamlit(
                    sms_uploaded_file, limit, progress_bar, status_text
                )
                
                # Update progress to 100%
                progress_bar.progress(1.0)
                status_text.empty()
                
                # Success message
                st.markdown(f"""
                <div class="success-box">
                    <strong>✅ Conversion Complete!</strong><br>
                    Processed {sms_count} SMS messages and {mms_count} MMS messages<br>
                    Total: {sms_count + mms_count} messages
                </div>
                """, unsafe_allow_html=True)
                
                # Download button
                st.download_button(
                    label="📥 Download Fig Backup ZIP",
                    data=zip_data,
                    file_name="fig_backup.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key="sms_download"
                )
                
                st.info("💡 **Next Steps:** Import the downloaded ZIP file into Fig Messenger to restore your messages.")
            
            except Exception as e:
                st.error(f"❌ Error during conversion: {str(e)}")
                st.exception(e)
    else:
        st.info("👆 Please upload an XML file to get started")
    
    # Instructions section for SMS
    with st.expander("📖 How to Get Your Android SMS Backup"):
        st.markdown("""
        ### Step 1: Install Backup App from Play Store
        
        **Recommended App (Tested):**
        - **[SMS Backup & Restore](https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore)** (by SyncTech/Carbonite) - ⭐ **Tested & Verified**
          - 10M+ downloads
          - Free with optional cloud backup
          - Exports in XML format (required for this converter)
          - ✅ **This is the app we tested with - guaranteed to work**
        
        **Alternative Apps (Not Tested):**
        - **[SMS Backup+](https://play.google.com/store/apps/details?id=com.zegoggles.smssync)** - Open source option (may work, but not tested)
        - **[Super Backup & Restore](https://play.google.com/store/apps/details?id=com.idea.backup.smscontacts)** - Alternative option (may work, but not tested)
        
        **Note:** Other apps that export in the same XML format should work, but we have only tested with SMS Backup & Restore.
        
        ### Step 2: Export Your Messages
        
        1. Open the backup app you installed
        2. Grant necessary permissions (SMS, Contacts, Storage)
        3. Tap **Backup** or **Export** option
        4. **⚠️ IMPORTANT**: Select **XML format** (not JSON or other formats)
        5. Choose what to backup:
           - ✅ SMS messages
           - ✅ MMS messages (if available)
           - ✅ Attachments (for MMS)
        6. Save the backup file
        
        ### Step 3: Transfer to Computer
        
        Transfer the XML file to your computer using:
        - USB cable
        - Email to yourself
        - Cloud storage (Google Drive, Dropbox, etc.)
        - File sharing apps
        
        ### Step 4: Upload Here
        
        Upload the XML file you exported, and this tool will convert it to Fig Messenger format.
        
        ### 💻 Prefer Command-Line? (More Private)
        
        For maximum privacy, use the command-line version instead:
        ```bash
        python convert_sms_to_fig.py your_backup.xml
        ```
        See [README.md](https://github.com/jacobshilitz/sms-to-fig-converter) for full documentation.
        
        ### 🔒 Privacy Options
        
        **For maximum privacy:**
        - **Command-line**: `python convert_sms_to_fig.py your_file.xml` (most private - runs on your computer)
        - **Run locally**: `streamlit run streamlit_app.py` (web interface on your computer)
        - See [README.md](https://github.com/jacobshilitz/sms-to-fig-converter) for details
        """)
    
    # Divider between sections
    st.divider()
    
    # ============================================
    # SECTION 2: CALLS CONVERTER
    # ============================================
    st.header("📞 Calls Converter")
    
    # File upload
    st.subheader("📤 Upload Your Call Backup File")
    calls_uploaded_file = st.file_uploader(
        "Choose your Android call backup XML file",
        type=['xml'],
        help="Upload the XML file exported from your Android call backup app",
        key="calls_uploader"
    )
    
    # Options
    col1, col2 = st.columns(2)
    with col1:
        calls_test_mode = st.checkbox("Test Mode (First 50 calls only)", value=False, 
                                help="Process only the first 50 calls to test the conversion",
                                key="calls_test_mode")
    with col2:
        calls_custom_limit = st.number_input("Custom Call Limit (optional)", 
                                       min_value=1, value=None, 
                                       help="Limit the number of calls to process",
                                       key="calls_limit")
    
    # Convert button
    if calls_uploaded_file is not None:
        if st.button("🔄 Convert Calls to Fig Format", type="primary", use_container_width=True, key="calls_convert"):
            # Determine limit
            limit = None
            if calls_test_mode:
                limit = 50
            elif calls_custom_limit:
                limit = int(calls_custom_limit)
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Convert
                json_data, calls_count = convert_calls_xml_to_fig_streamlit(
                    calls_uploaded_file, limit, progress_bar, status_text
                )
                
                # Update progress to 100%
                progress_bar.progress(1.0)
                status_text.empty()
                
                # Success message
                st.markdown(f"""
                <div class="success-box">
                    <strong>✅ Conversion Complete!</strong><br>
                    Processed {calls_count} calls
                </div>
                """, unsafe_allow_html=True)
                
                # Generate filename
                timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
                filename = f"calls-{timestamp}.json"
                
                # Download button
                st.download_button(
                    label="📥 Download Fig Calls JSON",
                    data=json_data,
                    file_name=filename,
                    mime="application/json",
                    use_container_width=True,
                    key="calls_download"
                )
                
                st.info("💡 **Next Steps:** Import the downloaded JSON file into Fig Messenger to restore your call history.")
            
            except Exception as e:
                st.error(f"❌ Error during conversion: {str(e)}")
                st.exception(e)
    else:
        st.info("👆 Please upload an XML file to get started")
    
    # Instructions section for Calls
    with st.expander("📖 How to Get Your Android Call Backup"):
        st.markdown("""
        ### Step 1: Install Backup App from Play Store
        
        **Recommended App (Tested):**
        - **[SMS Backup & Restore](https://play.google.com/store/apps/details?id=com.riteshsahu.SMSBackupRestore)** (by SyncTech/Carbonite) - ⭐ **Tested & Verified**
          - 10M+ downloads
          - Free with optional cloud backup
          - Exports call logs in XML format (required for this converter)
          - ✅ **This is the app we tested with - guaranteed to work**
        
        **Note:** Other apps that export in the same XML format should work, but we have only tested with SMS Backup & Restore.
        
        ### Step 2: Export Your Call History
        
        1. Open the backup app you installed
        2. Grant necessary permissions (Phone, Contacts, Storage)
        3. Tap **Backup** or **Export** option
        4. **⚠️ IMPORTANT**: Select **XML format** (not JSON or other formats)
        5. Choose what to backup:
           - ✅ Call logs
        6. Save the backup file
        
        ### Step 3: Transfer to Computer
        
        Transfer the XML file to your computer using:
        - USB cable
        - Email to yourself
        - Cloud storage (Google Drive, Dropbox, etc.)
        - File sharing apps
        
        ### Step 4: Upload Here
        
        Upload the XML file you exported, and this tool will convert it to Fig Messenger format.
        
        ### 💻 Prefer Command-Line? (More Private)
        
        For maximum privacy, use the command-line version instead:
        ```bash
        python convert_calls_to_fig.py your_backup.xml
        ```
        See [README.md](https://github.com/jacobshilitz/sms-to-fig-converter) for full documentation.
        
        ### 🔒 Privacy Options
        
        **For maximum privacy:**
        - **Command-line**: `python convert_calls_to_fig.py your_file.xml` (most private - runs on your computer)
        - **Run locally**: `streamlit run streamlit_app.py` (web interface on your computer)
        - See [README.md](https://github.com/jacobshilitz/sms-to-fig-converter) for details
        """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        Made with ❤️ for easy SMS and Call migration to Fig Messenger
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
