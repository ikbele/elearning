from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# Modèle pour les départements
class DepartementModel(Base):
    __tablename__ = 'departements'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)

    formations = relationship("FormationModel", back_populates="departement", cascade="all, delete-orphan")

# Modèle pour les formations
class FormationModel(Base):
    __tablename__ = 'formations'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    departement_id = Column(Integer, ForeignKey('departements.id'))

    departement = relationship("DepartementModel", back_populates="formations")
    students = relationship("StudentFormation", back_populates="formation", cascade="all, delete-orphan")

# Modèle pour les étudiants
class StudentModel(Base):
    __tablename__ = 'students'

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String, index=True)
    prenom = Column(String)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    departement_id = Column(Integer, ForeignKey('departements.id'))

    departement = relationship("DepartementModel")
    inscriptions = relationship("StudentFormation", back_populates="student", cascade="all, delete-orphan")

# Modèle pour l'inscription des étudiants aux formations
class StudentFormation(Base):
    __tablename__ = 'student_formation'

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    formation_id = Column(Integer, ForeignKey('formations.id'))

    student = relationship("StudentModel", back_populates="inscriptions")
    formation = relationship("FormationModel", back_populates="students")

# Modèle pour les livres recommandés
class RecommendedBook(Base):
    __tablename__ = "recommended_books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    price = Column(Float)  # ✅ Assure-toi que cette colonne existe aussi dans ta base
    category = Column(String)
    availability = Column(String)
