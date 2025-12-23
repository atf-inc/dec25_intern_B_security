import logging
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from apps.worker.intent.schemas import EmailIntentState, IntentAnalysis
from apps.worker.intent.prompts import SYSTEM_PROMPT, SUBJECT_PROMPT, BODY_PROMPT
from apps.worker.intent.taxonomy import Intent

logger = logging.getLogger(__name__)


def get_model():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable is missing or empty.")

    return ChatGoogleGenerativeAI(
        model="models/gemini-flash-lite-latest",
        temperature=0,
        google_api_key=api_key,
    )


async def analyze_subject(state: EmailIntentState) -> dict:
    """Analyze email subject to determine intent."""
    logger.info(f"Analyzing subject: {state.subject[:50]}...")
    
    model = get_model().with_structured_output(IntentAnalysis)

    intents_list = "\n".join([f"- {i.value}" for i in Intent])

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("user", SUBJECT_PROMPT)]
    )

    chain = prompt | model
    result = await chain.ainvoke(
        {"intents_list": intents_list, "subject": state.subject}
    )
    
    logger.info(f"Subject analysis result: intent={result.intent}, confidence={result.confidence}")

    return {
        "subject_intent": result.intent,
        "subject_confidence": result.confidence,
        "subject_indicators": result.indicators,
    }


async def analyze_body(state: EmailIntentState) -> dict:
    """Analyze email body to determine intent."""
    # Truncate body if too long
    body = state.body[:2000]
    logger.info(f"Analyzing body (length={len(state.body)}, truncated={len(body)})")

    model = get_model().with_structured_output(IntentAnalysis)

    intents_list = "\n".join([f"- {i.value}" for i in Intent])

    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM_PROMPT), ("user", BODY_PROMPT)]
    )

    chain = prompt | model
    result = await chain.ainvoke({"intents_list": intents_list, "body": body})
    
    logger.info(f"Body analysis result: intent={result.intent}, confidence={result.confidence}")

    return {
        "body_intent": result.intent,
        "body_confidence": result.confidence,
        "body_indicators": result.indicators,
    }


def resolve_intent(state: EmailIntentState) -> dict:
    """Resolve final intent by merging subject and body analysis results."""
    logger.info(
        f"Resolving intent: subject={state.subject_intent}, body={state.body_intent}"
    )
    
    # Logic for merging subject and body intent
    if state.subject_intent == state.body_intent:
        # Merge unique indicators
        combined_indicators = list(
            set((state.subject_indicators or []) + (state.body_indicators or []))
        )
        result = {
            "final_intent": state.subject_intent,
            "final_confidence": max(
                state.subject_confidence or 0, state.body_confidence or 0
            ),
            "final_indicators": combined_indicators,
        }
        logger.info(f"Intent match - final: {result['final_intent']}")
        return result

    # If different, prioritize higher confidence
    if (state.subject_confidence or 0) >= (state.body_confidence or 0):
        result = {
            "final_intent": state.subject_intent,
            "final_confidence": state.subject_confidence,
            "final_indicators": state.subject_indicators,
        }
        logger.info(f"Prioritizing subject intent: {result['final_intent']}")
        return result
    else:
        result = {
            "final_intent": state.body_intent,
            "final_confidence": state.body_confidence,
            "final_indicators": state.body_indicators,
        }
        logger.info(f"Prioritizing body intent: {result['final_intent']}")
        return result
