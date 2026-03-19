"""Interview chatbot service: mock interview with Mistral Small."""

import asyncio
import copy
import json
import logging
from typing import Any

from mistralai import Mistral
from mistralai.models import SDKError

from app.config import get_settings
from app.schemas import ChatMessage, InterviewFeedback, InterviewChatResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

RECRUITER_SYSTEM_PROMPT = """Tu es un recruteur senior exigeant et direct. Tu ne fais pas de cadeaux.
Tu fais passer un entretien d'embauche/stage à un candidat.

Voici le CV du candidat :
---
{cv_text}
---

Voici l'offre à laquelle il postule :
---
{job_offer}
---

STRUCTURE DE L'ENTRETIEN (suis cet ordre) :
1. ACCROCHE (1 question) : Présente-toi comme recruteur (prénom, poste) et demande au candidat de se présenter brièvement et d'expliquer sa motivation pour ce poste précis.
2. PARCOURS (1-2 questions) : Creuse un élément spécifique du CV — un projet, une expérience, un choix d'orientation. Demande des détails concrets, des chiffres, des résultats.
3. TECHNIQUE (2-3 questions) : Pose des questions techniques directement liées aux compétences requises dans l'offre. Adapte la difficulté au niveau du candidat (stage vs senior). Inclus au moins une mise en situation ("Comment ferais-tu si…").
4. SOFT SKILLS (1-2 questions) : Teste la gestion du stress, le travail d'équipe, la résolution de conflits ou l'organisation. Utilise des situations concrètes.
5. CLOSING (1 question) : Demande au candidat s'il a des questions, puis conclus l'entretien.

COMPORTEMENT DU RECRUTEUR :
- UNE SEULE question par message, jamais plusieurs.
- REBONDIS sur la réponse du candidat : cite un mot ou une idée qu'il a mentionné et approfondis. Ne passe pas mécaniquement à la question suivante.
- Si la réponse est vague, courte ou hors-sujet : relance fermement. Dis clairement que tu attends plus de détails. Exemples : "Tu peux être plus concret ?", "Donne-moi un exemple précis.", "Ça reste très général, qu'est-ce que tu as fait concrètement ?"
- Si la réponse est fausse ou incohérente : signale-le poliment mais clairement.
- Tutoie le candidat. Sois naturel et conversationnel.
- Ne fournis JAMAIS d'explication méta, d'excuse ou de commentaire hors personnage.
- Ton message doit contenir UNIQUEMENT le texte de l'entretien (pas de "Question 3 :", pas de catégorie).
- Quand tu estimes que l'entretien est terminé (après 6-9 questions bien couvertes), termine ton message par la phrase exacte : [ENTRETIEN_TERMINE]
- Commence par te présenter et poser ta première question.
"""

FEEDBACK_SYSTEM_PROMPT = """Tu es un coach en recrutement expert et exigeant. Tu évalues un candidat après un entretien.

Voici le CV du candidat :
---
{cv_text}
---

Voici l'offre à laquelle il postule :
---
{job_offer}
---

GRILLE D'ÉVALUATION (utilise ces 6 critères obligatoirement) :
1. **Présentation et motivation** (coeff 1) : Le candidat sait-il se présenter clairement ? Sa motivation pour le poste est-elle crédible et argumentée ?
2. **Compétences techniques** (coeff 2) : Maîtrise-t-il les compétences clés de l'offre ? Ses réponses techniques sont-elles précises et justes ?
3. **Exemples concrets** (coeff 2) : Donne-t-il des exemples tirés de son expérience ? Utilise-t-il des chiffres, des résultats, des situations vécues ?
4. **Communication** (coeff 1) : S'exprime-t-il clairement ? Ses réponses sont-elles structurées et de longueur appropriée ?
5. **Capacité de réflexion** (coeff 1) : Sait-il réfléchir à voix haute, analyser un problème, gérer l'incertitude ?
6. **Soft skills** (coeff 1) : Travail d'équipe, adaptabilité, gestion du stress — a-t-il su les démontrer ?

BARÈME :
- 0-3/10 : Insuffisant — réponses absentes, incohérentes ou hors-sujet sur la majorité des critères.
- 4-5/10 : Faible — quelques éléments corrects mais manque flagrant de préparation ou de contenu.
- 6/10 : Passable — les bases sont là mais trop de réponses vagues ou superficielles.
- 7/10 : Correct — bonne prestation avec quelques faiblesses identifiables.
- 8/10 : Bon — réponses solides, bien argumentées, rares points faibles.
- 9-10/10 : Excellent — candidat exceptionnel, réponses percutantes et complètes sur tous les critères.

CONSIGNES :
- Évalue CHAQUE critère de la grille. Chaque critère doit apparaître soit dans strengths soit dans improvements.
- Sois direct et honnête. Ne mets pas 7/10 par défaut — utilise tout le barème.
- Le score final est la moyenne pondérée des critères (les coefficients sont indiqués).
- Dans le summary, commence par un verdict en une phrase ("Prestation convaincante" / "Entretien insuffisant" / etc.).
- Dans advice, donne UN conseil actionnable et précis, pas une généralité.
- Génère le résultat au format JSON strict correspondant au schéma fourni.
"""

