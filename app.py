import os
import streamlit as st
import random
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
import shutil

SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = 'credentials.json'

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    
    return build('drive', 'v3', credentials=creds)

def create_timestamped_folder(service, parent_id, nickname, timestamp):
    folder_name = f"{nickname}_{timestamp}"
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = service.files().create(body=file_metadata, fields='id').execute()
    return folder['id'], folder_name

def upload_directory(service, local_path, drive_folder_id):
    for root, dirs, files in os.walk(local_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            media = MediaFileUpload(file_path)
            file_metadata = {
                'name': file_name,
                'parents': [drive_folder_id]
            }
            service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()

def generate_nickname():
    adjectives = ["Swift", "Bright", "Calm", "Daring", "Eager"]
    nouns = ["Phoenix", "Owl", "Wolf", "Eagle", "Shark"]
    return f"{random.choice(adjectives)}_{random.choice( nouns)}_{random.randint(100,999)}"

def sync_to_drive(local_path, drive_root_id):
    service = get_drive_service()
    nickname = generate_nickname()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    timestamped_folder_id, folder_name = create_timestamped_folder(service, drive_root_id, nickname, timestamp)
    upload_directory(service, local_path, timestamped_folder_id[0])
    return (timestamped_folder_id[0], folder_name)

def main():
    st.title("Google Drive Sync")
    
    col_local, _ = st.columns([3,1])
    with col_local:
        if st.button("Browse Local Directory"):
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            selected_dir = filedialog.askdirectory()
            st.session_state.local_dir = selected_dir
            
    local_dir = st.text_input(
        "Local Directory Path",
        value=st.session_state.get("local_dir", "")
    )
    
    drive_root = st.text_input("Google Drive Root Folder ID")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sync to Drive"):
            if local_dir and drive_root:
                try:
                    folder_id = sync_to_drive(local_dir, drive_root)
                    st.success(f"Synced successfully! Nickname: {folder_id[1].split('_')[0]}\nTimestamp: {folder_id[1].split('_', 1)[1]}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Please fill all fields")
    
    with col2:
        if st.button("Fetch Latest"):
            if drive_root:
                try:
                    service = get_drive_service()
                    results = service.files().list(
                        q=f"'{drive_root}' in parents and mimeType='application/vnd.google-apps.folder'",
                        orderBy="createdTime desc",
                        pageSize=1
                    ).execute()
                    latest_folder = results.get('files', [])
                    if latest_folder:
                        st.success(f"Latest folder: {latest_folder[0]['name']}")
                    else:
                        st.info("No folders found")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
            else:
                st.warning("Please enter Drive Root Folder ID")

if __name__ == "__main__":
    main()