from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import StudentModel
import bcrypt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
import time
import requests

client = TestClient(app)

# Crée un utilisateur test s'il n'existe pas
def setup_test_user():
    db = SessionLocal()
    existing = db.query(StudentModel).filter_by(email="testuser@example.com").first()
    if not existing:
        hashed_pw = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = StudentModel(
            nom="Test",
            prenom="User",
            email="testuser@example.com",
            password=hashed_pw,
            departement_id=1  # ⚠️ Assurez-vous qu’un département avec ID 1 existe !
        )
        db.add(user)
        db.commit()
    db.close()

# Test d'intégration backend
def test_login_backend():
    setup_test_user()

    login_data = {
        "email": "testuser@example.com",
        "password": "password123"
    }

    response = client.post("/login", json=login_data)

    assert response.status_code == 200
    assert response.json()["email"] == login_data["email"]
    assert "id" in response.json()

# Test de bout en bout avec Selenium
def test_login_selenium():
    # ⚠️ Change ce chemin selon ton système
    service = Service("C:/path/to/chromedriver.exe")
    driver = webdriver.Chrome(service=service)

    try:
        # Ouvre la page de connexion Next.js
        driver.get("http://localhost:3007/login")

        # Remplit les champs (assure-toi que les IDs "email" et "password" existent)
        email_input = driver.find_element(By.ID, "email")
        password_input = driver.find_element(By.ID, "password")

        email_input.send_keys("testuser@example.com")
        password_input.send_keys("password123")
        password_input.send_keys(Keys.RETURN)

        # Attente de la redirection vers le tableau de bord
        time.sleep(3)

        assert "Dashboard" in driver.page_source  # Ajuste selon ton composant Next.js

        # Vérifie aussi que l'API backend répond toujours bien
        response = requests.post("http://localhost:8082/login", json={
            "email": "testuser@example.com",
            "password": "password123"
        })

        assert response.status_code == 200
        assert response.json()["email"] == "testuser@example.com"

    finally:
        driver.quit()
