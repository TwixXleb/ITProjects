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

    def get_events(self, date_start=datetime.now() - timedelta(days=90), date_delta=None, subject=None):
        date_end = f'date_start < "{date_start + timedelta(days=date_delta)}"' if date_delta else ''
        date_start = f'date_start > "{date_start.strftime("%Y-%m-%d")}"' if date_start else ''
        subject_filter = f'type = "{subject}"' if subject else ''
        filters = list(filter(lambda x: x, [date_start, date_end, subject_filter]))
        query = (f'SELECT * FROM events '
                 f'{"WHERE " if filters else ""}'
                 f'{" AND ".join(filters)} ORDER BY date_start;')
        result = self.__query(query)
        return result

    def get_subjects(self):
        return self.__subjects

    def new_events(self, events):
        old_events = [
            [f'"{value}"' for key, value in event.items() if key != 'id'] for event in self.get_events()
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
        query = (f'INSERT INTO users (chat_id, subjects, organizers, sent) VALUES '
                 f'({id}, "[]", "[]", "[]");')
        self.__query(query)

    def subscribe(self, id, delta):
        query = (f'UPDATE users '
                 f'SET subscribed = 1, delta = {delta} '
                 f'WHERE chat_id = {id};')
        self.__query(query)

    def user_subject(self, id, subj):
        query = (f'SELECT subjects '
                 f'FROM users '
                 f'WHERE chat_id = {id};')
        user_subjects = json.loads(self.__query(query)[0]['subjects'])
        action = 1 if subj in user_subjects else 0
        user_subjects.remove(subj) if action else user_subjects.append(subj)
        query = (f'UPDATE users '
                 f"SET subjects = '{json.dumps(user_subjects, ensure_ascii=False)}' "
                 f'WHERE chat_id = {id};')
        self.__query(query)
        return action

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
        self.__menu_markup.row(btn_olympiad, btn_mailing)

        self.__mailing_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_1 = types.KeyboardButton("Настроить за какое время получать уведомления")
        btn_2 = types.KeyboardButton("Выбрать предметы")
        btn_3 = types.KeyboardButton("Выбрать конкретные олимпиады")
        btn_4 = types.KeyboardButton("Меню")
        self.__mailing_markup.row(btn_1)
        self.__mailing_markup.row(btn_2)
        self.__mailing_markup.row(btn_3)
        self.__mailing_markup.row(btn_4)

        self.__olymp_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_1 = types.KeyboardButton("Фильтр по предметам")
        btn_2 = types.KeyboardButton("---")
        btn_3 = types.KeyboardButton("---")
        btn_4 = types.KeyboardButton("Меню")
        self.__olymp_markup.row(btn_1)
        self.__olymp_markup.row(btn_2)
        self.__olymp_markup.row(btn_3)
        self.__olymp_markup.row(btn_4)

        self.__olymp_filter_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_1 = types.KeyboardButton("По предмету физика")
        btn_2 = types.KeyboardButton("По предмету информатика")
        btn_3 = types.KeyboardButton("По предмету математика")
        btn_4 = types.KeyboardButton("По предмету информационная безопасность")
        btn_5 = types.KeyboardButton("Меню")
        self.__olymp_filter_markup.row(btn_1, btn_2, btn_3)
        self.__olymp_filter_markup.row(btn_5, btn_4)

        self.__deltas_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_1 = types.KeyboardButton("1 день")
        btn_2 = types.KeyboardButton("3 дня")
        btn_3 = types.KeyboardButton("Неделя")
        self.__deltas_markup.row(btn_1, btn_2)
        self.__deltas_markup.row(btn_3)

        self.__subj_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_1 = types.KeyboardButton("Физика")
        btn_2 = types.KeyboardButton("Информатика")
        btn_3 = types.KeyboardButton("Математика")
        btn_4 = types.KeyboardButton("Информационная Безопасность")
        btn_5 = types.KeyboardButton("Меню")
        self.__subj_markup.row(btn_1, btn_2, btn_3)
        self.__subj_markup.row(btn_4, btn_5)

        @self.bot.message_handler(commands=['start', 'help'])
        def send_welcome(message):
            mysql.new_user(message.chat.id)
            self.bot.send_message(message.chat.id, 'йоу пчелл', reply_markup=self.__menu_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'олимпиады')
        def olympiads(message):
            events = mysql.get_events()

            msg = '\n'.join([self.event_formatter(event) for event in events])
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__olymp_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'фильтр по предметам')
        def mailing(message):
            msg = f'Выберите по какому предмету остортировать'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__olymp_filter_markup)

        @self.bot.message_handler(
            func=lambda msg: msg.text.lower() in list(map(lambda x: f'по предмету {x}', mysql.get_subjects()))
        )
        def olympiads(message):
            subject = message.text.split()[2]
            print(subject)
            events = mysql.get_events(subject=subject)

            msg = '\n'.join([self.event_formatter(event) for event in events])
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__olymp_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'рассылка')
        def mailing(message):
            msg = f'Выберите опцию'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__mailing_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'настроить за какое время получать уведомления')
        def select_delta(message):
            msg = f'За сколько дней до лимпиады вы бы хотели получать уведомления?'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__deltas_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'выбрать предметы')
        def select_subj(message):
            user = mysql.get_users(message.chat.id)[0]
            user_subjects = json.loads(user['subjects'])
            msg = (f'Выберете предметы, уведомления о '
                   f'олимпиадах по которым вам будут приходить') if not user_subjects \
                else (f'На данный момент вы подписанны на уведомления о олимпиадах '
                      f'{"по таким предметам, как " if len(user_subjects) > 1 else "по предмету "}'
                      f'{", ".join(user_subjects)}\n'
                      f'Вы можете выбрать предмет, на который хотели бы подписаться или же отписаться')
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__subj_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() in mysql.get_subjects())
        def subj(message):
            # mysql.subscribe(message.chat.id, deltas[message.text])
            action = mysql.user_subject(message.chat.id, message.text.lower())
            user = mysql.get_users(message.chat.id)[0]
            user_subjects = json.loads(user['subjects'])
            msg = f'{"Вы отписались от предмета " if action else "Вы подписались на предмет "}{message.text}\n'
            msg += (f'На данный момент вы подписанны на уведомления о олимпиадах '
                    f'{"по таким предметам, как " if len(user_subjects) > 1 else "по предмету "}'
                    f'{", ".join(user_subjects)}\n') if user_subjects else ''
            msg += f'Вы можете выйти в меню или же выбрать предмет, на который хотели бы подписаться или отписаться'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__subj_markup)

        @self.bot.message_handler(func=lambda msg: msg.text in deltas)
        def deltas_chose(message):
            mysql.subscribe(message.chat.id, deltas[message.text])
            msg = 'вы подписаны хз'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__menu_markup)
            self.send_notify(message.chat.id)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'меню')
        def menu(message):
            msg = 'Вы можете посмотреть список следующих олимпиад или же подписаться на уведомления о ближайших'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__menu_markup)

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