# Maximum characters sent to the API to stay within token limits
_CV_MAX_CHARS = 5000
_OFFER_MAX_CHARS = 3000


def _get_client() -> Mistral:
    """Instantiate a Mistral client."""
    return Mistral(api_key=get_settings().mistral_api_key)


def _truncate_context(cv_text: str, job_offer: str) -> tuple[str, str]:
    """Truncate CV and job offer to avoid exceeding token limits."""
    return cv_text[:_CV_MAX_CHARS], job_offer[:_OFFER_MAX_CHARS]


async def _call_with_retry(client: Mistral, max_retries: int = 3, **kwargs: Any) -> Any:
    """Call client.chat.complete_async with exponential backoff on rate limits."""
    for attempt in range(max_retries):
        try:
            return await client.chat.complete_async(**kwargs)
        except SDKError as e:
            if e.status_code == 429 and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.warning("Rate limit hit. Retrying in %ds (attempt %d/%d)...", wait_time, attempt + 1, max_retries)
                await asyncio.sleep(wait_time)
                continue
            raise


# ---------------------------------------------------------------------------
# 1. Start interview — first question
# ---------------------------------------------------------------------------
async def start_interview(cv_text: str, job_offer: str) -> tuple[str, str]:
    """Start a new mock interview. Returns (system_context, first_question)."""
    client = _get_client()
    truncated_cv, truncated_offer = _truncate_context(cv_text, job_offer)

    system_prompt = RECRUITER_SYSTEM_PROMPT.format(cv_text=truncated_cv, job_offer=truncated_offer)

    logger.info("Starting interview (CV: %d chars, offer: %d chars)", len(cv_text), len(job_offer))

    response = await _call_with_retry(
        client,
        model=get_settings().text_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Bonjour, je suis prêt pour l'entretien."},
        ],
        temperature=0.7,
    )

    first_question = response.choices[0].message.content.strip()
    system_context = f"Entretien pour : {job_offer[:120]}…"
    logger.info("Interview started, first question generated")
    return system_context, first_question


# ---------------------------------------------------------------------------
# 2. Chat — continue the interview
# ---------------------------------------------------------------------------
async def chat_interview(cv_text: str, job_offer: str, messages: list[ChatMessage]) -> InterviewChatResponse:
    """Process the next turn of the interview conversation."""
    client = _get_client()
    truncated_cv, truncated_offer = _truncate_context(cv_text, job_offer)

    system_prompt = RECRUITER_SYSTEM_PROMPT.format(cv_text=truncated_cv, job_offer=truncated_offer)

    api_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Bonjour, je suis prêt pour l'entretien."},
        *[{"role": msg.role, "content": msg.content} for msg in messages],
    ]

    logger.info("Interview chat turn (history: %d messages)", len(messages))

    response = await _call_with_retry(
        client,
        model=get_settings().text_model,
        messages=api_messages,
        temperature=0.7,
    )

    reply = response.choices[0].message.content.strip()
    is_final = "[ENTRETIEN_TERMINE]" in reply
    if is_final:
        reply = reply.replace("[ENTRETIEN_TERMINE]", "").strip()

    logger.info("Interview chat reply generated (is_final=%s)", is_final)
    return InterviewChatResponse(reply=reply, is_final=is_final)


# ---------------------------------------------------------------------------
# 3. Feedback — generate structured report
# ---------------------------------------------------------------------------
async def generate_feedback(cv_text: str, job_offer: str, messages: list[ChatMessage]) -> InterviewFeedback:
    """Generate a structured feedback report from the full interview."""
    client = _get_client()
    truncated_cv, truncated_offer = _truncate_context(cv_text, job_offer)

    system_prompt = FEEDBACK_SYSTEM_PROMPT.format(cv_text=truncated_cv, job_offer=truncated_offer)

    conversation = "\n\n".join(
        f"{'Recruteur' if m.role == 'assistant' else 'Candidat'} : {m.content}"
        for m in messages
    )

    # Exclude visual_report from schema — it comes from webcam, not from the LLM
    feedback_schema = copy.deepcopy(InterviewFeedback.model_json_schema())
    feedback_schema.get("properties", {}).pop("visual_report", None)
    for key in ("VisualAnalysisReport", "VisualObservation"):
        feedback_schema.get("$defs", {}).pop(key, None)

    logger.info("Generating interview feedback (%d messages)", len(messages))

    response = await _call_with_retry(
        client,
        model=get_settings().text_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Voici la transcription de l'entretien :\n\n{conversation}"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "interview_feedback",
                "schema": feedback_schema,
                "strict": True,
            },
        },
        temperature=0.3,
    )

    raw = response.choices[0].message.content
    feedback = InterviewFeedback.model_validate(json.loads(raw))
    logger.info("Feedback generated (score: %d/10)", feedback.score)
    return feedback
