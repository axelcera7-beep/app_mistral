"""Interview chatbot service: mock interview with Mistral Small."""

import json
import logging

from mistralai import Mistral

from app.config import get_settings
from app.schemas import (
    ChatMessage,
    FeedbackPoint,
    InterviewFeedback,
    InterviewChatResponse,
)

logger = logging.getLogger(__name__)

TEXT_MODEL = "mistral-small-latest"

# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

RECRUITER_SYSTEM_PROMPT = """Tu es un recruteur professionnel, bienveillant mais exigeant.
Tu fais passer un entretien d'embauche/stage à un candidat.

Voici le CV du candidat :
---
{cv_text}
---

Voici l'offre à laquelle il postule :
---
{job_offer}
---

Consignes :
- Pose entre 6 et 8 questions au total, une à la fois.
- Varie entre questions techniques, de motivation, de soft skills et de mise en situation.
- Adapte tes questions au CV du candidat ET à l'offre.
- Si la réponse est vague ou incomplète, relance poliment pour approfondir.
- Sois naturel, conversationnel, tutoie le candidat.
- Ne pose PAS toutes les questions d'un coup — une seule question par message.
- Quand tu estimes que l'entretien est terminé (après 6-8 questions bien couvertes), termine ton message par la phrase exacte : [ENTRETIEN_TERMINE]
- Commence par te présenter brièvement et poser ta première question.
"""

FEEDBACK_SYSTEM_PROMPT = """Tu es un coach en recrutement expert.
On te fournit la transcription complète d'un entretien d'embauche entre un recruteur et un candidat.

Voici le CV du candidat :
---
{cv_text}
---

Voici l'offre à laquelle il postule :
---
{job_offer}
---

Analyse l'entretien et génère un compte rendu structuré au format JSON strict correspondant au schéma fourni.
Sois précis, constructif et bienveillant dans tes commentaires.
Attribue une note sur 10 qui reflète la performance globale du candidat.
"""


def _get_client() -> Mistral:
    """Instantiate a Mistral client."""
    return Mistral(api_key=get_settings().mistral_api_key)


# ---------------------------------------------------------------------------
# 1. Start interview — first question
# ---------------------------------------------------------------------------
async def start_interview(cv_text: str, job_offer: str) -> tuple[str, str]:
    """Start a new mock interview. Returns (system_context, first_question)."""
    client = _get_client()

    system_prompt = RECRUITER_SYSTEM_PROMPT.format(
        cv_text=cv_text, job_offer=job_offer
    )

    logger.info("Starting interview (CV: %d chars, offer: %d chars)", len(cv_text), len(job_offer))

    response = await client.chat.complete_async(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Bonjour, je suis prêt pour l'entretien."},
        ],
        temperature=0.7,
    )

    first_question = response.choices[0].message.content.strip()

    # Build a short context summary for the frontend
    system_context = f"Entretien pour : {job_offer[:120]}…"

    logger.info("Interview started, first question generated")
    return system_context, first_question


# ---------------------------------------------------------------------------
# 2. Chat — continue the interview
# ---------------------------------------------------------------------------
async def chat_interview(
    cv_text: str, job_offer: str, messages: list[ChatMessage]
) -> InterviewChatResponse:
    """Process the next turn of the interview conversation."""
    client = _get_client()

    system_prompt = RECRUITER_SYSTEM_PROMPT.format(
        cv_text=cv_text, job_offer=job_offer
    )

    # Build messages list for the API
    api_messages = [{"role": "system", "content": system_prompt}]

    # The very first user message is the implicit "ready" message
    api_messages.append({"role": "user", "content": "Bonjour, je suis prêt pour l'entretien."})

    # Add conversation history
    for msg in messages:
        api_messages.append({"role": msg.role, "content": msg.content})

    logger.info("Interview chat turn (history: %d messages)", len(messages))

    response = await client.chat.complete_async(
        model=TEXT_MODEL,
        messages=api_messages,
        temperature=0.7,
    )

    reply = response.choices[0].message.content.strip()

    # Check if the recruiter signals end of interview
    is_final = "[ENTRETIEN_TERMINE]" in reply
    if is_final:
        reply = reply.replace("[ENTRETIEN_TERMINE]", "").strip()

    logger.info("Interview chat reply generated (is_final=%s)", is_final)
    return InterviewChatResponse(reply=reply, is_final=is_final)


# ---------------------------------------------------------------------------
# 3. Feedback — generate structured report
# ---------------------------------------------------------------------------
async def generate_feedback(
    cv_text: str, job_offer: str, messages: list[ChatMessage]
) -> InterviewFeedback:
    """Generate a structured feedback report from the full interview."""
    client = _get_client()

    system_prompt = FEEDBACK_SYSTEM_PROMPT.format(
        cv_text=cv_text, job_offer=job_offer
    )

    # Build the full conversation as text for analysis
    conversation = "\n\n".join(
        f"{'Recruteur' if m.role == 'assistant' else 'Candidat'} : {m.content}"
        for m in messages
    )

    # JSON schema for structured output
    feedback_schema = InterviewFeedback.model_json_schema()

    logger.info("Generating interview feedback (%d messages)", len(messages))

    response = await client.chat.complete_async(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Voici la transcription de l'entretien :\n\n{conversation}",
            },
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
    data = json.loads(raw)
    feedback = InterviewFeedback.model_validate(data)

    logger.info("Feedback generated (score: %d/10)", feedback.score)
    return feedback
