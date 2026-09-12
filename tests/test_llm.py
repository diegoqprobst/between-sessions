import pytest
from server import llm, config

def use(monkeypatch, p):
    monkeypatch.setattr(config, "FORCE_PROVIDER", p)
    monkeypatch.setattr(config, "OPENAI_MODEL", "")

def test_provider_precedence_openrouter_then_gemini_then_openai(monkeypatch):
    monkeypatch.setattr(config, "FORCE_PROVIDER", "")
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "k")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "g")
    assert llm.provider() == "openrouter"
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    assert llm.provider() == "gemini"
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    assert llm.provider() == "openai"

def test_openrouter_adds_provider_prefix(monkeypatch):
    use(monkeypatch, "openrouter")
    assert llm.model_id("gpt-5-mini") == "openai/gpt-5-mini"
    assert llm.model_id("meta-llama/llama-guard-4-12b") == "meta-llama/llama-guard-4-12b"

def test_gemini_rejects_foreign_ids_and_falls_back(monkeypatch):
    use(monkeypatch, "gemini")
    assert llm.model_id("gemini-3.8-flash") == "gemini-3.8-flash"
    assert llm.model_id("openai/gpt-5.4-mini") == "gemini-3.8-flash"
    assert llm.model_id() == "gemini-3.8-flash"

def test_openai_strips_prefix(monkeypatch):
    use(monkeypatch, "openai")
    assert llm.model_id("openai/gpt-5.4-mini") == "gpt-5.4-mini"
    assert llm.model_id("gemini-3.8-flash") == "gpt-5-mini"

def test_privacy_policy_only_on_openrouter(monkeypatch):
    use(monkeypatch, "openrouter")
    monkeypatch.setattr(config, "OPENROUTER_DATA_COLLECTION", "deny")
    monkeypatch.setattr(config, "OPENROUTER_ZDR", False)
    assert llm.provider_policy() == {"provider": {"data_collection": "deny"}}
    use(monkeypatch, "gemini")
    assert llm.provider_policy() == {}

def test_not_configured_without_any_key(monkeypatch):
    use(monkeypatch, "gemini")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    assert llm.configured() is False
