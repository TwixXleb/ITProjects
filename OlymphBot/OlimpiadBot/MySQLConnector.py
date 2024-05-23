from mysql.connector import connect, Error
from datetime import datetime, timedelta
import json
import re
import config as c


class MysqlConnector:
    def __init__(self):
        self.__subjects = [
            'физика',
            'информатика',
            'информационная безопасность',
            'математика'
        ]
        self.__organizers = [
            "Газпром",
            "ОРМО",
            "Innopolis Open",
            "Олимпиада им. Верченко",
            "Изумруд",
            "СПбАстро",
            "Олимпиада ИТМО",
            "Всесиб",
            "ММО",
            "Мосастро",
            "Барсик",
            "ИТМО",
            "МОШ",
            "ОММО",
            "Когнитивные технологии",
            "ШВБ",
            "Высшая проба",
            "Ломоносов",
            "Физтех (фиизка)",
            "Физтех (математик)",
            "Межвед",
            "СПбГУ",
            "Росатом",
            "САММАТ"
        ]

    @staticmethod
    def __query(q):
        try:
            with connect(
                    host=c.HOST,
                    user=c.USER,
                    password=c.PASSWORD,
                    database=c.DATABASE
            ) as connection:
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

    def get_events(self, date_start=datetime.now() - timedelta(days=90), date_delta=None, subject=None, organizer=None):
        date_end = f'date_start < "{date_start + timedelta(days=date_delta)}"' if date_delta else ''
        date_start = f'date_start > "{date_start.strftime("%Y-%m-%d")}"' if date_start else ''
        subject_filter = f'type = "{subject}"' if subject else ''
        org_filter = f'organizer = "{organizer}"' if organizer else ''
        filters = list(filter(lambda x: x, [date_start, date_end, subject_filter, org_filter]))
        query = (f'SELECT * FROM events '
                 f'{"WHERE " if filters else ""}'
                 f'{" AND ".join(filters)} ORDER BY date_start;')
        result = self.__query(query)
        return result

    def get_subjects(self):
        return self.__subjects

    def get_organizers(self):
        return self.__organizers

    def new_events(self, events):
        old_events = [
            [f'"{value}"' for key, value in event.items() if key != 'id'] for event in self.get_events(None)
        ]
        print('old events ', old_events)
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
        query = (f'INSERT INTO users (chat_id, subjects, organizers, sent, spec_notification) VALUES '
                 f'({id}, "[]", "[]", "[]", "[]");')
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

    def set_action(self, id, action):
        query = (f'UPDATE users '
                 f'SET action = "{action}" '
                 f'WHERE chat_id = {id};')
        self.__query(query)

    def get_action(self, id):
        query = (f'SELECT * '
                 f'FROM users '
                 f'WHERE chat_id = {id};')
        return self.__query(query)[0]['action']

    def user_spec_notify(self, id, event_id):
        query = (f'SELECT * '
                 f'FROM users '
                 f'WHERE chat_id = {id};')
        user = self.__query(query)[0]
        user_ids = json.loads(user['spec_notification'])
        action = event_id in user_ids
        user_ids.remove(event_id) if action else user_ids.append(event_id)
        query = (f'UPDATE users '
                 f'SET spec_notification = "{json.dumps(user_ids)}" '
                 f'WHERE chat_id = {id};')
        self.__query(query)
        return action

    def set_user_mailing(self, id, mailing_type):
        query = (f'UPDATE users '
                 f'SET selected_mailing = "{mailing_type}" '
                 f'WHERE chat_id = {id};')
        self.__query(query)