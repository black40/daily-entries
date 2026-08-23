from fastapi import FastAPI, Depends, HTTPException, Request, Response
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
    response = await call_next(request)
    if '/logout' in request.url.path:
        return response
    if not request.url.path.startswith('/favicon.ico'):
        refresh_user_session(request, response)
    return response


@app.get('/api/', response_model=FastUI, response_model_exclude_none=True)
def notes_list_page(request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    user_id = get_user_from_session(request)
    auth_components = []
    notes_for_table = []
    user = None

    if user_id:
        user = db.query(models.User).filter(models.User.id == user_id).first()

    if user_id and user:
        auth_components = [
            c.Paragraph(text=f'👤 {user.email}', class_name='text-muted me-2 d-inline'),
            c.Link(components=[c.Text(text='🚪 Выйти')], on_click=GoToEvent(url='/logout'), class_name='btn btn-sm btn-danger me-2'),
            c.Link(components=[c.Text(text='❌ Удалить аккаунт')], on_click=GoToEvent(url='/delete-account'), class_name='btn btn-sm btn-outline-danger')
        ]
        db_notes = db.query(models.Note).filter(models.Note.is_archived == False, models.Note.user_id == user_id).order_by(models.Note.created_at.desc()).all()
        for note in db_notes:
            pydantic_note = NoteReadSchema.model_validate(note)
            pydantic_note.archive_action = '📦 В архив'
            notes_for_table.append(pydantic_note)
    else:
        auth_components = [
            c.Paragraph(text='👤 Гость', class_name='text-muted me-3 d-inline'),
            c.Link(components=[c.Text(text='🔑 Войти')], on_click=GoToEvent(url='/login'), class_name='btn btn-sm btn-warning me-2'),
            c.Link(components=[c.Text(text='👤 Регистрация')], on_click=GoToEvent(url='/register'), class_name='btn btn-sm btn-outline-dark')
        ]

    main_content = []
    if user_id and user:
        main_content.append(c.Heading(text='Ваши активные записи', level=3))
        if notes_for_table:
            main_content.append(
                c.Table(data=notes_for_table, columns=[
                    DisplayLookup(field='title', title='Название', on_click=GoToEvent(url='/note/{id}')),
                    DisplayLookup(field='created_at', title='Дата создания', mode=DisplayMode.date),
                    DisplayLookup(field='archive_action', title='Действие', on_click=GoToEvent(url='/note/{id}/archive-run')),
                ])
            )
        else:
            main_content.append(c.Paragraph(text='Активных записей нет. Нажмите зеленую кнопку выше, чтобы написать первую!'))
    else:
        main_content.append(c.Paragraph(text='Пожалуйста, войдите в свой аккаунт, чтобы просматривать и создавать личные заметки.'))

    return [
        c.Page(
            components=[
                c.Heading(text='📝 Мой Дневник & Заметки', level=1),
                c.Link(components=[c.Text(text='📝 Active')], on_click=GoToEvent(url='/'), class_name='btn btn-sm btn-primary me-2'),
                c.Link(components=[c.Text(text='🗂 Архив')], on_click=GoToEvent(url='/archive'), class_name='btn btn-sm btn-secondary me-2'),
                c.Link(components=[c.Text(text='➕ Написать')], on_click=GoToEvent(url='/add'), class_name='btn btn-sm btn-success me-4'),
                *auth_components,
                c.Div(components=[], class_name='mt-4'),
                *main_content
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
def admin_users_page(db: Session = Depends(get_db)) -> list[AnyComponent]:
    db_users = db.query(models.User).order_by(models.User.id.asc()).all()
    users_for_table = [UserReadSchema.model_validate(user) for user in db_users]
    return [
        c.Page(
            components=[
                c.Heading(text='👥 Управление пользователями (Админка)', level=1),
                c.Link(components=[c.Text(text='🔙 На главную')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-3'),
                c.Div(components=[], class_name='mt-4'),
                c.Heading(text=f'Всего зарегистрировано: {len(users_for_table)}', level=4),
                c.Table(data=users_for_table, columns=[
                    DisplayLookup(field='id', title='ID'),
                    DisplayLookup(field='email', title='Email (Логин)'),
                    DisplayLookup(field='created_at', title='Дата регистрации', mode=DisplayMode.date),
                ]) if users_for_table else c.Paragraph(text='Пользователей в базе данных пока нет.')
            ]
        )
    ]


@app.post('/api/add', response_model=FastUI, response_model_exclude_none=True)
def handle_add_note(request: Request, form: NoteCreateSchema = fastui_form(NoteCreateSchema), db: Session = Depends(get_db)) -> list[AnyComponent]:
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]
    db.add(models.Note(title=form.title, content=form.content, user_id=user_id))
    db.commit()
    return [c.FireEvent(event=GoToEvent(url='/'))]


@app.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    return HTMLResponse(prebuilt_html(title='Личный Дневник'))
