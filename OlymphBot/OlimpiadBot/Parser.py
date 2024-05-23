from datetime import datetime, timedelta
import pycurl
from urllib.parse import urlencode
import json
from io import BytesIO
from bs4 import BeautifulSoup
import certifi


class HTMLParser:
    def __init__(self):
        self.__url = 'https://postypashki.ru/wp-admin/admin-ajax.php'

    def __post_req(self):
        month = datetime.now().month - 2

        crl = pycurl.Curl()
        crl.setopt(crl.URL, self.__url)

        post_body = {
            'action': 'ecwd_ajax',
            'ecwd_calendar_ids': '64',
            'ecwd_type': 'page',
            'ecwd_query': '',
            'ecwd_displays': 'full,list',
            'ecwd_prev_display': 'list',
            'ecwd_page_items': '150',
            'ecwd_event_search': 'yes',
            'ecwd_date': '1',
            'ecwd_date_filter': f'2024-{month}',
            'ecwd_nonce': '42f5dd1a6b'
        }
        post_data = urlencode(post_body)
        crl.setopt(crl.POSTFIELDS, post_data)
        crl.setopt(crl.HTTPHEADER, [
            'authority: postypashki.ru',
            'accept: */*',
            'accept-language: ru,en;q=0.9',
            'content-type: application/x-www-form-urlencoded; charset=UTF-8',
            'cookie: beget=begetok',
            'origin: https://postypashki.ru',
            'referer: https://postypashki.ru/ecwd_calendar/calendar/',
            'sec-ch-ua: "Not_A Brand";v="8", "Chromium";v="120", "YaBrowser";v="24"',
            'sec-ch-ua-mobile: ?0',
            'sec-ch-ua-platform: "Linux"',
            'sec-fetch-dest: empty',
            'sec-fetch-mode: cors',
            'sec-fetch-site: same-origin',
            'user-agent: PycURL',
            'x-requested-with: XMLHttpRequest'
        ])

        buffer = BytesIO()
        crl.setopt(crl.WRITEDATA, buffer)

        crl.setopt(crl.CAINFO, certifi.where())

        crl.perform()
        crl.close()

        body = buffer.getvalue()
        return body.decode('iso-8859-1')

    def get_events(self):
        parsed = BeautifulSoup(self.__post_req(), features='html.parser')
        events_raw = parsed.find(id='ecwd_ld_json').string
        events = json.loads(events_raw)
        return events

