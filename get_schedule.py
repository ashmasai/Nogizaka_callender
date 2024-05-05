from datetime import datetime,timedelta
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from dateutil.relativedelta import relativedelta
from urllib.parse import urlparse, parse_qs
import pytz

#スクレイピング用のクラス
class Scraper:
    def __init__(self, base_url): #base_urlは
        #属性の設定
        self.base_url = base_url
        self.driver = None
        self.setup_driver()

    #WebDriverの設定をするメソッド
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless") # GUIがない環境で動作するためのheadlessオプションを指定
        chrome_options.add_argument("--no-sandbox") # sandboxプロセスを無効化
        chrome_options.add_argument("--disable-dev-shm-usage") # メモリ不足を防ぐためのオプション
        self.driver = webdriver.Chrome(options = chrome_options ) # ChromeのWebDriverオブジェクトを作成

    def fetch_schedule(self, date):
        url = self.base_url + f"&dy={date}"
        self.driver.get(url)

        self.driver.implicitly_wait(20)
        html = self.driver.page_source
        return BeautifulSoup(html, 'html.parser')

    def close(self):
        if self.driver:
            self.driver

#nヶ月後の日付を指定したフォーマットで返す関数
def get_formatted_date_n_months_later(n, date_format='%Y%m'):
    """
    :param n: int, 加算する月数
    :param date_format: str, 出力する日付のフォーマット
    :return: str, フォーマットされた日付
    """
    current_date = datetime.now()
    future_date = current_date + relativedelta(months=n)
    formatted_future_date = future_date.strftime(date_format)
    return formatted_future_date


# 誕生日タグには日付情報が記載されていないので、親要素に移動してから日付情報を取得
def extract_date_from_parent(div):
    
    parent_day_div = div.find_parent('div',class_='sc--day')
    id_div = parent_day_div.find('div', class_='sc--day__hd js-pos a--tx')
    
    if parent_day_div:
        day = id_div.get('id') # IDから日付情報を取得
    return day

#イベントごとにまとめたHTMLのリストから、テキスト情報を抽出する関数
def extract_event(divs, formatted_future_date):
    # 空のリストを初期化
    events = []

    date_obj = datetime.strptime(formatted_future_date, '%Y%m')
    formatted_ym = datetime.strftime(date_obj, '%Y-%m')

    # 各div要素をループ処理
    for div in divs:

        # 各イベントのdivから必要な情報を抽出
        a_tag = div.find('a', class_='m--scone__a')
        if not a_tag:
            continue
        
        category = div.find('p', class_='m--scone__cat__name')
        title = div.find('p', class_='m--scone__ttl')
        time_info = div.find('p', class_='m--scone__st')
        link = a_tag['href']

        #誕生日の場合親要素から日付情報を取得
        if category.text.strip().replace('<br/>', ' ') == "誕生日":
            day = extract_date_from_parent(div)
        else:
            # リンクから日付情報を解析
            query_params = parse_qs(urlparse(link).query)
            day = query_params.get('wd02', [''])[0]


        date_str = f"{formatted_ym}-{day}"
        date =datetime.strptime(date_str, '%Y-%m-%d').date()

        # 各情報が存在するかチェックし、存在しない場合は適切に処理
        event_info = {
            "category": category.text.strip().replace('<br/>', ' ') if category else "No Category",
            "title": title.text.strip() if title else "No Title",
            "time": time_info.text.strip() if time_info else "All day",
            "link": link,
            "date": date
        }

        # イベント情報をメインのリストに追加
        events.append(event_info)

    return events

def adjust_over_midnight_time(time_str, date):
    # イベント時刻が24:00以上の場合、時間を24で割った余りと日付を繰り上げ
    hours, minutes = map(int, time_str.split(':'))
    if hours >= 24:
        hours -= 24
        date += timedelta(days=1)
    return datetime.combine(date, datetime.strptime(f"{hours}:{minutes}", "%H:%M").time())

#Googleカレンダー形式に変換する関数
def format_event_for_google_calendar(event):
    # タイムゾーンの設定
    timezone = pytz.timezone("Asia/Tokyo")

    # イベント開始と終了時間をパース
    if "time" in event and event["time"] != "All day":
        time_parts = event["time"].split("〜")
        start_time_str = time_parts[0]
        start_datetime = adjust_over_midnight_time(start_time_str, event["date"])

        # 終了時刻が記載されているか確認
        if len(time_parts) > 1 and time_parts[1]:
            end_time_str = time_parts[1]
            end_datetime = adjust_over_midnight_time(end_time_str, event["date"])
            end_time_provided = True
        else:
            # 終了時刻が記載されていない場合、1時間後を仮定
            end_datetime = start_datetime + timedelta(hours=1)
            end_time_provided = False


        # タイムゾーンを適用
        start_datetime = timezone.localize(start_datetime)
        end_datetime = timezone.localize(end_datetime)

        # Google カレンダー形式のイベントデータを作成
        description = f"カテゴリー: {event['category']} Link: {event['link']}"
        #終了時間が未定の場合、説明文に追記
        if not end_time_provided:
            description += " (終了時間未定)"

        google_event = {
            "summary": event["title"],
            "location": "",
            "description": description,
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": "Asia/Tokyo"
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "Asia/Tokyo"
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 30}
                ]
            }
        }
    else:
        # 終日イベントの場合
        start_date = event["date"]
        end_date = start_date + timedelta(days=1)  # 終日イベントの終了日は次の日の0:00とする

        google_event = {
            "summary": event["title"],
            "location": "",
            "description": f"Category: {event['category']} Link: {event['link']}",
            "start": {
                "date": start_date.strftime('%Y-%m-%d'),
            },
            "end": {
                "date": end_date.strftime('%Y-%m-%d'),
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 30}
                ]
            }
        }

    return google_event


def get_nogizaka_schedule(n_month):
    #乃木坂の公式ホームページのURL
    base_url = "https://www.nogizaka46.com/s/n46/media/list?"
    #Scraperクラスのインスタンスを作成
    nogizaka =Scraper(base_url)

    formatted_future_date = get_formatted_date_n_months_later(n_month, '%Y%m')

    soup = nogizaka.fetch_schedule(formatted_future_date)
    # イベントごとのHTMLをリストに格納
    divs = soup.find_all('div', class_='m--scone')

    # イベント情報の抽出
    events = extract_event(divs,formatted_future_date)
    # Google カレンダー形式に変換
    google_events = [format_event_for_google_calendar(event) for event in events]

    #ドライバーを閉じる
    nogizaka.close()
    return google_events

if __name__ == "__main__":
    # 3ヶ月後のイベント情報を取得
    num_month =3
    events = get_nogizaka_schedule(num_month)
    print(events)