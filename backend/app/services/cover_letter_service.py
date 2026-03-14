"""Mistral AI service for generating personalized cover letters."""

import logging

from mistralai import Mistral
from mistralai.models import UserMessage, SystemMessage

from app.config import get_settings
from app.schemas import CoverLetterResponse

from datetime import datetime

logger = logging.getLogger(__name__)

# System prompt for mistral-large
COVER_LETTER_SYSTEM_PROMPT = """
Tu es un expert RH et un rédacteur professionnel spécialisé dans les lettres de motivation.
Ton but est de rédiger une lettre de motivation sur-mesure, convaincante et naturelle, prête à l'envoi.

RÈGLES ABSOLUES - SOUS PEINE DE REJET :
1. N'UTILISE JAMAIS de textes entre crochets, parenthèses ou de placeholders textuels (ex: [Nom de l'entreprise], [Date]).
2. FORMAT COMPLET OBLIGATOIRE : Tu dois impérativement inclure un en-tête professionnel complet au début de la lettre :
   - Coordonnées de l'expéditeur (extraites du CV : Nom, Email, Téléphone, Adresse).
   - Coordonnées du destinataire (extraites de l'offre : Nom de l'entreprise, Adresse). Si l'adresse de l'entreprise manque, mets juste le nom de l'entreprise.
   - Lieu et Date (utilise la date du jour fournie dans les données).
   - Objet de la lettre (ex: Objet : Candidature pour le poste de...).
3. Trouve le nom de l'entreprise DANS L'OFFRE. Si le nom de l'entreprise est introuvable, utilise une formule générique fluide comme "votre entreprise".
4. Écris en Français.
5. Ne laisse aucun élément à remplir par le candidat. La lettre générée doit pouvoir être copiée-collée et envoyée à la seconde sans aucune retouche.

MÉTHODOLOGIE :
- Analyse le CV pour comprendre le parcours du candidat.
- Analyse l'offre pour cerner les besoins.
- Mets en avant 1 ou 2 correspondances parfaites entre le profil et le poste.
- Si des EXEMPLES DE STYLE sont fournis, adopte IMMÉDIATEMENT ce tone of voice exact (formel, direct, créatif, concis, etc.).
"""

async def generate_cover_letter_text(
    cv_text: str,
    job_offer: str,
    language: str = "français",
    examples: list[str] = None
) -> CoverLetterResponse:
    """
    Generate a highly personalized cover letter using Mistral Large.
    Optionally mimics the style of provided examples.
    """
    settings = get_settings()
    model = "mistral-large-latest"
    
    client = Mistral(api_key=settings.mistral_api_key)
    
    current_date = datetime.now().strftime("%d %B %Y")
    
    user_content = (
        f"Tu DOIS ABSOLUMENT rédiger cette lettre en : {language.upper()}.\n\n"
        f"Date du jour : {current_date}\n\n"
        f"Voici le profil du candidat (CV):\n{cv_text}\n\n"
        f"---\nVoici l'offre pour laquelle le candidat postule:\n{job_offer}\n\n---\n"
    )
    
    if examples and len(examples) > 0:
        user_content += "Voici quelques EXEMPLES de lettres précédemment écrites par le candidat. "
        user_content += "Analyse leur style et IMITE CE STYLE pour la nouvelle lettre :\n\n"
        for i, ex in enumerate(examples, 1):
            user_content += f"EXEMPLE {i}:\n{ex}\n\n"
            
    user_content += (
        "Maintenant, rédige la lettre de motivation finale. "
        "En plus de la lettre, fournis un court résumé (summary) expliquant tes choix de rédaction."
    )
    
    messages = [
        SystemMessage(content=COVER_LETTER_SYSTEM_PROMPT),
        UserMessage(content=user_content),
    ]
    
    logger.info("Generating cover letter using Mistral API...")
    
    try:
        chat_response = await client.chat.parse_async(
            model=model,
            messages=messages,
            response_format=CoverLetterResponse,
        )
        
        return chat_response.choices[0].message.parsed
        
    except Exception as exc:
        logger.exception("Erreur lors de la génération de la lettre de motivation via Mistral API")
        raise

async def revise_cover_letter_text(
    current_letter: str,
    instructions: str,
    language: str = "français"
) -> CoverLetterResponse:
    """
    Take an existing cover letter and user feedback to generate a revised version.
    """
    settings = get_settings()
    model = "mistral-large-latest"
    client = Mistral(api_key=settings.mistral_api_key)
    
    system_prompt = (
        "Tu es un rédacteur professionnel et un expert RH.\n\n"
        "RÈGLES ABSOLUES - SOUS PEINE DE REJET :\n"
        "1. N'UTILISE JAMAIS de textes entre crochets, parenthèses ou de placeholders textuels (ex: [Nom de l'entreprise], [Date]).\n"
        "2. FORMAT COMPLET OBLIGATOIRE : Garde bien l'en-tête, la structure et la mise en forme de la lettre existante.\n"
        "3. Ne laisse aucun élément à remplir par le candidat. La lettre générée doit pouvoir être copiée-collée et envoyée à la seconde sans aucune retouche.\n"
    )
    
    user_content = (
        f"Tu DOIS ABSOLUMENT rédiger cette lettre en : {language.upper()}.\n\n"
        "Voici la lettre de motivation actuelle :\n"
        f"{current_letter}\n\n"
        "---\n"
        "Voici les modifications demandées par l'utilisateur :\n"
        f"{instructions}\n\n"
        "---\n"
        "Maintenant, réécris entièrement la lettre en appliquant ces modifications avec soin. "
        "Conserve le reste de la lettre (les bons éléments) intacts si la consigne ne demande pas de les changer. "
        "Fournis également un bref résumé (summary) expliquant ce que tu as modifié."
    )
    
    messages = [
        SystemMessage(content=system_prompt),
        UserMessage(content=user_content),
    ]
    
    logger.info("Revising cover letter using Mistral API...")
    
    try:
        chat_response = await client.chat.parse_async(
            model=model,
            messages=messages,
            response_format=CoverLetterResponse,
        )
        return chat_response.choices[0].message.parsed
    except Exception as exc:
        logger.exception("Erreur lors de la révision de la lettre de motivation via Mistral API")
        raise
