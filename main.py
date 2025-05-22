from fastapi import FastAPI, HTTPException, Depends, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from database import SessionLocal, engine
from models import Base, DepartementModel, FormationModel, StudentModel, StudentFormation, RecommendedBook
import bcrypt
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import openai

# Configuration OpenAI
openai.api_key = "TA_CLE_OPENAI_ICI"  # Remplace avec ta propre clé en environnement sécurisé

# Initialisation FastAPI
app = FastAPI()

# CORS
origins = [
    "http://localhost:3000",
    "http://localhost:4200"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Création des tables
Base.metadata.create_all(bind=engine)

# Dépendance DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Schémas Pydantic
class StudentSchema(BaseModel):
    nom: str
    prenom: str
    email: str
    password: str
    departement_id: int

class DepartementSchema(BaseModel):
    name: str

class FormationSchema(BaseModel):
    title: str
    description: str
    departement_id: int

class StudentFormationLink(BaseModel):
    student_id: int
    formation_id: int

class RecommendedBookSchema(BaseModel):
    title: str
    price: float
    category: str
    availability: str

# Routes

@app.post("/departements")
def create_departement(dep: DepartementSchema, db: Session = Depends(get_db)):
    db_dep = DepartementModel(name=dep.name)
    db.add(db_dep)
    db.commit()
    db.refresh(db_dep)
    return db_dep

@app.get("/departements")
def list_departements(db: Session = Depends(get_db)):
    return db.query(DepartementModel).all()

@app.post("/formations")
def create_formation(form: FormationSchema, db: Session = Depends(get_db)):
    db_form = FormationModel(**form.dict())
    db.add(db_form)
    db.commit()
    db.refresh(db_form)
    return db_form

@app.get("/formations")
def list_formations(db: Session = Depends(get_db)):
    return db.query(FormationModel).all()

@app.post("/students")
def create_student(student: StudentSchema, db: Session = Depends(get_db)):
    if db.query(StudentModel).filter_by(email=student.email).first():
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    if not db.query(DepartementModel).filter_by(id=student.departement_id).first():
        raise HTTPException(status_code=400, detail="Département non trouvé")

    hashed_pw = bcrypt.hashpw(student.password.encode('utf-8'), bcrypt.gensalt())
    db_student = StudentModel(
        nom=student.nom,
        prenom=student.prenom,
        email=student.email,
        password=hashed_pw.decode('utf-8'),
        departement_id=student.departement_id
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@app.get("/students", response_model=List[StudentSchema])
def get_students(db: Session = Depends(get_db)):
    return db.query(StudentModel).all()

@app.get("/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(StudentModel).filter(StudentModel.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Étudiant introuvable")
    return student

@app.post("/login")
def login(data: dict = Body(...), db: Session = Depends(get_db)):
    user = db.query(StudentModel).filter_by(email=data["email"]).first()
    if not user or not bcrypt.checkpw(data["password"].encode(), user.password.encode()):
        raise HTTPException(status_code=401, detail="Email ou mot de passe invalide")
    return user

@app.post("/inscriptions")
def inscrire_formation(link: StudentFormationLink, db: Session = Depends(get_db)):
    if db.query(StudentFormation).filter_by(student_id=link.student_id, formation_id=link.formation_id).first():
        raise HTTPException(status_code=400, detail="Déjà inscrit à cette formation")
    inscription = StudentFormation(student_id=link.student_id, formation_id=link.formation_id)
    db.add(inscription)
    db.commit()
    return {"message": "Inscription réussie"}

@app.get("/students/{student_id}/formations")
def get_student_formations(student_id: int, db: Session = Depends(get_db)):
    student = db.query(StudentModel).filter_by(id=student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Étudiant non trouvé")
    return [ins.formation for ins in student.inscriptions]

@app.post("/scrape-books")
def scrape_books(db: Session = Depends(get_db)):
    url = "https://books.toscrape.com/catalogue/page-1.html"
    books = []

    while url:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        for book in soup.select(".product_pod"):
            title = book.h3.a["title"]
            price = float(book.select_one(".price_color").text[1:])
            availability = book.select_one(".instock.availability").text.strip()
            category = "Unknown"
            books.append(RecommendedBook(
                title=title, price=price, category=category, availability=availability
            ))

        next_page = soup.select_one("li.next a")
        url = urljoin(url, next_page["href"]) if next_page else None

    db.bulk_save_objects(books)
    db.commit()
    return {"message": f"{len(books)} livres ajoutés."}

@app.get("/recommendations")
def get_recommended_books(
    category: Optional[str] = Query(None),
    price_min: Optional[float] = Query(None),
    price_max: Optional[float] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(RecommendedBook)
    if category:
        query = query.filter(RecommendedBook.category == category)
    if price_min:
        query = query.filter(RecommendedBook.price >= price_min)
    if price_max:
        query = query.filter(RecommendedBook.price <= price_max)
    return query.all()

@app.get("/books/summary")
async def get_book_summary(book_url: str = Query(..., description="URL du livre à scraper")):
    try:
        content = scrape_book_content(book_url)
        if not content:
            raise HTTPException(status_code=404, detail="Aucun contenu trouvé")
        summary = generate_summary(content)
        return {"source_url": book_url, "summary": summary}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur AI : {str(e)}")

def scrape_book_content(url: str) -> str:
    if not url.startswith("https://books.toscrape.com/catalogue/"):
        raise ValueError("L’URL doit provenir de books.toscrape.com/catalogue/...")

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=404, detail="Livre introuvable.")
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.find("div", class_="product_main").h1.get_text(strip=True)

    description_tag = soup.find("div", id="product_description")
    if description_tag and description_tag.find_next_sibling("p"):
        description = description_tag.find_next_sibling("p").get_text(strip=True)
    else:
        description = "Pas de description disponible."

    return f"Titre : {title}\nDescription : {description}"

def generate_summary(content: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Tu es un assistant qui résume des livres."},
            {"role": "user", "content": f"Fais un résumé de ce livre :\n\n{content}"}
        ],
        temperature=0.7,
        max_tokens=150
    )
    return response.choices[0].message["content"].strip()
