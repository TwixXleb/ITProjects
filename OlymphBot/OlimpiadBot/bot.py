import telebot
from telebot import types
import json
import schedule


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

        self.__num_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        btn_menu = types.KeyboardButton("Меню")
        self.__num_markup.row(btn_olympiad, btn_menu)

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
        btn_2 = types.KeyboardButton("Фильтр по организатору")
        btn_4 = types.KeyboardButton("Меню")
        self.__olymp_markup.row(btn_1)
        self.__olymp_markup.row(btn_2)
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
            msg = ('Здраствуйте!\n'
                   'Вы можете посмотреть список следующих олимпиад или же подписаться на уведомления о ближайших')
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__menu_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'олимпиады')
        def olympiads(message):
            events = mysql.get_events()

            msg = '\n'.join([self.event_formatter(event) for event in events])
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__olymp_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'фильтр по предметам')
        def subj_filter(message):
            msg = f'Выберите по какому предмету остортировать'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__olymp_filter_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'фильтр по организатору')
        def org_filter(message):
            mysql.set_action(message.chat.id, 'olymp_org')
            new_line = '\n'
            msg = (f'Напишите номер организатора:\n'
                   f'{new_line.join(map(lambda x: f"{x[0] + 1}. {x[1]}", enumerate(mysql.get_organizers())))}')
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__num_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.isdigit() and mysql.get_action(msg.chat.id) == 'olymp_org')
        def olympiads_org_filtered(message):
            if int(message.text) > len(mysql.get_organizers()):
                self.bot.send_message(message.chat.id, "Неверный номер", reply_markup=self.__olymp_markup)
                return
            org_number = int(message.text) - 1
            events = mysql.get_events(organizer=mysql.get_organizers()[org_number])
            if events:
                msg = '\n'.join([self.event_formatter(event) for event in events])
            else:
                msg = "В ближайшее время этот организатор не будет проводить олимпиады"
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__olymp_markup)

        @self.bot.message_handler(
            func=lambda msg: msg.text.isdigit() and mysql.get_action(msg.chat.id) == 'mailing_spec'
        )
        def mailing_spec_filtered(message):
            if int(message.text) > len(mysql.get_events()):
                self.bot.send_message(message.chat.id, "Неверный номер", reply_markup=self.__olymp_markup)
                return
            mysql.set_user_mailing(message.chat.id, 'spec')
            event_number = int(message.text) - 1
            event = mysql.get_events()[event_number]
            action = mysql.user_spec_notify(message.chat.id, event['id'])
            msg = (f'Вы {"удалили" if action else "добавили"} олимпиаду '
                   f'в список тех, о которых вам буду приходить уведомления')
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__mailing_markup)

        @self.bot.message_handler(
            func=lambda msg: msg.text.lower() in list(map(lambda x: f'по предмету {x}', mysql.get_subjects()))
        )
        def olympiads_subj_filtered(message):
            subject = message.text.split()[2]
            events = mysql.get_events(subject=subject)

            msg = '\n'.join([self.event_formatter(event) for event in events])
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__olymp_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'рассылка')
        def mailing(message):
            msg = f'Выберите опцию'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__mailing_markup)

        @self.bot.message_handler(func=lambda msg: msg.text.lower() == 'выбрать конкретные олимпиады')
        def individual_mailing(message):
            mysql.set_action(message.chat.id, 'mailing_spec')
            events = mysql.get_events()
            nl = '\n'
            msg = (f'Напишите номер олимпиады, уведомления о которой вы бы хотели получать\n'
                   f'{nl.join(map(lambda x: f"{x[0] + 1}. {self.event_formatter(x[1])}", enumerate(events)))}')

            self.bot.send_message(message.chat.id, msg, reply_markup=self.__num_markup)

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
            action = mysql.user_subject(message.chat.id, message.text.lower())
            user = mysql.get_users(message.chat.id)[0]
            user_subjects = json.loads(user['subjects'])
            mysql.set_user_mailing(message.chat.id, 'subj')
            msg = f'{"Вы отписались от предмета " if action else "Вы подписались на предмет "}{message.text}\n'
            msg += (f'На данный момент вы подписанны на уведомления о олимпиадах '
                    f'{"по таким предметам, как " if len(user_subjects) > 1 else "по предмету "}'
                    f'{", ".join(user_subjects)}\n') if user_subjects else ''
            msg += f'Вы можете выйти в меню или же выбрать предмет, на который хотели бы подписаться или отписаться'
            self.bot.send_message(message.chat.id, msg, reply_markup=self.__subj_markup)

        @self.bot.message_handler(func=lambda msg: msg.text in deltas)
        def deltas_chose(message):
            mysql.subscribe(message.chat.id, deltas[message.text])
            msg = f'Теперь вы будете получать уведомления о олимпиадах за {message.text}'
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
                    if user['selected_mailing'] == 'subj':
                        user_subjects = json.loads(user['subjects'])
                        if user_subjects:
                            if event['type'] not in user_subjects:
                                continue
                    if user['selected_mailing'] == 'spec':
                        user_specs = json.loads(user['spec_notification'])
                        if user_specs:
                            if event['id'] not in user_specs:
                                continue
                    delta = event['date_start'] - datetime.now() + timedelta(days=90)
                    if delta.days < user['delta']:
                        new_sent.append(event['id'])
                        msg = (f'{"Осталось" if delta.days > 1 else "Остался"} {delta.days} '
                               f'{"дней" if delta.days > 4 else "дня" if delta.days > 1 else "день"} '
                               f'до олимпиады:\n') if delta.days != 0 else "Сегодня!\n"
                        msg += f'{self.event_formatter(event)}'
                        self.bot.send_message(user['chat_id'], msg, reply_markup=self.__menu_markup)