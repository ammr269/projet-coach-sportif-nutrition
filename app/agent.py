import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict
from mistralai import Mistral
from dotenv import load_dotenv
from app.db import get_relevant_foods_and_exercises
from app.schemas import ChatRequest
from datetime import datetime

load_dotenv()

client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))

# --------------------------
# GESTION DE L'HISTORIQUE
# --------------------------
conversation_history: Dict[str, List[Dict]] = {}

def get_conversation_history(session_id: str) -> List[Dict]:
    """Récupère l'historique d'une session."""
    return conversation_history.get(session_id, [])

def add_to_history(session_id: str, role: str, content: str):
    """Ajoute un message à l'historique."""
    if session_id not in conversation_history:
        conversation_history[session_id] = []
    
    conversation_history[session_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    if len(conversation_history[session_id]) > 20:
        conversation_history[session_id] = conversation_history[session_id][-20:]

# --------------------------
# APPEL LLM AVEC RETRY
# --------------------------
async def call_llm_system(messages: list[dict], max_retries: int = 3) -> str:
    """
    Appelle Mistral avec gestion d'erreurs et retry logic.
    """
    for attempt in range(max_retries):
        try:
            response = await asyncio.to_thread(
                client.chat.complete,
                model="mistral-large-latest",
                messages=messages,
                temperature=0.7,  
                max_tokens=1500   
            )
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            if attempt == max_retries - 1:
                return f"❌ Erreur après {max_retries} tentatives: {str(e)}"
            
            await asyncio.sleep(2 ** attempt)
    
    return "Erreur inattendue lors de l'appel au LLM."

# --------------------------
# PROMPT PATH
# --------------------------
PROMPT_PATH = Path(__file__).resolve().parents[1] / "prompts" / "coach_prompt.txt"

# --------------------------
# CALCUL DES BESOINS CALORIQUES
# --------------------------
def calculate_daily_calories(profile) -> Dict:
    """
    Calcule les besoins caloriques selon la formule de Mifflin-St Jeor.
    """
    if not profile or not all([profile.age, profile.weight_kg, profile.height_cm, profile.sex]):
        return {"bmr": None, "tdee": None, "target": None}
    
    # BMR (Basal Metabolic Rate)
    if profile.sex.lower() == "homme":
        bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + 5
    else:  
        bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age - 161
    
    # TDEE (Total Daily Energy Expenditure) - activité modérée
    tdee = bmr * 1.55
    
    # Ajustement selon objectif
    target = tdee
    if profile.goal == "perte_de_poids":
        target = tdee - 500  
    elif profile.goal == "prise_de_masse":
        target = tdee + 300  
    
    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "target": round(target)
    }

# --------------------------
# DÉTECTION D'INTENTION
# --------------------------
def detect_intent(question: str) -> str:
    """
    Détecte l'intention de l'utilisateur.
    """
    q = question.lower()
    
    if any(word in q for word in ["menu", "repas", "manger", "recette", "calories"]):
        return "nutrition"
    elif any(word in q for word in ["exercice", "sport", "entraînement", "musculation", "cardio"]):
        return "exercise"
    elif any(word in q for word in ["plan", "programme", "semaine", "routine"]):
        return "program"
    else:
        return "general"

# --------------------------
# ENRICHISSEMENT DES DONNÉES RAG
# --------------------------
def enrich_rag_data(data_docs: Dict, profile) -> str:
    """
    Formate les données RAG de manière structurée et enrichie.
    """
    enriched = []
    
    # Aliments
    if data_docs.get("foods"):
        enriched.append("📊 ALIMENTS DISPONIBLES:")
        for food in data_docs["foods"]:
            tags = ", ".join(food.get("tags", []))
            enriched.append(
                f"- {food['name'].upper()}: {food['calories_per_100g']} kcal/100g "
                f"[{tags}]"
            )
    
    # Exercices
    if data_docs.get("exercises"):
        enriched.append("\n💪 EXERCICES DISPONIBLES:")
        for ex in data_docs["exercises"]:
            muscles = ", ".join(ex.get("muscles", []))
            enriched.append(
                f"- {ex['name'].upper()} ({ex['difficulty']}): cible {muscles}"
            )
    
    # Informations profil
    if profile:
        calories_info = calculate_daily_calories(profile)
        if calories_info["target"]:
            enriched.append(f"\n🎯 BESOINS CALORIQUES:")
            enriched.append(f"- Métabolisme de base: {calories_info['bmr']} kcal")
            enriched.append(f"- Dépense journalière: {calories_info['tdee']} kcal")
            enriched.append(f"- Objectif ({profile.goal}): {calories_info['target']} kcal")
    
    return "\n".join(enriched)

