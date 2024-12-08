Aiogram3 bot Application

Приложение предназначено для создания на лету директорий и загрузки на локальный сервер хешированных файлов посредством Telegram, а так же дальнейшего просмотра загруженных в директории фото. Использует PostgreSQL в качестве базы данных.

Перед тем как начать, убедитесь, что у вас установлены следующие компоненты:

Python (версия 3.11+)
PostgreSQL (версия 14+)
pip
virtualenv (опционально)

Установка

python -m venv venv
source venv/bin/activate # Для macOS/Linux
venv\Scripts\activate # Для Windows

Установите зависимости:

pip install -r requirements.txt

Настройте базу данных: Создайте базу данных в PostgreSQL и обновите настройки в .env вашего проекта:

API_TOKEN = 'TOKEN' 
host='host' 
port="port" 
user="user" 
password="password" 
database="database" 
DATABASE_URL='path_to_database'

##Запуск приложения 
##Чтобы запустить приложение, выполните следующую команду: python3 app.py
