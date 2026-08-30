from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi import Form
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from fastui import FastUI, AnyComponent, prebuilt_html
from fastui import components as c
from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from fastui.forms import fastui_form

from app.database import engine, Base, get_db
from app.auth import hash_password, verify_password
from app.session import set_user_session, get_user_from_session, refresh_user_session
from app.notes import router as notes_router  # ИМПОРТИРУЕМ НАШ НОВЫЙ РОУТЕР
import app.models as models
from app.schemas import NoteCreateSchema, NoteReadSchema, UserRegisterSchema, UserLoginSchema, UserReadSchema

app = FastAPI()
Base.metadata.create_all(bind=engine)

# ПОДКЛЮЧАЕМ РОУТЫ ЗАМЕТОК
app.include_router(notes_router)


@app.middleware('http')
async def sliding_session_middleware(request: Request, call_next):
    '''Промежуточный слой, который сдвигает срок годности Cookie при каждом клике.'''
    response = await call_next(request)
    
    # ИСПРАВЛЕНО: Если пользователь выходит или только входит, мы ЖЕЛЕЗНО не трогаем сессию в middleware!
    if '/logout' in request.url.path or '/login' in request.url.path:
        return response
        
    # Для всех остальных страниц (кроме иконок) кука плавно скользит вперед
    if not request.url.path.startswith('/favicon.ico'):
        refresh_user_session(request, response)
        
    return response


