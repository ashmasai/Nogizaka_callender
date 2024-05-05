from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from get_schedule import get_nogizaka_schedule
from dotenv import load_dotenv
import os.path


# スコープを設定

#APIの構築
def build_api():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    if os.path.exists('secret_folder/token.json'):
        creds = Credentials.from_authorized_user_file('secret_folder/token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('secret_folder/credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('secret_folder/token.json', 'w') as token:
                token.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)
    if service is None:
        print("Failed to create the Google Calendar service")
    return service

# 　イベントの追加
def add_event_to_calendar(event):
    service = build_api()
    #メインのカレンダーに追加する場合はcalenderID = "primary"を指定
    #別のカレンダーに追加する場合はそのカレンダーのIDを指定

    load_dotenv()  # .env ファイルから環境変数を読み込む
    # カレンダーIDを環境変数から取得
    calendar_id = os.getenv('GOOGLE_CALENDAR_ID')
    
    event_result = service.events().insert(calendarId = calendar_id, body=event).execute()
    print(f"Event created: {event_result.get('htmlLink')}")





events = get_nogizaka_schedule(0)
for event in events:
     add_event_to_calendar(event)
"""
if __name__ == "__main__":
    #現在から2ヶ月後までのイベント情報を取得し、カレンダーに追加
    num_month = 3
    for i in range(num_month):
        events = get_nogizaka_schedule(i)
        for event in events:
            add_event_to_calendar(event)
"""