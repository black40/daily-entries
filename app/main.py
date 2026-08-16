from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
# Импортируем движок, базу и зависимость из нашего нового файла
from app.database import engine, Base, get_db 
import app.models

app = FastAPI()

# Эта строчка автоматически создаст таблицы в файле .db при старте (если их нет)
Base.metadata.create_all(bind=engine)

@app.get('/')
async def main():
    return {'message': 'hello fastapi'}

@app.get("/api/notes")
def get_notes(db: Session = Depends(get_db)):
    # Здесь вы будете делать запросы к SQLite через SQLAlchemy
    pass

