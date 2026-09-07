from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse

from fastui import FastUI, AnyComponent
from fastui import components as c
from fastui.events import GoToEvent
from fastui.components.display import DisplayLookup, DisplayMode
from fastui.forms import SelectOption
from fastui.forms import fastui_form


from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schemas import NoteCreateSchema, NoteReadSchema, CategoryCreateSchema, CategoryReadSchema
from app.auth import get_current_user

router = APIRouter()

@router.get('/archive', response_model=FastUI, response_model_exclude_none=True)
def archive_list_page(
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Страница архива заметок пользователя под защитой единой зависимости.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    db_notes = db.query(models.Note).filter(
        models.Note.is_archived == True, 
        models.Note.user_id == current_user.id
    ).order_by(models.Note.created_at.desc()).all()
    
    notes_for_table = []
    for note in db_notes:
        schema = NoteReadSchema.model_validate(note)
        schema.category_name = f'📁 {note.category.name}' if note.category else '📝 Без категории'
        schema.archive_action = '⏪ Восстановить'
        notes_for_table.append(schema)

    return [
        c.Page(
            components=[
                c.Heading(text='🗂 Архив ваших записей', level=1),
                c.Link(components=[c.Text(text='🔙 На главную')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-4'),
                
                c.Table(
                    data=notes_for_table,
                    columns=[
                        DisplayLookup(field='title', title='Название', on_click=GoToEvent(url='/note/{id}')),
                        DisplayLookup(field='category_name', title='Категория'),
                        DisplayLookup(field='created_at', title='Дата создания', mode=DisplayMode.date),
                        DisplayLookup(field='archive_action', title='Действие', on_click=GoToEvent(url='/note/{id}/restore-run')),
                        DisplayLookup(
                            field='delete_action', 
                            title='Уничтожить', 
                            on_click=GoToEvent(url='/note/{id}/delete-run?from_page=archive')
                        ),
                    ]
                ) if notes_for_table else c.Paragraph(text='В архиве пока пусто.', class_name='text-muted')
            ]
        )
    ]


@router.get('/note/{note_id}/archive-run', response_model=FastUI, response_model_exclude_none=True)
def handle_archive_note(
    note_id: int, 
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Перенос заметки в архив под защитой зависимости.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note or db_note.user_id != current_user.id:
        return [c.FireEvent(event=GoToEvent(url='/'))]

    db_note.is_archived = True
    db.commit()
    return [c.FireEvent(event=GoToEvent(url='/'))]


@router.get('/note/{note_id}/restore-run', response_model=FastUI, response_model_exclude_none=True)
def handle_restore_note(
    note_id: int, 
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Восстановление заметки из архива.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note or db_note.user_id != current_user.id:
        return [c.FireEvent(event=GoToEvent(url='/'))]

    db_note.is_archived = False
    db.commit()
    return [c.FireEvent(event=GoToEvent(url='/archive'))]

@router.get('/note/{note_id}', response_model=FastUI, response_model_exclude_none=True)
def view_note_page(
    note_id: int, 
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Детальный просмотр заметки под защитой зависимости.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note or db_note.user_id != current_user.id:
        return [c.FireEvent(event=GoToEvent(url='/'))]

    note = NoteReadSchema.model_validate(db_note)
    note.category_name = f'📁 {db_note.category.name}' if db_note.category else '📝 Без категории'

    return [
        c.Page(
            components=[
                c.Heading(text=db_note.title, level=1, class_name='mb-2'),
                c.Paragraph(
                    text=f'Дата создания: {note.created_at.strftime("%d.%m.%Y %H:%M")} | Категория: {note.category_name}', 
                    class_name='text-muted small mb-4'
                ),
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
def add_note_page(
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Страница создания заметки с универсальными FormFieldInput.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    db_categories = db.query(models.Category).filter(models.Category.user_id == current_user.id).order_by(models.Category.name.asc()).all()
    
    select_options = [SelectOption(value='0', label='Без категории')]
    for cat in db_categories:
        select_options.append(SelectOption(value=str(cat.id), label=f'📁 {cat.name}'))

    return [
        c.Page(
            components=[
                c.Heading(text='➕ Создать новую запись', level=1),
                c.Link(components=[c.Text(text='🔙 На главную')], on_click=GoToEvent(url='/'), class_name='btn btn-secondary mb-4'),
                c.Div(components=[], class_name='mt-4'),
                
                c.Form(
                    submit_url='/api/add',
                    form_fields=[
                                                c.FormFieldInput(
                            name='title', 
                            title='Название заметки'
                        ),
                        c.FormFieldSelect(
                            name='category_id', 
                            title='Категория (необязательно)', 
                            options=select_options, 
                            initial='0'
                        ),
                        # ИСПРАВЛЕНО: Убрали некорректный html_type. 
                        # Оставляем только rows=10, и FastUI сам превратит поле в Textarea!
                        c.FormFieldInput(
                            name='content', 
                            title='Текст заметки (поддерживает Markdown)', 
                            rows=10
                        ),

                    ]
                )
            ]
        )
    ]


@router.get('/categories', response_model=FastUI, response_model_exclude_none=True)
def categories_management_page(
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Страница управления категориями под защитой зависимости.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    db_categories = db.query(models.Category).filter(models.Category.user_id == current_user.id).order_by(models.Category.name.asc()).all()
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
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Обработчик удаления категории с защитой владельца.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    category = db.query(models.Category).filter(
        models.Category.id == category_id,
        models.Category.user_id == current_user.id
    ).first()

    if category:
        db.delete(category)
        db.commit()

    return [c.FireEvent(event=GoToEvent(url='/categories'))]


@router.get('/note/{note_id}/edit-category', response_model=FastUI, response_model_exclude_none=True)
def edit_note_category_page(
    note_id: int, 
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Страница изменения категории для заметки.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note or db_note.user_id != current_user.id:
        return [c.FireEvent(event=GoToEvent(url='/'))]

    db_categories = db.query(models.Category).filter(models.Category.user_id == current_user.id).order_by(models.Category.name.asc()).all()
    
    # Заполняем опции через SelectOption
    select_options = [SelectOption(value='0', label='Без категории')]
    for cat in db_categories:
        select_options.append(SelectOption(value=str(cat.id), label=f'📁 {cat.name}'))

    current_value = str(db_note.category_id) if db_note.category_id else '0'

    return [
        c.Page(
            components=[
                c.Heading(text=f'Перенос заметки: «{db_note.title}»', level=2),
                c.Link(components=[c.Text(text='🔙 Отмена')], on_click=GoToEvent(url=f'/note/{note_id}'), class_name='btn btn-secondary mb-4'),
                c.Div(components=[], class_name='mt-4'),
                
                c.Form(
                    submit_url=f'/api/note/{note_id}/edit-category',
                    form_fields=[
                        # ИСПРАВЛЕНО: Обращаемся к полю выбора через c.FormFieldSelect!
                        c.FormFieldSelect(
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
    category_id: str = Form(...),
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Обработчик изменения категории у существующей заметки.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note or db_note.user_id != current_user.id:
        return [c.FireEvent(event=GoToEvent(url='/'))]

    parsed_category_id = None
    if category_id and category_id != '0':
        try:
            parsed_category_id = int(category_id)
        except ValueError:
            parsed_category_id = None

    db_note.category_id = parsed_category_id
    db.commit()

    return [c.FireEvent(event=GoToEvent(url=f'/note/{note_id}'))]


@router.post('/categories', response_model=FastUI, response_model_exclude_none=True)
def handle_create_category(
    form: CategoryCreateSchema = fastui_form(CategoryCreateSchema),
    # ИСПРАВЛЕНО: Перевели роут на единую зависимость вместо get_user_from_session
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Обработчик создания категории под защитой зависимости.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    new_category = models.Category(
        name=form.name,
        user_id=current_user.id
    )
    db.add(new_category)
    db.commit()

    return [c.FireEvent(event=GoToEvent(url='/categories'))]


# Убедитесь, что Query импортирован наверх файла из fastapi
from fastapi import Query

@router.get('/note/{note_id}/delete-run', response_model=FastUI, response_model_exclude_none=True)
def handle_delete_note(
    note_id: int,
    # ИСПРАВЛЕНО: Явно принимаем параметр, откуда было совершено удаление
    from_page: Optional[str] = Query(None),
    current_user: Optional[models.User] = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    '''Уничтожение заметки: физически удаляет запись и возвращает на указанную страницу.'''
    if not current_user:
        return [c.FireEvent(event=GoToEvent(url='/login?error=auth_required'))]

    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    
    if db_note and db_note.user_id == current_user.id:
        db.delete(db_note)
        db.commit()

    # ИСПРАВЛЕНО: Железная логика редиректа на основе явного параметра кнопки!
    if from_page == 'archive':
        return [c.FireEvent(event=GoToEvent(url='/archive'))]
        
    return [c.FireEvent(event=GoToEvent(url='/'))]
