from fastapi import Response, Request
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

# Официальные компоненты FastUI
from fastui import FastUI, AnyComponent, prebuilt_html
from fastui import components as c
from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from fastui.forms import fastui_form

# Импорты структуры проекта
import app.models as models
from app.database import engine, Base, get_db
from app.auth import hash_password, verify_password
from app.schemas import NoteCreateSchema, NoteReadSchema, UserRegisterSchema, UserLoginSchema
from app.session import set_user_session, get_user_from_session, refresh_user_session


app = FastAPI()

@app.middleware('http')
async def sliding_session_middleware(request: Request, call_next):
    '''Промежуточный слой, который сдвигает срок годности Cookie при каждом клике.'''
    response = await call_next(request)
    
    # ИСПРАВЛЕНО: Если пользователь выходит (/logout), мы ЖЕЛЕЗНО не продлеваем сессию!
    if '/logout' in request.url.path:
        return response
        
    # Для всех остальных страниц (кроме иконок) кука плавно скользит вперед
    if not request.url.path.startswith('/favicon.ico'):
        refresh_user_session(request, response)
        
    return response



# Автоматически создаем таблицы в notes_app.db при старте
Base.metadata.create_all(bind=engine)


@app.get('/api/', response_model=FastUI, response_model_exclude_none=True)
def notes_list_page(
    request: Request,  # <-- ДОБАВИЛИ СЮДА, чтобы читать Cookie
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Главная страница: список активных заметок с динамической авторизацией.'''
    db_notes = (
        db.query(models.Note)
        .filter(models.Note.is_archived == False)
        .order_by(models.Note.created_at.desc())
        .all()
    )
    
    notes_for_table = []
    for note in db_notes:
        pydantic_note = NoteReadSchema.model_validate(note)
        pydantic_note.archive_action = '📦 В архив'
        notes_for_table.append(pydantic_note)

    # 1. Проверяем, авторизован ли пользователь прямо сейчас
    user_id = get_user_from_session(request)
    auth_components = []

    if user_id:
        # Если пользователь вошёл, ищем его email в базе
        user = db.query(models.User).filter(models.User.id == user_id).first()
        user_email = user.email if user else 'Пользователь'
        
        # ИСПРАВЛЕНО: Заменили c.Span на проверенный c.Paragraph с классом d-inline.
        # Теперь Pydantic примет class_name, а текст останется в одну строку с кнопкой!
        auth_components = [
            c.Paragraph(text=f'👤 {user_email}', class_name='text-muted me-2 d-inline'),
            c.Link(components=[c.Text(text='🚪 Выйти')], on_click=GoToEvent(url='/logout'), class_name='btn btn-sm btn-danger')
        ]

    else:
        # Если не вошёл — показываем стандартные кнопки Войти и Регистрация
        auth_components = [
            c.Link(components=[c.Text(text='🔑 Войти')], on_click=GoToEvent(url='/login'), class_name='btn btn-sm btn-warning me-2'),
            c.Link(components=[c.Text(text='👤 Регистрация')], on_click=GoToEvent(url='/register'), class_name='btn btn-sm btn-outline-dark')
        ]

    return [
        c.Page(
            components=[
                c.Heading(text='📝 Мой Дневник & Заметки', level=1),
                
                # Ряд навигации
                c.Link(components=[c.Text(text='📝 Активные записи')], on_click=GoToEvent(url='/'), class_name='btn btn-sm btn-primary me-2'),
                c.Link(components=[c.Text(text='🗂 Открыть архив')], on_click=GoToEvent(url='/archive'), class_name='btn btn-sm btn-secondary me-2'),
                c.Link(components=[c.Text(text='➕ Написать новую заметку')], on_click=GoToEvent(url='/add'), class_name='btn btn-sm btn-success me-4'),
                
                # ВСТАВИЛИ ДИНАМИЧЕСКИЕ КНОПКИ АВТОРИЗАЦИИ
                *auth_components,
                
                c.Div(components=[], class_name='mt-4'),
                c.Heading(text='Ваши записи', level=3) if notes_for_table else c.Paragraph(text='Активных записей нет.'),
                
                c.Table(
                    data=notes_for_table,
                    columns=[
                        DisplayLookup(field='title', title='Название', on_click=GoToEvent(url='/note/{id}')),
                        DisplayLookup(field='created_at', title='Дата создания', mode=DisplayMode.date),
                        DisplayLookup(field='archive_action', title='Действие', on_click=GoToEvent(url='/note/{id}/archive-run')),
                    ]
                ) if notes_for_table else c.Div(components=[])
            ]
        )
    ]


@app.get('/api/register', response_model=FastUI, response_model_exclude_none=True)
def register_page() -> list[AnyComponent]:
    '''Страница с формой регистрации нового пользователя.'''
    return [
        c.Page(
            components=[
                c.Heading(text='🔑 Регистрация нового аккаунта', level=1),
                c.Link(components=[c.Text(text='🔙 На главную')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-3'),
                c.Div(components=[], class_name='mt-4'),
                
                # Автоматическая форма FastUI на основе SecretStr скрывает вводимый пароль точками
                c.ModelForm(model=UserRegisterSchema, submit_url='/api/register')
            ]
        )
    ]


@app.post('/api/register', response_model=FastUI, response_model_exclude_none=True)
def handle_register(
    form: UserRegisterSchema = fastui_form(UserRegisterSchema),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Обработчик регистрации: проверяет уникальность email, хэширует пароль и пишет в SQLite.'''
    # 1. Проверяем, не занят ли почтовый ящик в базе
    existing_user = db.query(models.User).filter(models.User.email == form.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail='Пользователь с таким email уже существует')
    
    # 2. Безопасно хэшируем пароль. Достаем строку из SecretStr через метод get_secret_value()
    hashed_pwd = hash_password(form.password.get_secret_value())
    
    # 3. Сохраняем зашифрованного пользователя
    new_user = models.User(
        email=form.email,
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    
    # После успешной отправки возвращаем пользователя на главную страницу
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/api/archive', response_model=FastUI, response_model_exclude_none=True)
def archive_list_page(db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Страница архива заметок.'''
    db_notes = (
        db.query(models.Note)
        .filter(models.Note.is_archived == True)
        .order_by(models.Note.created_at.desc())
        .all()
    )
    notes_for_table = []
    for note in db_notes:
        pydantic_note = NoteReadSchema.model_validate(note)
        pydantic_note.archive_action = '↩️ Вернуть'
        notes_for_table.append(pydantic_note)

    return [
        c.Page(
            components=[
                c.Heading(text='🗂 Архив записей', level=1),
                c.Link(components=[c.Text(text='📝 Назад к записям')], on_click=GoToEvent(url='/'), class_name='btn btn-sm btn-outline-primary me-2'),
                c.Link(components=[c.Text(text='🗂 Архив')], on_click=GoToEvent(url='/archive'), class_name='btn btn-sm btn-secondary'),
                c.Div(components=[], class_name='mt-4'),
                c.Table(
                    data=notes_for_table,
                    columns=[
                        DisplayLookup(field='title', title='Название', on_click=GoToEvent(url='/note/{id}')),
                        DisplayLookup(field='created_at', title='Дата создания', mode=DisplayMode.date),
                        DisplayLookup(field='archive_action', title='Восстановить', on_click=GoToEvent(url='/note/{id}/unarchive-run')),
                        DisplayLookup(field='delete_action', title='Удалить', on_click=GoToEvent(url='/note/{id}/delete-run')),
                    ]
                ) if notes_for_table else c.Paragraph(text='В архиве пока ничего нет.')
            ]
        )
    ]


@app.get('/api/note/{note_id}/archive-run', response_model=FastUI, response_model_exclude_none=True)
def handle_archive_note(note_id: int, db: Session = Depends(get_db)) -> list[AnyComponent]:
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if db_note:
        db_note.is_archived = True
        db.commit()
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/api/note/{note_id}/unarchive-run', response_model=FastUI, response_model_exclude_none=True)
def handle_unarchive_note(note_id: int, db: Session = Depends(get_db)) -> list[AnyComponent]:
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if db_note:
        db_note.is_archived = False
        db.commit()
    return [c.FireEvent(event=GoToEvent(url='/archive'))]


@app.get('/api/note/{note_id}/delete-run', response_model=FastUI, response_model_exclude_none=True)
def handle_delete_note(note_id: int, db: Session = Depends(get_db)) -> list[AnyComponent]:
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if db_note:
        db.delete(db_note)
        db.commit()
    return [c.FireEvent(event=GoToEvent(url='/archive'))]


@app.get('/api/note/{note_id}', response_model=FastUI, response_model_exclude_none=True)
def view_note_page(note_id: int, db: Session = Depends(get_db)) -> list[AnyComponent]:
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail='Заметка не найдена')
    note = NoteReadSchema.model_validate(db_note)
    return [
        c.Page(
            components=[
                c.Heading(text=note.title, level=1),
                c.Paragraph(text=f'Дата создания: {note.created_at.strftime("%d.%m.%Y %H:%M")}'),
                c.Link(components=[c.Text(text='🔙 Назад к списку')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-3'),
                c.Div(components=[], class_name='my-4 p-4 bg-light rounded border'),
                c.Markdown(text=note.content),
            ]
        )
    ]


@app.get('/api/add', response_model=FastUI, response_model_exclude_none=True)
def add_note_page() -> list[AnyComponent]:
    return [
        c.Page(
            components=[
                c.Heading(text='✏️ Новая запись', level=1),
                c.Link(components=[c.Text(text='🔙 Отмена')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-3'),
                c.Div(components=[], class_name='mt-4'),
                c.ModelForm(model=NoteCreateSchema, submit_url='/api/add')
            ]
        )
    ]


@app.post('/api/add', response_model=FastUI, response_model_exclude_none=True)
def handle_add_note(
    request: Request,  # <-- ДОБАВИЛИ СЮДА
    form: NoteCreateSchema = fastui_form(NoteCreateSchema),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Обработчик добавления заметки: читает автора из сессии Cookie.'''
    # Узнаем ID пользователя, который сейчас авторизован
    user_id = get_user_from_session(request)

    if not user_id:
        # Если куки нет или она протухла, не даем писать в дневник
        raise HTTPException(status_code=401, detail='Пожалуйста, войдите в аккаунт')

    new_note = models.Note(
        title=form.title,
        content=form.content,
        user_id=user_id  # <-- ПРИВЯЗАЛИ К РЕАЛЬНОМУ АВТОРУ
    )
    db.add(new_note)
    db.commit()
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/api/login', response_model=FastUI, response_model_exclude_none=True)
def login_page() -> list[AnyComponent]:
    '''Страница входа в приложение.'''
    return [
        c.Page(
            components=[
                c.Heading(text='🔑 Вход в систему', level=1),
                c.Link(components=[c.Text(text='🔙 На главную')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-3'),
                c.Div(components=[], class_name='mt-4'),
                # Указали модель напрямую из импортированных схем
                c.ModelForm(model=UserLoginSchema, submit_url='/api/login')
            ]
        )
    ]


@app.post('/api/login', response_model=FastUI, response_model_exclude_none=True)
def handle_login(
    response: Response,
    # УБРАЛИ тернарный оператор, оставили чистую аннотацию типа по правилам Python
    form: UserLoginSchema = fastui_form(UserLoginSchema),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Обработчик входа: сверяет хэш и выдает Cookie-сессию.'''
    user = db.query(models.User).filter(models.User.email == form.email).first()
    
    if not user or not verify_password(form.password.get_secret_value(), user.hashed_password):
        raise HTTPException(status_code=400, detail='Неверный email или пароль')
    
    # ЗАПОМИНАЕМ ПОЛЬЗОВАТЕЛЯ: Пишем зашифрованный ID в браузер
    set_user_session(response, user.id)
    
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/api/logout', response_model=FastUI, response_model_exclude_none=True)
def handle_logout(response: Response) -> list[AnyComponent]:
    '''Удаляет Cookie-сессию из браузера и разлогинивает пользователя.'''
    response.delete_cookie('diary_session')
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    '''Любой адрес, не начинающийся с /api, отдаст JS-фронтенд от FastUI.'''
    return HTMLResponse(prebuilt_html(title='Личный Дневник'))
