from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastui import FastUI, AnyComponent
from fastui import components as c
from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from fastui.forms import fastui_form

from app.database import get_db
from app.session import get_user_from_session
import app.models as models
from app.schemas import NoteCreateSchema, NoteReadSchema, CategoryCreateSchema
from fastui.components.forms import FormFieldInput, FormFieldSelect, FormFieldTextarea  # <-- ДОБАВЬТЕ ЭТОТ ИМПОРТ НАВЕРХ ФАЙЛА, если линтер ругается

# Создаем дочерний роутер для заметок
router = APIRouter(prefix='/api')


@router.get('/archive', response_model=FastUI, response_model_exclude_none=True)
def archive_list_page(request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    db_notes = (
        db.query(models.Note)
        .filter(models.Note.is_archived == True, models.Note.user_id == user_id)
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
                ) if notes_for_table else c.Paragraph(text='В вашем архиве пока ничего нет.')
            ]
        )
    ]


@router.get('/note/{note_id}/archive-run', response_model=FastUI, response_model_exclude_none=True)
def handle_archive_note(note_id: int, request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Перевод заметки в архив с жесткой проверкой владельца.'''
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    # Защита: проверяем, что заметка существует и принадлежит именно этому пользователю
    if db_note and db_note.user_id == user_id:
        db_note.is_archived = True
        db.commit()
    return [c.FireEvent(event=GoToEvent(url='/'))]


@router.get('/note/{note_id}/unarchive-run', response_model=FastUI, response_model_exclude_none=True)
def handle_unarchive_note(note_id: int, request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Извлечение заметки из архива с жесткой проверкой владельца.'''
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if db_note and db_note.user_id == user_id:
        db_note.is_archived = False
        db.commit()
    return [c.FireEvent(event=GoToEvent(url='/archive'))]


@router.get('/note/{note_id}/delete-run', response_model=FastUI, response_model_exclude_none=True)
def handle_delete_note(note_id: int, request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Физическое удаление заметки с жесткой проверкой владельца.'''
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if db_note and db_note.user_id == user_id:
        db.delete(db_note)
        db.commit()
    return [c.FireEvent(event=GoToEvent(url='/archive'))]


@router.get('/note/{note_id}', response_model=FastUI, response_model_exclude_none=True)
def view_note_page(note_id: int, request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Страница детального просмотра: выводит реальное название заметки без технических ID.'''
    user_id = get_user_from_session(request)
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail='Заметка не найдена')
        
    if user_id and db_note.user_id != user_id:
        return [c.FireEvent(event=GoToEvent(url='/'))]
    
    category_text = f'📁 {db_note.category.name}' if db_note.category else '📝 Без категории'
    
    note = NoteReadSchema.model_validate(db_note)
    note.category_name = category_text
    
    return [
        c.Page(
            components=[
                # ИСПРАВЛЕНО: Жестко прописали db_note.title. 
                # Теперь здесь будет выводиться реальный заголовок (например, "Мой день"), а не безликая цифра 4!
                c.Heading(text=db_note.title, level=1, class_name='mb-2'),
                
                # Дата создания и категория
                c.Paragraph(
                    text=f'Дата создания: {note.created_at.strftime("%d.%m.%Y %H:%M")} | Категория: {note.category_name}', 
                    class_name='text-muted small mb-4'
                ),
                
                c.Link(components=[c.Text(text='🔙 Назад к списку')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-3'),
                c.Div(components=[], class_name='my-4 p-4 bg-light rounded border'),
                c.Markdown(text=note.content),
            ]
        )
    ]


@router.get('/add', response_model=FastUI, response_model_exclude_none=True)
def add_note_page(request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Страница создания новой заметки с ручной сборкой формы без ошибок Pydantic.'''
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    # 1. Загружаем все категории текущего пользователя
    db_categories = db.query(models.Category).filter(models.Category.user_id == user_id).order_by(models.Category.name.asc()).all()
    
    # 2. Формируем список опций в формате FastUI Select: [{'value': '0', 'label': 'Текст'}]
    select_options = [{'value': '0', 'label': 'Без категории'}]
    for cat in db_categories:
        select_options.append({'value': str(cat.id), 'label': f'📁 {cat.name}'})

    return [
        c.Page(
            components=[
                c.Heading(text='✏️ Новая запись в дневник', level=1),
                c.Link(components=[c.Text(text='🔙 Отмена')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-4'),
                c.Div(components=[], class_name='mt-4'),
                
                # ИСПРАВЛЕНО: Вместо c.ModelForm собрали форму вручную через c.Form. 
                # Теперь Pydantic примет структуру без ошибок extra_forbidden!
                c.Form(
                    submit_url='/api/add',
                    form_fields=[
                        FormFieldInput(name='title', title='Заголовок заметки', required=True),
                        FormFieldTextarea(name='content', title='Текст заметки', rows=5, required=True),
                        FormFieldSelect(
                            name='category_id', 
                            title='Категория', 
                            options=select_options,
                            initial='0'
                        )
                    ]
                )
            ]
        )
    ]


@router.get('/categories', response_model=FastUI, response_model_exclude_none=True)
def categories_management_page(request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Страница настройки категорий: список и форма добавления.'''
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    # Загружаем все существующие категории этого пользователя
    db_categories = db.query(models.Category).filter(models.Category.user_id == user_id).order_by(models.Category.name.asc()).all()
    
    categories_list = []
    for cat in db_categories:
        categories_list.append(
            c.Paragraph(text=f'📁 {cat.name}', class_name='p-2 bg-white rounded border mb-1 small')
        )

    return [
        c.Page(
            components=[
                c.Heading(text='⚙️ Настройка ваших категорий', level=1),
                c.Link(components=[c.Text(text='🔙 На главную')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-4'),
                
                c.Div(
                    components=[
                        c.Div(
                            components=[
                                c.Heading(text='Создать новую категорию', level=3, class_name='mb-3'),
                                # Форма создания на основе нашей схемы
                                c.ModelForm(model=CategoryCreateSchema, submit_url='/api/categories')
                            ],
                            class_name='col-md-6 border-end pe-4'
                        ),
                        c.Div(
                            components=[
                                c.Heading(text='Ваши текущие категории', level=3, class_name='mb-3'),
                                *categories_list
                            ] if categories_list else [c.Paragraph(text='Вы еще не создали ни одной категории.', class_name='text-muted')],
                            class_name='col-md-6 ps-4'
                        )
                    ],
                    class_name='row'
                )
            ]
        )
    ]


@router.post('/categories', response_model=FastUI, response_model_exclude_none=True)
def handle_create_category(
    request: Request,
    form: CategoryCreateSchema = fastui_form(CategoryCreateSchema),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Обработчик создания категории: сохраняет тему в SQLite.'''
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    # Проверяем, нет ли уже категории с таким же именем у этого пользователя
    existing_cat = db.query(models.Category).filter(
        models.Category.name == form.name,
        models.Category.user_id == user_id
    ).first()
    
    if existing_cat:
        raise HTTPException(status_code=400, detail='Категория с таким названием уже существует')

    # Создаем и сохраняем новую категорию
    new_category = models.Category(
        name=form.name,
        user_id=user_id
    )
    db.add(new_category)
    db.commit()

    # Перезагружаем страницу управления категориями, чтобы увидеть обновленный список
    return [c.FireEvent(event=GoToEvent(url='/categories'))]
