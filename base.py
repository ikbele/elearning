from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configuration de la base de données
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# Création de l'engine
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

# Création de la base de données et de la session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe de base
Base = declarative_base()

# Modèle de données
class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

# Création des tables
Base.metadata.create_all(bind=engine)

# Initialisation de FastAPI
app = FastAPI()

# Dépendance pour obtenir la session de la base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Route pour ajouter un item
@app.post("/items/")
async def create_item(name: str, db: Session = Depends(get_db)):
    db_item = Item(name=name)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
