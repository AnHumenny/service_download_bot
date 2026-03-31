import os
import hashlib
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'dbname': os.getenv('database'),
    'user': os.getenv('user'),
    'password': os.getenv('password'),
    'host': os.getenv('host'),
    'port': os.getenv('port')
}

def hashing_password(password: str) -> str:
    """hashing password."""
    return hashlib.sha256(password.encode()).hexdigest()

def add_user(login, name, status, password, phone, email, tg_id):
    pswrd = hashing_password(password)
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        insert_query = '''
        INSERT INTO _userbot(login, name, status, password, phone, email, tg_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        '''
        cursor.execute(insert_query, (login, name, status, pswrd, phone, email, tg_id))
        conn.commit()
        print("Пользователь добавлен успешно!")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    add_user(
        login="q",
        name = "vih",
        status = "admin",
        password = "q",
        phone = "333333",
        email = "email@email.com",
        tg_id = "408395"
    )