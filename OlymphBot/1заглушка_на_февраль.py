import time
import telebot
from telebot import types
from threading import Thread
from bs4 import BeautifulSoup
import pycurl
import certifi
from io import BytesIO
from urllib.parse import urlencode
import json
from datetime import datetime, timedelta
import schedule
import re
from mysql.connector import connect, Error


class HTMLParser:
    def __init__(self):
        self.__url = 'https://postypashki.ru/wp-admin/admin-ajax.php'

    def __post_req(self):
        month = datetime.now().month - 3

        crl = pycurl.Curl()
        crl.setopt(crl.URL, self.__url)

        post_body = {
            'action': 'ecwd_ajax',
            'ecwd_calendar_ids': '64',
            # 'ecwd_link': '?date=2024-3-11&t=list',
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


class MysqlConnector:
    def __init__(self):
        self.__host = 'localhost'
        self.__user = 'root'
        self.__password = 'QW15aszx'
        self.__database = 'olimpiadych'
        self.__subjects = [
            'физика',
            'информатика',
            'информационная безопасность',
            'математика'
        ]

    def __query(self, q):
        try:
            with connect(
                    host=self.__host,
                    user=self.__user,
                    password=self.__password,
                    database=self.__database
            ) as connection:
                # print(connection)
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(q)
                    result = cursor.fetchall()
                    connection.commit()
                connection.commit()
                cursor.close()
                connection.close()
                return result
        except Error as e:
            print(e)
            return

    def max_id(self, table):
        query = f'SELECT * FROM {table} ORDER BY id DESC LIMIT 0, 1;'
        result = self.__query(query)
        if result:
            return result[0]['id'] + 1
        else:
            return 0

    def get_events(self, date_start=datetime.now() - timedelta(days=90), date_delta=None):
        date_end = f' AND date_start < "{date_start + timedelta(days=date_delta)}"' if date_delta else ''
        date_start = f'WHERE date_start > "{date_start.strftime("%Y-%m-%d")}"' if date_start else ''
        query = (f'SELECT * FROM events '
                 f'{date_start}{date_end} ORDER BY date_start;')
        result = self.__query(query)
        return result

    def new_events(self, events):
        old_events = [
            [f'"{value}"' for key, value in event.items() if key != 'id'] for event in self.get_events(None)
        ]
        print(old_events)
        pattern = r"\(([А-Яа-яA-Za-z0-9_ ]+)\)"

        def event_formatter(event):
            name_raw = event['name'].replace('–', '-')
            type_raw = re.search(pattern, event["name"])
            name_formatted = name_raw if (
                    type_raw is None or type_raw.group(1) not in self.__subjects) else (
                " ".join(name_raw.replace(type_raw.group(0), "").split()))
            organizer, name = list(
                map(
                    lambda x: f'"{x.strip()}"',
                    filter(
                        lambda x: x.strip(),
                        re.split(r"-|–", name_formatted)
                    )
                )
            )
            event_type = '"None"' if type_raw is None or type_raw.group(1) not in self.__subjects else (
                f'"{type_raw.group(1)}"')
            date_start = f'"{datetime.strptime(event["startDate"], "%Y-%m-%d %H:%M")}"'
            date_end = f'"{datetime.strptime(event["endDate"], "%Y-%m-%d %H:%M")}"'
            return [organizer, name, event_type, date_start, date_end]

        events = [", ".join(event_formatter(event)) for event in events if event_formatter(event) not in old_events]
        print(events)
        if events:
            query = (f'INSERT INTO events (organizer, name, type, date_start, date_end) '
                     f'VALUES '
                     f'ROW({"), ROW(".join(events)});')
            self.__query(query)
            print(query)

    def get_users(self, id=None):
        where = '' if id is None else f" WHERE chat_id = {id}"
        query = f'SELECT * FROM users{where};'
        result = self.__query(query)
        return result

    def new_user(self, id):
        old_users = [user['chat_id'] for user in self.get_users()]
        if id in old_users:
            return
        query = (f'INSERT INTO users (chat_id) VALUES '
                 f'({id});')
        self.__query(query)

    def subscribe(self, id, delta):
        query = (f'UPDATE users '
                 f'SET subscribed = 1, delta = {delta} '
                 f'WHERE chat_id = {id};')
        self.__query(query)

    def add_sent(self, id, events):
        query = (f'SELECT * FROM users '
                 f'WHERE chat_id = {id};')
        old_events = json.loads(self.__query(query)[0]['sent'])
        if not old_events:
            old_events = []
        query = (f'UPDATE users '
                 f'SET sent = "{old_events + events}" '
                 f'WHERE chat_id = {id};')
        self.__query(query)


class Bot:
    def __init__(self, mysql):
        self.__mysql = mysql
        self.bot = telebot.TeleBot('7111330805:AAF2pmwgIj-1NzUfXH0aVwp1zQ1YposVpl8')

        self.__months = ['Января', 'Февраля', 'Марта', 'Апреля', 'Мая', 'Июня',
                         'Июля', 'Августа', 'Сентября', 'Октября', 'Ноября', 'Декабря']

        deltas = {
            "1 день": 1,
            "3 дня": 3,
            "Неделя": 7
        }

        self.__menu_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_olympiad = types.KeyboardButton("Олимпиады")
        btn_mailing = types.KeyboardButton("Рассылка")
        self.__menu_markup.add(btn_olympiad, btn_mailing)

        self.__mailing_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_1 = types.KeyboardButton("1 день")
        btn_2 = types.KeyboardButton("3 дня")
        btn_3 = types.KeyboardButton("Неделя")
        self.__mailing_markup.row(btn_1, btn_2)
        self.__mailing_markup.row(btn_3)

        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            mysql.new_user(message.chat.id)
            self.bot.send_message(message.chat.id, 'йоу пчелл', reply_markup=self.__menu_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'олимпиады')
        def olympiads(message):
            events = mysql.get_events()

            msg = '\n'.join([self.event_formatter(event) for event in events])
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__menu_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'рассылка')
        def olympiads(message):
            msg = f'Выберите за какое время до отсылатиь хз'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__mailing_markup)

        @self.bot.message_handler(func=lambda msg: msg.text in deltas)
        def olympiads(message):
            mysql.subscribe(message.chat.id, deltas[message.text])
            msg = 'вы подписаны хз'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__menu_markup)
            self.send_notify(message.chat.id)

    def event_formatter(self, event):
        event_type = f' - {event["type"]}' if event['type'] != 'None' else ''
        date = event["date_start"]
        event_day = f'{date.strftime("%d")} {self.__months[int(date.strftime("%m")) - 1]}'
        event_time = f' {date.strftime("%H:%M")} - {event["date_end"].strftime("%H:%M")}' if (
                date.strftime("%H") != '00') else ''

        return (f'{event["organizer"]} - {event["name"]}{event_type}\n'
                f'{event_day}{event_time}\n')

    def start(self):
        schedule.every().day.at('09:00').do(self.send_notify)

        self.bot.infinity_polling()

    def send_notify(self, id=None):
        users = self.__mysql.get_users(id)
        events = self.__mysql.get_events()

        for user in users:
            sent = json.loads(user['sent'])
            if not sent:
                sent = []
            new_sent = []
            for event in events:
                if event['id'] not in sent:
                    delta = event['date_start'] - datetime.now() + timedelta(days=90)
                    if delta.days < user['delta']:
                        new_sent.append(event['id'])
                        msg = (f'{"Осталось" if delta.days > 1 else "Остался"} {delta.days} '
                               f'{"дней" if delta.days > 4 else "дня" if delta.days > 1 else "день"} '
                               f'до олимпиады:\n') if delta.days != 0 else "Сегодня!\n"
                        msg += f'{self.event_formatter(event)}'
                        self.bot.send_message(user['chat_id'], msg, reply_markup=self.__menu_markup)
            # self.__mysql.add_sent(user['chat_id'], new_sent)


def update_base(parser, mysql):
    print(mysql.get_events())
    events = parser.get_events()
    print(events)
    mysql.new_events(events)


def event_scheduler(mysql):
    parser = HTMLParser()

    update_base(parser, mysql)
    schedule.every().day.at('00:00').do(update_base, parser, mysql)
    # schedule.every(10).seconds.do(update_base, parser, mysql)

    while True:
        schedule.run_pending()
        time.sleep(1)


def main():
    mysql = MysqlConnector()
    bot = Bot(mysql)

    bot_thread = Thread(target=bot.start, args=())
    scheduler_thread = Thread(target=event_scheduler, args=(mysql,))

    # create_bot(mysql)

    bot_thread.start()
    scheduler_thread.start()


if __name__ == '__main__':
    main()
