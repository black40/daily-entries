from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

# Компоненты FastUI
from fastui import FastUI, AnyComponent, prebuilt_html
from fastui import components as c
from fastui.components.display import DisplayLookup, DisplayMode
from fastui.events import GoToEvent
from fastui.forms import fastui_form

# Импорты вашего проекта
from app.database import engine, Base, get_db
import app.models as models
from app.schemas import NoteCreateSchema, NoteReadSchema

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.get("/api/", response_model=FastUI, response_model_exclude_none=True)
def notes_list_page(db: Session = Depends(get_db)) -> list[AnyComponent]:
    """Главная страница: список заметок и кнопка создания."""
    db_notes = db.query(models.Note).order_by(models.Note.created_at.desc()).all()
    notes_for_table = [NoteReadSchema.model_validate(note) for note in db_notes]

    return [
        c.Page(
            components=[
                c.Heading(text="📝 Мой Дневник & Заметки", level=1),
                c.Paragraph(text="Добро пожаловать. Ниже представлены ваши ежедневные записи."),
                
                c.Button(text="➕ Написать заметку", on_click=GoToEvent(url="/add")),
                
                c.Div(components=[], class_name="mt-4"),
                
                c.Heading(text="Ваши записи", level=3) if notes_for_table else c.Paragraph(text="Пока записей нет. Напишите первую!"),
                
                c.Table(
                    data=notes_for_table,
                    columns=[
                        # Сделали заголовок кликабельным: он ведет на /note/{id}
                        DisplayLookup(field='title', title='Название', on_click=GoToEvent(url='/note/{id}')),
                        DisplayLookup(field='created_at', title='Дата создания', mode=DisplayMode.date),
                    ]
                ) if notes_for_table else c.Div(components=[])
            ]
        )
    ]


@app.get("/api/note/{note_id}", response_model=FastUI, response_model_exclude_none=True)
def view_note_page(note_id: int, db: Session = Depends(get_db)) -> list[AnyComponent]:
    """Страница детального просмотра одной конкретной заметки."""
    # Ищем заметку в SQLite по ID
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not db_note:
        raise HTTPException(status_code=404, detail="Заметка не найдена")
    
    note = NoteReadSchema.model_validate(db_note)

    return [
        c.Page(
            components=[
                c.Heading(text=note.title, level=1),
                c.Paragraph(text=f"Дата создания: {note.created_at.strftime('%d.%m.%Y %H:%M')}"),
                c.Button(text="🔙 Назад к списку", on_click=GoToEvent(url="/")),
                
                c.Div(components=[], class_name="mt-4 my-4 p-4 bg-light rounded border"),
                
                # Выводим сам текст заметки
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
                c.Button(text="🔙 Назад к списку", on_click=GoToEvent(url="/")),
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
