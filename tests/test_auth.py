import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
import app.models as models
from app.auth import hash_password

# База данных в оперативной памяти с поддержкой общего кэша
TEST_DATABASE_URL = 'sqlite:///file:test_diary_db?mode=memory&cache=shared&uri=true'

engine = create_engine(TEST_DATABASE_URL, connect_args={'check_same_thread': False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name='session')
def session_fixture():
    '''Фикстура, которая создает таблицы перед каждым тестом и чистит их после.'''
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name='client')
def client_fixture(session):
    '''Фикстура клиента, переопределяющая get_db.'''
    def override_get_db():
        try:
            yield session
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- СУЩЕСТВУЮЩИЕ ТЕСТЫ ---

def test_main_page_returns_guest_status(client):
    '''Проверяем, что неавторизованный пользователь видит статус Гость.'''
    response = client.get('/api/')
    assert response.status_code == 200
    assert 'Гость' in str(response.json())


def test_user_registration_success(client):
    '''Проверяем успешную регистрацию нового аккаунта.'''
    payload = {'email': 'tester@i.ua', 'password': 'safe_password_123'}
    response = client.post('/api/register', data=payload)
    assert response.status_code == 200
    assert '/login' in str(response.json())


# --- НОВЫЕ СВЕРХВАЖНЫЕ ТЕСТЫ ДЛЯ ПРОДАКШЕНА ---

def test_user_login_success_sets_cookie(client, session):
    '''Проверяем, что при успешном входе бэкенд выдает Cookie-сессию.'''
    # Создаем пользователя в тестовой БД вручную
    hashed = hash_password('correct_pass')
    db_user = models.User(email='user@test.ru', hashed_password=hashed)
    session.add(db_user)
    session.commit()

    # Отправляем форму входа
    payload = {'email': 'user@test.ru', 'password': 'correct_pass'}
    response = client.post('/api/login', data=payload)
    
    assert response.status_code == 200
    # Проверяем, что бэкенд скомандовал браузеру записать нашу куку кук!
    assert 'diary_session' in response.cookies


def test_hidden_action_routes_block_guest(client):
    '''Проверяем защиту роутов: гость не может отправить заметку в архив.'''
    # Пытаемся дернуть архив напрямую без куки
    response = client.get('/api/note/1/archive-run')
    assert response.status_code == 200
    # Наша защита должна перенаправить взломщика на форму входа
    assert '/login' in str(response.json())


def test_admin_page_access_control(client, session):
    '''Проверяем права доступа к админке /users с корректной проверкой JSON.'''
    # Устанавливаем тестовую переменную окружения, чтобы бэкенд знал, кто тут админ
    os.environ['ADMIN_EMAIL'] = 'admin@test.ru'

    # 1. Создаем обычного пользователя и админа
    hashed = hash_password('pass123')
    simple_user = models.User(email='user@test.ru', hashed_password=hashed)
    admin_user = models.User(email='admin@test.ru', hashed_password=hashed) # Теперь совпадает с ADMIN_EMAIL
    session.add_all([simple_user, admin_user])
    session.commit()

    # 2. Тестируем под обычным юзером
    client.post('/api/login', data={'email': 'user@test.ru', 'password': 'pass123'})
    response = client.get('/api/users')
    
    response_json = response.json()
    assert response.status_code == 200
    
    # ИСПРАВЛЕНО: Добавили, так как FastUI всегда возвращает список компонентов!
    assert response_json[0]['type'] == 'FireEvent'
    assert response_json[0]['event']['url'] == '/'


    # Выходим
    client.get('/api/logout')

    # 3. Тестируем под легальным админом
    client.post('/api/login', data={'email': 'admin@test.ru', 'password': 'pass123'})
    response = client.get('/api/users')
    
    assert 'Управление пользователями' in str(response.json())


def test_create_note_with_category(client, session):
    '''Проверяем, что заметка успешно создается и привязывается к числу-категории.'''
    # 1. Создаем пользователя и его личную категорию в БД
    hashed = hash_password('pass123')
    user = models.User(email='author@i.ua', hashed_password=hashed)
    session.add(user)
    session.commit()

    category = models.Category(name='Спорт', user_id=user.id)
    session.add(category)
    session.commit()

    # 2. Авторизуемся
    client.post('/api/login', data={'email': 'author@i.ua', 'password': 'pass123'})

    # 3. Отправляем POST-запрос создания заметки через нашу форму c.Form
    payload = {
        'title': 'Моя тренировка',
        'content': 'Бег 5 км',
        'category_id': str(category.id)  # Форма шлет ID строкой
    }
    response = client.post('/api/add', data=payload)
    assert response.status_code == 200

    # 4. Проверяем в SQLite, что типы сконвертировались и связь записалась корректно
    db_note = session.query(models.Note).filter(models.Note.title == 'Моя тренировка').first()
    assert db_note is not None
    assert db_note.category_id == category.id
    assert db_note.user_id == user.id
