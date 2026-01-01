import streamlit as st
import requests
from app.schemas import UserProfile


API_URL = st.secrets.get('API_URL', 'http://localhost:8000/chat')

st.title('Coach Nutrition & Sport')
st.write(f"API_URL utilisée : {API_URL}")

# -------------------------
# FORMULAIRE PROFIL
# -------------------------
# with st.form('profile'):
#     age = st.number_input('Age', min_value=10, max_value=120, value=30)
#     weight = st.number_input('Poids (kg)', min_value=20.0, max_value=300.0, value=70.0)
#     height = st.number_input('Taille (cm)', min_value=100.0, max_value=230.0, value=175.0)
#     goal = st.selectbox('Objectif', ['perte_de_poids', 'maintien', 'prise_de_masse'])
#     allergies = st.text_input('Allergies (séparées par des virgules)')
#     submitted = st.form_submit_button('Sauvegarder le profil')

# if submitted:
#     st.session_state['profile'] = {
#         'age': int(age),
#         'weight_kg': float(weight),
#         'height_cm': float(height),
#         'goal': goal,
#         'allergies': [a.strip() for a in allergies.split(',') if a.strip()]
#     }
#     st.success('Profil sauvegardé')

with st.form('profile_form'):
    age = st.number_input('Age', min_value=10, max_value=120, value=30)
    weight = st.number_input('Poids (kg)', min_value=20.0, max_value=300.0, value=70.0)
    height = st.number_input('Taille (cm)', min_value=100.0, max_value=230.0, value=175.0)
    goal = st.selectbox('Objectif', ['perte_de_poids', 'maintien', 'prise_de_masse'])
    allergies = st.text_input('Allergies (séparées par des virgules)')
    submitted = st.form_submit_button('Sauvegarder le profil')

if submitted:
    st.session_state['profile'] = {
        'age': int(age),
        'weight_kg': float(weight),
        'height_cm': float(height),
        'goal': goal,
        'allergies': [a.strip() for a in allergies.split(',') if a.strip()]
    }
    st.success('Profil sauvegardé')


# Affichage du profil sauvegardé
if 'profile' in st.session_state:
    st.write('Profil actuel :')
    st.json(st.session_state['profile'])

# -------------------------
# QUESTION AU COACH
# -------------------------
question = st.text_input('Pose ta question au coach', '')

if st.button('Envoyer') and question.strip():
    payload = {
        'question': question,
        'profile': st.session_state.get('profile', None)
    }

    with st.spinner('Génération en cours...'):
        try:
            resp = requests.post(API_URL, json=payload, timeout=30)

            if resp.status_code == 200:
                data = resp.json()
                st.markdown('### Réponse du coach')
                st.write(data.get('reply'))
            else:
                st.error(f"Erreur API: {resp.status_code} - {resp.text}")

        except Exception as e:
            st.error(f"Erreur lors de l'appel API : {e}")