# --------------------------
# PROCESS CHAT PRINCIPAL (AMÉLIORÉ)
# --------------------------
async def process_chat(req: ChatRequest) -> str:
    """
    Traite la requête avec RAG amélioré + historique + contexte enrichi.
    """
    session_id = req.session_id or "default"
    
    # 1. Détection d'intention
    intent = detect_intent(req.question)
    
    # 2. Récupération RAG avec plus de résultats selon l'intention
    top_k = 15 if intent == "program" else 10
    data_docs = get_relevant_foods_and_exercises(req.question, top_k=top_k)
    
    # 3. Enrichissement des données
    enriched_data = enrich_rag_data(data_docs, req.profile)
    
    # 4. Chargement du prompt système
    if PROMPT_PATH.exists():
        prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    else:
        prompt_template = """Tu es un coach nutrition et sport expert.
Utilise UNIQUEMENT les données fournies dans {{DATA}}.
Réponds de manière structurée et personnalisée."""
    
    system_message = prompt_template.replace("{{DATA}}", enriched_data)
    
    # 5. Construction du message utilisateur avec contexte
    user_context = [f"📝 Question: {req.question}"]
    
    if req.profile:
        user_context.append(f"\n👤 Profil utilisateur:")
        user_context.append(f"- Age: {req.profile.age} ans")
        user_context.append(f"- Poids: {req.profile.weight_kg} kg")
        user_context.append(f"- Taille: {req.profile.height_cm} cm")
        user_context.append(f"- Objectif: {req.profile.goal}")
        if req.profile.allergies:
            user_context.append(f"- ⚠️ Allergies: {', '.join(req.profile.allergies)}")
    
    user_context.append(f"\n🎯 Intention détectée: {intent}")
    
    user_message = "\n".join(user_context)
    
    # 6. Récupération de l'historique
    history = get_conversation_history(session_id)
    
    # 7. Construction des messages pour le LLM
    messages = [{"role": "system", "content": system_message}]
    
    # Ajouter les 3 derniers échanges de l'historique pour contexte
    recent_history = history[-6:] if len(history) > 6 else history
    for msg in recent_history:
        if msg["role"] in ["user", "assistant"]:
            messages.append({"role": msg["role"], "content": msg["content"]})
    
    messages.append({"role": "user", "content": user_message})
    
    # 8. Appel au LLM avec retry
    llm_reply = await call_llm_system(messages)
    
    # 9. Post-traitement
    final_reply = apply_business_rules(llm_reply, req, intent)
    
    # 10. Sauvegarde dans l'historique
    add_to_history(session_id, "user", req.question)
    add_to_history(session_id, "assistant", final_reply)
    
    return final_reply

# --------------------------
# RÈGLES MÉTIER AMÉLIORÉES
# --------------------------
def apply_business_rules(reply: str, req: ChatRequest, intent: str) -> str:
    """
    Applique des règles métier et valide la réponse.
    """
    # 1. Filtrage des allergènes
    if req.profile and req.profile.allergies:
        for allergen in req.profile.allergies:
            if allergen.lower() in reply.lower():
                reply += f"\n\n⚠️ ATTENTION: Ce plan contient '{allergen}' (allergie détectée). Remplace-le par une alternative."
    
    # 2. Validation des mots interdits
    forbidden = ["médicament", "dopant", "stéroïde", "anabolisant"]
    for word in forbidden:
        if word in reply.lower():
            return "❌ Je ne peux pas recommander de substances médicamenteuses ou dopantes. Consulte un médecin pour ce type de conseil."
    
    # 3. Vérification réponse vide
    if not reply or reply.strip() == "" or len(reply) < 20:
        return "Je n'ai pas suffisamment d'informations pour répondre de manière complète. Peux-tu reformuler ta question ?"
    
    # 4. Ajout de disclaimer selon l'intention
    if intent == "nutrition":
        reply += "\n\n💡 Conseil: Ces recommandations sont générales. Consulte un nutritionniste pour un suivi personnalisé."
    elif intent == "exercise":
        reply += "\n\n💡 Conseil: Commence progressivement et écoute ton corps. En cas de douleur, consulte un professionnel."
    
    return reply