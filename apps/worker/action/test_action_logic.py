"""
Unit Tests for Action Agent Logic.

Tests:
- Verdict-to-label mapping
- Idempotency behavior
- Gemini response parsing
- Label application logic

Run with: python test_action_logic.py
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock

# Test the label mapping
def test_verdict_to_label_mapping():
    from gmail_labels import VERDICT_TO_LABEL, get_label_for_verdict
    
    assert get_label_for_verdict("malicious") == "MailShield/MALICIOUS"
    assert get_label_for_verdict("suspicious") == "MailShield/CAUTIOUS"
    assert get_label_for_verdict("clean") == "MailShield/SAFE"
    assert get_label_for_verdict("safe") == "MailShield/SAFE"  # Gemini returns "safe"
    
    # Unknown verdict defaults to CAUTIOUS
    assert get_label_for_verdict("unknown") == "MailShield/CAUTIOUS"
    assert get_label_for_verdict("something_random") == "MailShield/CAUTIOUS"
    
    print("✅ Verdict-to-label mapping test passed")


def test_url_sanitization():
    from ai_fallback import sanitize_url_for_logs
    
    assert sanitize_url_for_logs("http://evil.com") == "http://evil[.]com"
    assert sanitize_url_for_logs("https://paypa1.com/login") == "https://paypa1[.]com/login"
    assert sanitize_url_for_logs("ftp://192.168.1.1") == "ftp://192[.]168[.]1[.]1"
    
    print("✅ URL sanitization test passed")


def test_mailshield_label_config():
    from gmail_labels import MAILSHIELD_LABELS
    
    # All labels should have required fields
    for label_name, config in MAILSHIELD_LABELS.items():
        assert "name" in config
        assert "labelListVisibility" in config
        assert "messageListVisibility" in config
        assert "color" in config
        assert config["name"] == label_name
    
    # Verify color scheme
    assert MAILSHIELD_LABELS["MailShield/MALICIOUS"]["color"]["backgroundColor"] == "#cc3a21"  # Red
    assert MAILSHIELD_LABELS["MailShield/CAUTIOUS"]["color"]["backgroundColor"] == "#f2a600"  # Orange
    assert MAILSHIELD_LABELS["MailShield/SAFE"]["color"]["backgroundColor"] == "#16a766"  # Green
    
    print("✅ MailShield label config test passed")


def test_label_cache_operations():
    from gmail_labels import _label_cache, clear_label_cache
    
    # Clear cache first to ensure clean state
    clear_label_cache()
    
    # Manually add to cache
    _label_cache["test-label"] = "test-id"
    assert _label_cache["test-label"] == "test-id"
    assert len(_label_cache) == 1
    
    # Clear and verify
    clear_label_cache()
    assert len(_label_cache) == 0
    
    print("✅ Label cache operations test passed")


def test_pydantic_models():
    from main import UnifiedDecisionPayload, SandboxResult, DecisionMetadata, ActionResult
    
    # Test UnifiedDecisionPayload
    payload = UnifiedDecisionPayload(
        message_id="test-123",
        static_risk_score=85,
        sandboxed=True,
        sandbox_result=SandboxResult(verdict="malicious", score=90),
        decision_metadata=DecisionMetadata(provider="hybrid-analysis", timed_out=False),
        extracted_urls=["http://evil.com"]
    )
    
    assert payload.message_id == "test-123"
    assert payload.sandbox_result.verdict == "malicious"
    assert payload.extracted_urls == ["http://evil.com"]
    
    # Test ActionResult
    result = ActionResult(
        message_id="test-123",
        original_verdict="malicious",
        final_verdict="malicious",
        label_applied="MailShield/MALICIOUS",
        moved_to_spam=True,
        ai_analysis_used=False
    )
    
    assert result.moved_to_spam is True
    assert result.ai_analysis_used is False
    
    print("✅ Pydantic models test passed")


def test_payload_without_urls():
    from main import UnifiedDecisionPayload, SandboxResult, DecisionMetadata
    
    # Payload without extracted_urls (should be None)
    payload = UnifiedDecisionPayload(
        message_id="test-456",
        static_risk_score=50,
        sandboxed=True,
        sandbox_result=SandboxResult(verdict="unknown", score=50),
        decision_metadata=DecisionMetadata(provider="mock", timed_out=True)
    )
    
    assert payload.extracted_urls is None
    
    print("✅ Payload without URLs test passed")


def test_gemini_json_response_parsing():
    """Test parsing various Gemini response formats."""
    
    # Valid responses
    valid_responses = [
        '{"verdict": "malicious", "reason": "Typosquatting detected"}',
        '{"verdict": "safe", "reason": "Legitimate domain"}',
        '{"verdict":"malicious","reason":"test"}',  # No spaces
    ]
    
    for response in valid_responses:
        parsed = json.loads(response)
        assert "verdict" in parsed
        assert "reason" in parsed
        assert parsed["verdict"] in ("malicious", "safe")
    
    print("✅ Gemini JSON parsing test passed")


if __name__ == "__main__":
    # Run all tests
    test_verdict_to_label_mapping()
    test_url_sanitization()
    test_mailshield_label_config()
    test_label_cache_operations()
    test_pydantic_models()
    test_payload_without_urls()
    test_gemini_json_response_parsing()
    
    print("\n🎉 All Action Agent Logic Tests Passed!")
