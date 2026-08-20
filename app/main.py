from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

# Официальные компоненты FastUI
from fastui import FastUI, AnyComponent, prebuilt_html
from fastui import components as c
from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from fastui.forms import fastui_form

# Импорты вашей структуры проекта
from app.database import engine, Base, get_db
import app.models as models
from app.schemas import NoteCreateSchema, NoteReadSchema

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.get("/api/", response_model=FastUI, response_model_exclude_none=True)
def notes_list_page(db: Session = Depends(get_db)) -> list[AnyComponent]:
    """Главная страница: список активных заметок в красивой таблице."""
    db_notes = (
        db.query(models.Note)
        .filter(models.Note.is_archived == False)
        .order_by(models.Note.created_at.desc())
        .all()
    )
    
    notes_for_table = []
    for note in db_notes:
        pydantic_note = NoteReadSchema.model_validate(note)
        # Текст действия, который активируется при наведении на строку
        pydantic_note.archive_action = "📦 В архив"
        notes_for_table.append(pydantic_note)

    return [
        c.Page(
            components=[
                c.Heading(text="📝 Мой Дневник & Заметки", level=1),
                
                # Кнопки навигации сверху
                c.Link(components=[c.Text(text="📝 Активные записи")], on_click=GoToEvent(url="/"), class_name="btn btn-sm btn-primary me-2"),
                c.Link(components=[c.Text(text="🗂 Открыть архив")], on_click=GoToEvent(url="/archive"), class_name="btn btn-sm btn-outline-secondary me-2"),
                c.Link(components=[c.Text(text="➕ Написать новую заметку")], on_click=GoToEvent(url="/add"), class_name="btn btn-sm btn-success"),
                
                c.Div(components=[], class_name="mt-4"),
                c.Heading(text="Ваши записи", level=3) if notes_for_table else c.Paragraph(text="Активных записей нет."),
                
                # ВОЗВРАЩЕННАЯ СТАБИЛЬНАЯ ТАБЛИЦА
                c.Table(
                    data=notes_for_table,
                    columns=[
                        DisplayLookup(field='title', title='Название', on_click=GoToEvent(url='/note/{id}')),
                        DisplayLookup(field='created_at', title='Дата создания', mode=DisplayMode.date),
                        DisplayLookup(
                            field='archive_action', 
                            title='Действие', 
                            on_click=GoToEvent(url='/note/{id}/archive')
                        ),
                    ]
                ) if notes_for_table else c.Div(components=[])
            ]
        )
    ]


@app.get("/api/archive", response_model=FastUI, response_model_exclude_none=True)
def archive_list_page(db: Session = Depends(get_db)) -> list[AnyComponent]:
    """Страница архива: показывает только заархивированные заметки."""
    db_notes = (
        db.query(models.Note)
        .filter(models.Note.is_archived == True)
        .order_by(models.Note.created_at.desc())
        .all()
    )
    
    notes_for_table = []
    for note in db_notes:
        pydantic_note = NoteReadSchema.model_validate(note)
        # Восстанавливаем заголовок и текст действия для архива
        pydantic_note.archive_action = "↩️ Вернуть в список"
        notes_for_table.append(pydantic_note)

    return [
        c.Page(
            components=[
                c.Heading(text="🗂 Архив записей", level=1),
                
                c.Link(components=[c.Text(text="📝 Назад к записям")], on_click=GoToEvent(url="/"), class_name="btn btn-sm btn-outline-primary me-2"),
                c.Link(components=[c.Text(text="🗂 Архив")], on_click=GoToEvent(url="/archive"), class_name="btn btn-sm btn-secondary"),
                
                c.Div(components=[], class_name="mt-4"),
                
                # ТАБЛИЦА АРХИВА С ИСПРАВЛЕННЫМИ ЗАГОЛОВКАМИ
                c.Table(
                    data=notes_for_table,
                    columns=[
                        DisplayLookup(field='title', title='Название', on_click=GoToEvent(url='/note/{id}')),
                        DisplayLookup(field='created_at', title='Дата создания', mode=DisplayMode.date),
                        DisplayLookup(
                            field='archive_action', 
                            title='Действие', 
                            on_click=GoToEvent(url='/note/{id}/unarchive')
                        ),
                    ]
                ) if notes_for_table else c.Paragraph(text="В архиве пока ничего нет.")
            ]
        )
    ]


@app.get("/api/note/{note_id}/archive", response_model=FastUI, response_model_exclude_none=True)
def handle_archive_note(note_id: int, db: Session = Depends(get_db)) -> list[AnyComponent]:
    """Обработчик отправки заметки в архив."""
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Заметка не найдена")
    
    db_note.is_archived = True
    db.commit()
    return [c.FireEvent(event=GoToEvent(url="/"))]


@app.get("/api/note/{note_id}/unarchive", response_model=FastUI, response_model_exclude_none=True)
def handle_unarchive_note(note_id: int, db: Session = Depends(get_db)) -> list[AnyComponent]:
    """Обработчик извлечения заметки из архива."""
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Заметка не найдена")
    
    db_note.is_archived = False
    db.commit()
    return [c.FireEvent(event=GoToEvent(url="/archive"))]


@app.get("/api/note/{note_id}", response_model=FastUI, response_model_exclude_none=True)
def view_note_page(note_id: int, db: Session = Depends(get_db)) -> list[AnyComponent]:
    """Страница детального просмотра одной заметки."""
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Заметка не найдена")
    
    note = NoteReadSchema.model_validate(db_note)

    return [
        c.Page(
            components=[
                c.Heading(text=note.title, level=1),
                c.Paragraph(text=f"Дата создания: {note.created_at.strftime('%d.%m.%Y %H:%M')}"),
                c.Link(components=[c.Text(text="🔙 Назад к списку")], on_click=GoToEvent(url="/"), class_name="btn btn-secondary mb-3"),
                c.Div(components=[], class_name="my-4 p-4 bg-light rounded border"),
                c.Markdown(text=note.content),
            ]
        )
    ]


@app.get("/api/add", response_model=FastUI, response_model_exclude_none=True)
def add_note_page() -> list[AnyComponent]:
    """Страница с формой добавления новой заметки."""
    return [
        c.Page(
            components=[
                c.Heading(text="✏️ Новая запись", level=1),
                c.Link(components=[c.Text(text="🔙 Отмена")], on_click=GoToEvent(url="/"), class_name="btn btn-secondary mb-3"),
                c.Div(components=[], class_name="mt-4"),
                c.ModelForm(model=NoteCreateSchema, submit_url="/api/add")
            ]
        )
    ]


@app.post("/api/add", response_model=FastUI, response_model_exclude_none=True)
def handle_add_note(
    form: NoteCreateSchema = fastui_form(NoteCreateSchema),
    db: Session = Depends(get_db)
) -> list[AnyComponent]:
    """Обработчик отправки формы."""
    new_note = models.Note(title=form.title, content=form.content)
    db.add(new_note)
    db.commit()
    return [c.FireEvent(event=GoToEvent(url="/"))]


@app.get('/{path:path}')
async def html_landing() -> HTMLResponse:
    return HTMLResponse(prebuilt_html(title="Личный Дневник"))
