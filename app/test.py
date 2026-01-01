import requests

def test_chat_api():
    url = "http://127.0.0.1:8000/chat"
    payload = {
        "question": "Quels exercices pour débuter ?",
        "profile": {
            "age": 25,
            "weight_kg": 65,
            "height_cm": 170,
            "sex": "femme",
            "goal": "maintien",
            "allergies": []
        }
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Statut:", response.status_code)
        print("Réponse JSON:", response.json())
    except requests.exceptions.RequestException as e:
        print("Erreur lors de l'appel API:", e)

if __name__ == "__main__":
    test_chat_api()
