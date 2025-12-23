"""
Gemini AI Fallback for URL Analysis.

When the Analysis Worker returns verdict: "unknown", this module uses
Gemini 1.5 Flash to analyze URLs for phishing patterns.
"""

import os
import logging
import asyncio
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


class Verdict(str, Enum):
    """Possible URL analysis verdicts."""
    MALICIOUS = "malicious"
    SAFE = "safe"
    UNKNOWN = "unknown"


class URLAnalysisResult(BaseModel):
    """Structured output for URL analysis."""
    verdict: Literal["malicious", "safe"] = Field(
        description="The security verdict for the analyzed URLs"
    )
    reason: str = Field(
        description="Detailed explanation of why the URLs are considered malicious or safe"
    )


SYSTEM_PROMPT = """You are a Cyber Threat Analyst specializing in phishing detection.
Analyze the provided URLs for security threats.

Look for these patterns:
1. TYPOSQUATTING: Misspelled brand names (paypa1.com, amaz0n.com, g00gle.com)
2. SUSPICIOUS TLDs: Unusual domains (.xyz, .top, .click, .info, .work)
3. DECEPTIVE SUBDOMAINS: Legitimate-looking subdomains on malicious domains (login-paypal.evil.com)
4. URL SHORTENERS: Links hiding destinations (bit.ly, tinyurl, t.co)
5. IP-BASED URLS: Direct IP addresses instead of domain names
6. EXCESSIVE SUBDOMAINS: Many subdomain levels (secure.login.verify.account.example.com)
7. SUSPICIOUS PATHS: Paths containing words like "login", "verify", "update", "secure" combined with brand names

Be conservative - if in doubt, mark as malicious. User safety is paramount."""

USER_PROMPT = """Analyze these URLs for phishing or malicious content:

{urls_text}"""


def get_model() -> ChatGoogleGenerativeAI:
    """
    Get a configured ChatGoogleGenerativeAI model.
    
    Returns:
        Configured LangChain Gemini model
        
    Raises:
        RuntimeError: If GOOGLE_API_KEY is not set
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY environment variable is missing or empty.")
    
    return ChatGoogleGenerativeAI(
        model="models/gemini-flash-lite-latest",
        temperature=0.1,  # Low temperature for consistent security decisions
        google_api_key=api_key,
    )


def sanitize_url_for_logs(url: str) -> str:
    """
    Sanitize URL for safe logging (prevent accidental clicks).
    Replaces '.' with '[.]' in the URL.
    
    Args:
        url: Raw URL string
        
    Returns:
        Sanitized URL safe for logs
    """
    return url.replace('.', '[.]')


async def analyze_urls(urls: list[str]) -> tuple[str, str]:
    """
    Analyze URLs using Gemini AI for phishing detection with retry logic.
    
    Args:
        urls: List of URLs to analyze
        
    Returns:
        Tuple of (verdict, reason) where verdict is "malicious", "safe", or "unknown"
    """
    if not urls:
        return Verdict.SAFE.value, "No URLs to analyze"
    
    # Check if API key is available
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY not set. AI fallback will be unavailable.")
        return Verdict.UNKNOWN.value, "AI analysis unavailable (missing key)"
    
    # Retry logic
    max_retries = 3
    base_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                logger.info(f"Gemini retry attempt {attempt + 1}/{max_retries}")
            
            # Format URLs for analysis (limit to 10 URLs)
            urls_text = "\n".join([f"- {url}" for url in urls[:10]])
            
            logger.info(
                f"Sending {len(urls)} URLs to Gemini for analysis",
                extra={"urls_sanitized": [sanitize_url_for_logs(u) for u in urls[:5]]}
            )
            
            # Get model with structured output
            model = get_model().with_structured_output(URLAnalysisResult)
            
            # Create prompt
            prompt = ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("user", USER_PROMPT)
            ])
            
            # Create chain and invoke
            chain = prompt | model
            result = await chain.ainvoke({"urls_text": urls_text})
            
            logger.info(
                f"Gemini analysis complete",
                extra={"verdict": result.verdict, "reason": result.reason[:100]}
            )
            
            return result.verdict, result.reason
            
        except Exception as e:
            logger.error(f"Gemini API call failed (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                # Exhausted retries
                return Verdict.UNKNOWN.value, f"AI analysis failed after {max_retries} attempts: {str(e)[:100]}"
    
    return Verdict.UNKNOWN.value, "AI analysis loop error"


async def is_gemini_available() -> bool:
    """
    Check if Gemini API is available and configured.
    
    Returns:
        True if Gemini is ready to use
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return False
    
    try:
        # Try to initialize model to verify configuration
        get_model()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Gemini model: {e}")
        return False
