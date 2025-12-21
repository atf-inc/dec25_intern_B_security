"""
Gemini AI Fallback for URL Analysis.

When the Decision Agent returns verdict: "unknown", this module uses
Gemini 1.5 Flash to analyze URLs for phishing patterns.
"""

import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy initialization of Gemini model
_model = None

SYSTEM_INSTRUCTION = """You are a Cyber Threat Analyst specializing in phishing detection.
Analyze the provided URLs for security threats.

Look for these patterns:
1. TYPOSQUATTING: Misspelled brand names (paypa1.com, amaz0n.com, g00gle.com)
2. SUSPICIOUS TLDs: Unusual domains (.xyz, .top, .click, .info, .work)
3. DECEPTIVE SUBDOMAINS: Legitimate-looking subdomains on malicious domains (login-paypal.evil.com)
4. URL SHORTENERS: Links hiding destinations (bit.ly, tinyurl, t.co)
5. IP-BASED URLS: Direct IP addresses instead of domain names
6. EXCESSIVE SUBDOMAINS: Many subdomain levels (secure.login.verify.account.example.com)
7. SUSPICIOUS PATHS: Paths containing words like "login", "verify", "update", "secure" combined with brand names

Respond ONLY with a valid JSON object in this exact format:
{"verdict": "malicious", "reason": "string explaining why"}
or
{"verdict": "safe", "reason": "string explaining why"}

Be conservative - if in doubt, mark as malicious. User safety is paramount."""


def _get_model():
    """Lazily initialize the Gemini model."""
    global _model
    if _model is None:
        try:
            import google.generativeai as genai
            
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                logger.error("GEMINI_API_KEY not set. AI fallback will be unavailable.")
                return None
            
            genai.configure(api_key=api_key)
            _model = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                system_instruction=SYSTEM_INSTRUCTION,
                generation_config={
                    "temperature": 0.1,  # Low temperature for consistent security decisions
                    "max_output_tokens": 256,
                    "response_mime_type": "application/json",
                }
            )
            logger.info("Gemini model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini model: {e}")
            return None
    return _model


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
    Analyze URLs using Gemini AI for phishing detection.
    
    Args:
        urls: List of URLs to analyze
        
    Returns:
        Tuple of (verdict, reason) where verdict is "malicious" or "safe"
    """
    if not urls:
        return "safe", "No URLs to analyze"
    
    model = _get_model()
    if model is None:
        # Fail conservative if Gemini unavailable
        logger.warning("Gemini model unavailable, defaulting to cautious verdict")
        return "suspicious", "AI analysis unavailable - manual review recommended"
    
    # Format URLs for analysis
    urls_text = "\n".join([f"- {url}" for url in urls[:10]])  # Limit to 10 URLs
    prompt = f"Analyze these URLs for phishing or malicious content:\n\n{urls_text}"
    
    try:
        logger.info(
            f"Sending {len(urls)} URLs to Gemini for analysis",
            extra={"urls_sanitized": [sanitize_url_for_logs(u) for u in urls[:5]]}
        )
        
        response = await model.generate_content_async(prompt)
        
        # Parse JSON response
        response_text = response.text.strip()
        logger.debug(f"Gemini raw response: {response_text}")
        
        try:
            result = json.loads(response_text)
            verdict = result.get("verdict", "safe").lower()
            reason = result.get("reason", "No reason provided")
            
            # Validate verdict
            if verdict not in ("malicious", "safe"):
                logger.warning(f"Unexpected verdict '{verdict}', treating as suspicious")
                verdict = "suspicious"
                reason = f"Unclear AI response: {reason}"
            
            logger.info(
                f"Gemini analysis complete",
                extra={"verdict": verdict, "reason": reason[:100]}
            )
            return verdict, reason
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            # Try to extract verdict from text response
            if "malicious" in response_text.lower():
                return "malicious", f"AI flagged as malicious (parse error): {response_text[:100]}"
            return "suspicious", f"Could not parse AI response: {response_text[:100]}"
            
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}", exc_info=True)
        # Fail conservative
        return "suspicious", f"AI analysis failed: {str(e)[:100]}"


async def is_gemini_available() -> bool:
    """
    Check if Gemini API is available and configured.
    
    Returns:
        True if Gemini is ready to use
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return False
    
    model = _get_model()
    return model is not None