@app.get('/api/', response_model=FastUI, response_model_exclude_none=True)
def notes_list_page(request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Главная страница: динамический вывод заметок и категорий в сайдбаре.'''
    user_id = get_user_from_session(request)
    auth_components = []
    notes_for_table = []
    sidebar_categories = []
    user = None

    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()

    # Сборка компонентов авторизации хедера
    if user_id and user:
        auth_components = [
            c.Paragraph(text=f'👤 {user.email}', class_name='text-muted me-2 d-inline small'),
            c.Link(components=[c.Text(text='🚪 Выйти')], on_click=GoToEvent(url='/logout'), class_name='btn btn-sm btn-danger me-2'),
            c.Link(components=[c.Text(text='❌ Удалить аккаунт')], on_click=GoToEvent(url='/delete-account'), class_name='btn btn-sm btn-outline-danger me-2')
        ]
        if user.email == 'admin@i.ua':
            auth_components.append(
                c.Link(components=[c.Text(text='👥 Админка')], on_click=GoToEvent(url='/users'), class_name='btn btn-sm btn-secondary')
            )
        
        # Подгружаем активные заметки пользователя
        db_notes = db.query(models.Note).filter(models.Note.is_archived == False, models.Note.user_id == user_id).order_by(models.Note.created_at.desc()).all()
        notes_for_table = [NoteReadSchema.model_validate(note) for note in db_notes]
        for n in notes_for_table:
            n.archive_action = '📦 В архив'
            
        # НОВОЕ: Подгружаем реальные категории пользователя из SQLite!
        db_categories = db.query(models.Category).filter(models.Category.user_id == user_id).order_by(models.Category.name.asc()).all()
        for cat in db_categories:
            sidebar_categories.append(
                c.Paragraph(text=f'📁 {cat.name}', class_name='p-2 bg-white rounded border mb-1 small')
            )
    else:
        auth_components = [
            c.Paragraph(text='👤 Гость', class_name='text-muted me-3 d-inline small'),
            c.Link(components=[c.Text(text='🔑 Войти')], on_click=GoToEvent(url='/login'), class_name='btn btn-sm btn-warning me-2'),
            c.Link(components=[c.Text(text='👤 Регистрация')], on_click=GoToEvent(url='/register'), class_name='btn btn-sm btn-outline-dark')
        ]

    # Сборка центрального контента (CONTENT)
    content_components = []
    if user_id and user:
        content_components.append(c.Heading(text='Ваши активные записи', level=3, class_name='mb-3'))
        if notes_for_table:
            content_components.append(
                c.Table(data=notes_for_table, columns=[
                    DisplayLookup(field='title', title='Название', on_click=GoToEvent(url='/note/{id}')),
                    DisplayLookup(field='created_at', title='Дата создания', mode=DisplayMode.date),
                    DisplayLookup(field='archive_action', title='Действие', on_click=GoToEvent(url='/note/{id}/archive-run')),
                ])
            )
        else:
            content_components.append(c.Paragraph(text='Активных записей нет. Создайте первую категорию и напишите заметку!'))
    else:
        content_components.append(c.Paragraph(text='Пожалуйста, войдите в свой аккаунт, чтобы просматривать и создавать личные заметки.', class_name='alert alert-info'))

    # Формируем блок категорий для сайдбара
    if not sidebar_categories and user_id:
        sidebar_categories.append(c.Paragraph(text='Категорий пока нет', class_name='text-muted small italic mb-3'))

    return [
        c.Page(
            components=[
                # HEADER
                c.Div(
                    components=[
                        c.Link(components=[c.Heading(text='📝 Дневник SaaS', level=3, class_name='m-0 text-dark')], on_click=GoToEvent(url='/')),
                        c.Div(components=auth_components, class_name='d-flex align-items-center')
                    ],
                    class_name='d-flex justify-content-between align-items-center p-3 mb-4 bg-light border-bottom'
                ),
                # GRID SYSTEM
                c.Div(
                    components=[
                        c.Div(
                            components=[
                                # SIDEBAR
                                c.Div(
                                    components=[
                                        c.Link(components=[c.Text(text='➕ Написать заметку')], on_click=GoToEvent(url='/add'), class_name='btn btn-success w-100 mb-2') if user_id else c.Div(components=[]),
                                        c.Link(components=[c.Text(text='🗂 Открыть архив')], on_click=GoToEvent(url='/archive'), class_name='btn btn-outline-secondary w-100 mb-4') if user_id else c.Div(components=[]),
                                        
                                        c.Heading(text='📂 Категории', level=4, class_name='mb-2'),
                                        c.Div(
                                            components=sidebar_categories + ([
                                                c.Link(components=[c.Text(text='⚙️ Настроить категории')], on_click=GoToEvent(url='/categories'), class_name='btn btn-sm btn-link p-0 mt-2')
                                            ] if user_id else []),
                                            class_name='p-3 bg-light rounded border'
                                        )
                                    ],
                                    class_name='col-md-3 border-end pe-3'
                                ),
                                # CONTENT
                                c.Div(components=content_components, class_name='col-md-9')
                            ],
                            class_name='row'
                        )
                    ],
                    class_name='container-fluid mb-5'
                ),
                # FOOTER
                c.Div(
                    components=[c.Paragraph(text='© 2026 Личный Дневник SaaS. Все права защищены. Бла бла бла...', class_name='text-muted text-center m-0 small')],
                    class_name='p-3 mt-auto bg-light border-top fixed-bottom'
                )
            ]
        )
    ]


@app.get('/api/register', response_model=FastUI, response_model_exclude_none=True)
def register_page() -> list[AnyComponent]:
    return [
        c.Page(
            components=[
                c.Heading(text='👤 Регистрация нового аккаунта', level=1),
                c.Link(components=[c.Text(text='🔙 На главную')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-3'),
                c.Div(components=[], class_name='mt-4'),
                c.ModelForm(model=UserRegisterSchema, submit_url='/api/register', initial={})
            ]
        )
    ]


@app.post('/api/register', response_model=FastUI, response_model_exclude_none=True)
def handle_register(form: UserRegisterSchema = fastui_form(UserRegisterSchema), db: Session = Depends(get_db)) -> list[AnyComponent]:
    existing_user = db.query(models.User).filter(models.User.email == form.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail='Пользователь с таким email уже существует')
    hashed_pwd = hash_password(form.password.get_secret_value())
    new_user = models.User(email=form.email, hashed_password=hashed_pwd)
    db.add(new_user); db.commit()
    return [c.FireEvent(event=GoToEvent(url='/login'))]


@app.get('/api/login', response_model=FastUI, response_model_exclude_none=True)
def login_page() -> list[AnyComponent]:
    return [
        c.Page(
            components=[
                c.Heading(text='🔑 Вход в систему', level=1),
                c.Link(components=[c.Text(text='🔙 На главную')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-3'),
                c.Div(components=[], class_name='mt-4'),
                c.ModelForm(model=UserLoginSchema, submit_url='/api/login', initial={})
            ]
        )
    ]


@app.post('/api/login', response_model=FastUI, response_model_exclude_none=True)
def handle_login(response: Response, form: UserLoginSchema = fastui_form(UserLoginSchema), db: Session = Depends(get_db)) -> list[AnyComponent]:
    user = db.query(models.User).filter(models.User.email == form.email).first()
    if not user or not verify_password(form.password.get_secret_value(), user.hashed_password):
        raise HTTPException(status_code=400, detail='Неверный email или пароль')
    set_user_session(response, user.id)
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/api/logout', response_model=FastUI, response_model_exclude_none=True)
def handle_logout(response: Response) -> list[AnyComponent]:
    response.delete_cookie('diary_session')
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/api/delete-account', response_model=FastUI, response_model_exclude_none=True)
def handle_delete_account(request: Request, response: Response, db: Session = Depends(get_db)) -> list[AnyComponent]:
    user_id = get_user_from_session(request)
    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            db.delete(user); db.commit()
    response.delete_cookie('diary_session')
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/api/users', response_model=FastUI, response_model_exclude_none=True)
def admin_users_page(request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Служебная страница для просмотра всех зарегистрированных пользователей (доступна только админу).'''
    # 1. Читаем текущую сессию
    user_id = get_user_from_session(request)
    user = db.query(models.User).filter(models.User.id == user_id).first() if user_id else None
    
    # 2. ИСПРАВЛЕНО: Если пользователь не вошел или его email не админский, разворачиваем на главную
    # Впишите сюда свой реальный email, под которым будете администрировать систему
    if not user or user.email != 'admin@i.ua':
        return [c.FireEvent(event=GoToEvent(url='/'))]

    # 3. Если проверку прошел — загружаем список
    db_users = db.query(models.User).order_by(models.User.id.asc()).all()
    users_for_table = [UserReadSchema.model_validate(user_item) for user_item in db_users]

    return [
        c.Page(
            components=[
                c.Heading(text='👥 Управление пользователями (Админка)', level=1),
                c.Link(components=[c.Text(text='🔙 На главную')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-3'),
                c.Div(components=[], class_name='mt-4'),
                c.Heading(text=f'Всего зарегистрировано: {len(users_for_table)}', level=4),
                c.Table(
                    data=users_for_table,
                    columns=[
                        DisplayLookup(field='id', title='ID'),
                        DisplayLookup(field='email', title='Email (Логин)'),
                        DisplayLookup(field='created_at', title='Дата регистрации', mode=DisplayMode.date),
                        # ИСПРАВЛЕНО: Добавили колонку с кнопкой удаления и роутом действия
                        DisplayLookup(
                            field='delete_action', 
                            title='Действие', 
                            on_click=GoToEvent(url='/users/{id}/delete-run')
                        ),
                    ]
                ) if users_for_table else c.Paragraph(text='Пользователей в базе данных пока нет.')
            ]
        )
    ]

@app.get('/api/users/{user_to_delete_id}/delete-run', response_model=FastUI, response_model_exclude_none=True)
def handle_admin_delete_user(
    user_to_delete_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Админский роут: удаляет выбранного пользователя и каскадом все его заметки.'''
    # 1. Проверяем, что текущий пользователь — действительно главный админ
    current_user_id = get_user_from_session(request)
    current_user = db.query(models.User).filter(models.User.id == current_user_id).first() if current_user_id else None
    
    if not current_user or current_user.email != 'admin@i.ua':  # Используем ваш реальный email!
        return [c.FireEvent(event=GoToEvent(url='/'))]
        
    # 2. Не даем админу случайно удалить самого себя (защита от выстрела в ногу)
    if user_to_delete_id == current_user.id:
        raise HTTPException(status_code=400, detail='Вы не можете удалить свой собственный аккаунт администратора!')

    # 3. Находим жертву и удаляем
    user_target = db.query(models.User).filter(models.User.id == user_to_delete_id).first()
    if user_target:
        db.delete(user_target)
        db.commit()
        
    # Возвращаем админа на обновленную страницу списка пользователей
    return [c.FireEvent(event=GoToEvent(url='/users'))]


@app.post('/api/add', response_model=FastUI, response_model_exclude_none=True)
def handle_add_note(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category_id: str = Form(...),  # Прилетает в виде строки ('0', '1', '2')
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Обработчик добавления заметки: конвертирует строковый ID категории в число для SQLite.'''
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    # ИСПРАВЛЕНО: Конвертируем строковый ID категории в чистое число.
    # Если пришел '0' (Без категории), записываем в базу None.
    # Если пришло число ('1', '2') — превращаем в int, чтобы SQLAlchemy правильно связала таблицы!
    parsed_category_id = None
    if category_id and category_id != '0':
        try:
            parsed_category_id = int(category_id)
        except ValueError:
            parsed_category_id = None

    # Создаем запись с идеально провалидированными типами данных
    new_note = models.Note(
        title=title,
        content=content,
        user_id=user_id,
        category_id=parsed_category_id  # Теперь сюда пишется легальный int или None
    )
    db.add(new_note)
    db.commit()
    
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    return HTMLResponse(prebuilt_html(title='Личный Дневник'))
