"""Vision analysis service: analyze webcam frames using Mistral Vision (Pixtral)."""

import asyncio
import base64
import json
import logging

from mistralai import Mistral
from mistralai.models import SDKError

from app.config import get_settings
from app.schemas import VisualAnalysisReport, VisualObservation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt for visual analysis
# ---------------------------------------------------------------------------
VISUAL_ANALYSIS_PROMPT = """Tu es un coach expert en communication non-verbale et en entretiens d'embauche.

On te fournit {n_frames} captures d'écran prises à intervalles réguliers pendant un entretien d'embauche vidéo.
Les images sont dans l'ordre chronologique : la première correspond au DÉBUT de l'entretien, la dernière à la FIN.

Analyse attentivement les images et produis un rapport structuré au format JSON strict correspondant au schéma fourni.

CRITÈRES D'ANALYSE (chacun doit apparaître dans tes observations) :
1. **Expressions faciales** : sourires, neutralité, nervosité, froncements de sourcils, micro-expressions. Compare le début et la fin de l'entretien — le candidat s'est-il détendu ou crispé au fil du temps ?
2. **Posture** : droite, détendue, voûtée, agitée, bras croisés, mains. Note les changements de posture au cours de l'entretien.
3. **Contact visuel** : regarde la caméra (= contact visuel), regarde ailleurs, yeux baissés, lit ses notes. Évalue la fréquence et la constance du contact visuel.
4. **Confiance générale** : dégage de l'assurance, hésitant, stressé. Évalue l'ÉVOLUTION de la confiance entre les premières et les dernières images.
5. **Environnement** : éclairage, cadrage, arrière-plan — sont-ils professionnels et appropriés pour un entretien ?

BARÈME DU SCORE DE CONFIANCE :
- 0-3 : Très nerveux, posture fermée, pas de contact visuel
- 4-5 : Hésitant, quelques signaux positifs mais inconstants
- 6-7 : Correct, présence acceptable avec des axes d'amélioration
- 8-9 : Bon, langage corporel positif et constant
- 10 : Excellent, communication non-verbale irréprochable

CONSIGNES :
- Fournis exactement 5 observations (une par critère ci-dessus).
- Pour chaque observation, mentionne ce que tu vois CONCRÈTEMENT dans les images (pas de généralités).
- Note l'évolution au cours de l'entretien (début vs milieu vs fin).
- Propose 3-4 recommandations actionnables et spécifiques.
- Rédige en français.
"""


def _get_client() -> Mistral:
    """Instantiate a Mistral client."""
    return Mistral(api_key=get_settings().mistral_api_key)


async def analyze_visual(frames_b64: list[str], job_offer: str = "") -> VisualAnalysisReport:
    """Analyze webcam frames using Mistral Vision and return a structured report.

    Args:
        frames_b64: List of base64-encoded JPEG images.
        job_offer: Optional job offer text for context.

    Returns:
        VisualAnalysisReport with observations and recommendations.
    """
    client = _get_client()

    # Build multimodal content: text prompt + images
    content_parts = [
        {
            "type": "text",
            "text": f"Analyse les images suivantes prises pendant un entretien d'embauche."
                    + (f"\n\nContexte de l'offre : {job_offer[:500]}" if job_offer else ""),
        }
    ]

    # Add each frame as an image_url with base64 data URI
    for i, frame_b64 in enumerate(frames_b64):
        # Ensure the base64 string has the proper data URI prefix
        if not frame_b64.startswith("data:"):
            frame_b64 = f"data:image/jpeg;base64,{frame_b64}"

        content_parts.append({
            "type": "image_url",
            "image_url": {"url": frame_b64},
        })

    system_prompt = VISUAL_ANALYSIS_PROMPT.format(n_frames=len(frames_b64))

    # Include JSON schema in the prompt so the model knows the expected format
    report_schema = VisualAnalysisReport.model_json_schema()
    schema_instruction = (
        "\n\nRéponds UNIQUEMENT avec un objet JSON valide respectant ce schéma :\n"
        + json.dumps(report_schema, ensure_ascii=False, indent=2)
    )

    logger.info("Analyzing %d webcam frames with Vision model (%s)...", len(frames_b64), get_settings().vision_model)

    max_retries = 4
    for attempt in range(max_retries):
        try:
            response = await client.chat.complete_async(
                model=get_settings().vision_model,
                messages=[
                    {"role": "system", "content": system_prompt + schema_instruction},
                    {"role": "user", "content": content_parts},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            raw = response.choices[0].message.content
            data = json.loads(raw)
            report = VisualAnalysisReport.model_validate(data)

            logger.info("Visual analysis complete (confidence: %d/10)", report.confidence_score)
            return report

        except SDKError as e:
            if e.status_code == 429 and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10
                logger.warning(f"Vision rate limit hit. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue
            raise
