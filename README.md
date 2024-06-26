# ITProjects

## Проект 1: Telegram Бот для Уведомлений об Олимпиадах

### Структура проекта

Проект структурирован следующим образом:
```
project/
├── .idea/		# Папка с конфигурационными файлами проекта для IDE
│    ├──.gitignore           
├── .venv/                 # Виртуальное окружение для проекта
├── pycache/           # Папка с скомпилированными файлами Python
├── bot.py                 # Основной файл с реализацией Telegram бота
├── config.py              # Файл с конфигурационными данными
├── main.py                # Главный файл для запуска проекта
├── MySQLConnector.py      # Файл с реализацией подключения и работы с базой данных MySQL
├── Parser.py		# Файл с реализацией парсера HTML
└── requirements.txt		# Файл с библиотеками для Python 
```
### Функциональные требования

1. Бот Telegram:
   - Приветственное сообщение при команде /start.
   - Отображение списка ближайших олимпиад по запросу.
   - Фильтрация олимпиад по предметам и организаторам.
   - Настройка уведомлений о предстоящих олимпиадах.

2. Парсер HTML:
   - Отправка POST-запросов к веб-странице для получения данных об олимпиадах.
   - Парсинг и возврат списка олимпиад.

3. Работа с базой данных:
   - Подключение к базе данных MySQL.
   - Хранение данных об олимпиадах и пользователях.
   - CRUD операции для управления данными.

4. Планировщик задач:
   - Автоматическое обновление базы данных с расписанием олимпиад.
   - Ежедневная отправка уведомлений пользователям о предстоящих событиях.

### Используемый стек

- Язык программирования: Python
- Библиотеки и фреймворки:
  - telebot для создания Telegram бота.
  - BeautifulSoup для парсинга HTML.
  - pycurl для выполнения HTTP-запросов.
  - mysql.connector для работы с базой данных MySQL.
  - schedule для планирования задач.
  - logging для логирования событий.
- База данных: MySQL
- Виртуальное окружение: virtualenv или conda

### Установка и запуск

1. Клонирование репозитория:
   ```
   git clone https://github.com/TwixXleb/ITProjects.git
   cd ITProjects
   ```

2. Создание виртуального окружения:
   ```
   python -m venv venv
   source venv/bin/activate  # Для Windows: venv\Scripts\activate
   ```

3. Установка зависимостей:
   ```
   pip install -r requirements.txt
   ```

4. Настройка базы данных:
   - Создайте базу данных MySQL и заполните конфигурационные данные в config/config.py.

5. Запуск проекта:
   ```
   python main.py
   ```

### Гифка с примером работы проектом

![Gif Project](https://github.com/TwixXleb/ITProjects/blob/main/Img/ProgGif.gif)

### Ссылка на доску

[KuryagiTable](https://team-9zz0qfts6zno.atlassian.net/jira/software/projects/KUR/boards/2?atlOrigin=eyJpIjoiMTA4ZDg0ZThhYzFjNDYyMTkxN2Q5OTZhMmRlN2FmMjgiLCJwIjoiaiJ9)

