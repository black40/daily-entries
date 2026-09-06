from fastapi import APIRouter, Depends, HTTPException, Request, Form
from sqlalchemy.orm import Session
from fastui import FastUI, AnyComponent
from fastui import components as c
from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from fastui.forms import fastui_form

from app.database import get_db
from app.session import get_user_from_session
import app.models as models
from app.schemas import NoteCreateSchema, NoteReadSchema, CategoryCreateSchema, CategoryReadSchema
from fastui.components.forms import FormFieldInput, FormFieldSelect, FormFieldTextarea

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
                c.Heading(text=db_note.title, level=1, class_name='mb-2'),
                
                # Дата создания и категория заметки
                c.Paragraph(
                    text=f'Дата создания: {note.created_at.strftime("%d.%m.%Y %H:%M")} | Категория: {note.category_name}', 
                    class_name='text-muted small mb-4'
                ),
                
                # ИСПРАВЛЕНО: Две кнопки стоят аккуратно в один ряд в общем блоке Div
                c.Div(
                    components=[
                        c.Link(components=[c.Text(text='🔙 Назад к списку')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary me-2'),
                        c.Link(components=[c.Text(text='🏷 Сменить категорию')], on_click=GoToEvent(url=f'/note/{note_id}/edit-category'), class_name='btn btn-outline-primary')
                    ],
                    class_name='mb-4'
                ),
                
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
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

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
    '''Страница настройки категорий: форма создания и интерактивная таблица удаления.'''
    user_id = get_user_from_session(request)

    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]


    # Загружаем категории и валидируем их через схему со встроенной кнопкой удаления
    db_categories = db.query(models.Category).filter(models.Category.user_id == user_id).order_by(models.Category.name.asc()).all()
    categories_for_table = [CategoryReadSchema.model_validate(cat) for cat in db_categories]

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
                                c.ModelForm(model=CategoryCreateSchema, submit_url='/api/categories')
                            ],
                            class_name='col-md-5 border-end pe-4'
                        ),
                        c.Div(
                            components=[
                                c.Heading(text='Ваши текущие категории', level=3, class_name='mb-3'),
                                # ИСПРАВЛЕНО: Вместо списка параграфов выводим полноценную таблицу с действием!
                                c.Table(
                                    data=categories_for_table,
                                    columns=[
                                        DisplayLookup(field='name', title='Название папки'),
                                        DisplayLookup(
                                            field='delete_action', 
                                            title='Действие', 
                                            on_click=GoToEvent(url='/categories/{id}/delete')
                                        )
                                    ]
                                ) if categories_for_table else c.Paragraph(text='Вы еще не создали ни одной категории.', class_name='text-muted')
                            ],
                            class_name='col-md-7 ps-4'
                        )
                    ],
                    class_name='row'
                )
            ]
        )
    ]


@router.get('/categories/{category_id}/delete', response_model=FastUI, response_model_exclude_none=True)
def handle_delete_category(
    category_id: int, 
    request: Request, 
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Роут удаления: стирает категорию из базы данных, изолируя права пользователя.'''
    user_id = get_user_from_session(request)
    
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]


    # Находим категорию и строго проверяем, принадлежит ли она текущему пользователю (защита!)
    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == user_id
    ).first()

    if category:
        db.delete(category)
        db.commit()

    # Перезагружаем страницу категорий, чтобы увидеть обновленную таблицу
    return [c.FireEvent(event=GoToEvent(url='/categories'))]


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

@router.get('/note/{note_id}/edit-category', response_model=FastUI, response_model_exclude_none=True)
def edit_note_category_page(note_id: int, request: Request, db: Session = Depends(get_db)) -> list[AnyComponent]:
    '''Страница изменения категории для уже существующей заметки.'''
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    # Находим заметку и проверяем права доступа
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note or db_note.user_id != user_id:
        return [c.FireEvent(event=GoToEvent(url='/'))]

    # 1. Загружаем все категории текущего пользователя для выпадающего списка
    db_categories = db.query(models.Category).filter(models.Category.user_id == user_id).order_by(models.Category.name.asc()).all()
    
    # 2. Формируем опции для Select
    select_options = [{'value': '0', 'label': 'Без категории'}]
    for cat in db_categories:
        select_options.append({'value': str(cat.id), 'label': f'📁 {cat.name}'})

    # Определяем текущее значение, чтобы список открывался на текущей категории заметки
    current_value = str(db_note.category_id) if db_note.category_id else '0'

    return [
        c.Page(
            components=[
                c.Heading(text=f'Перенос заметки: «{db_note.title}»', level=2),
                c.Link(components=[c.Text(text='🔙 Отмена')], on_click=GoToEvent(url=f'/note/{note_id}'), class_name='btn btn-secondary mb-4'),
                c.Div(components=[], class_name='mt-4'),
                
                # Форма со списком категорий
                c.Form(
                    submit_url=f'/api/note/{note_id}/edit-category',
                    form_fields=[
                        FormFieldSelect(
                            name='category_id', 
                            title='Выберите новую категорию', 
                            options=select_options,
                            initial=current_value
                        )
                    ]
                )
            ]
        )
    ]


@router.post('/note/{note_id}/edit-category', response_model=FastUI, response_model_exclude_none=True)
def handle_edit_note_category(
    note_id: int,
    request: Request,
    category_id: str = Form(...),  # Получаем выбранное значение строкой ('0', '1', '2')
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Обработчик изменения категории: обновляет поле category_id в SQLite.'''
    user_id = get_user_from_session(request)
    if not user_id:
        return [c.FireEvent(event=GoToEvent(url='/login'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note or db_note.user_id != user_id:
        return [c.FireEvent(event=GoToEvent(url='/'))]

    # Конвертируем строковый ID в число или None
    parsed_category_id = None
    if category_id and category_id != '0':
        try:
            parsed_category_id = int(category_id)
        except ValueError:
            parsed_category_id = None

    # Обновляем поле в базе данных
    db_note.category_id = parsed_category_id
    db.commit()

    # Возвращаем пользователя на страницу детального просмотра этой заметки
    return [c.FireEvent(event=GoToEvent(url=f'/note/{note_id}'))]
