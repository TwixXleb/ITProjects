import time
from threading import Thread
import schedule
from MySQLConnector import MysqlConnector
from Parser import HTMLParser
from bot import Bot


def update_base(parser, mysql):
    print(mysql.get_events())
    events = parser.get_events()
    print(events)
    mysql.new_events(events)


def event_scheduler(mysql):
    parser = HTMLParser()

    update_base(parser, mysql)
    schedule.every().day.at('00:00').do(update_base, parser, mysql)

    while True:
        schedule.run_pending()
        time.sleep(1)


def main():
    mysql = MysqlConnector()
    bot = Bot(mysql)

    bot_thread = Thread(target=bot.start, args=())
    scheduler_thread = Thread(target=event_scheduler, args=(mysql,))

    bot_thread.start()
    scheduler_thread.start()


if __name__ == '__main__':
    main()
