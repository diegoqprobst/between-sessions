import pytest
from server import llm, config

@pytest.fixture
def openrouter(monkeypatch):
    monkeypatch.setattr(config, "USE_OPENROUTER", True)

@pytest.fixture
def openai_direct(monkeypatch):
    monkeypatch.setattr(config, "USE_OPENROUTER", False)

def test_openrouter_adds_provider_prefix(openrouter):
    assert llm.model_id("gpt-5-mini") == "openai/gpt-5-mini"
    assert llm.model_id("openai/gpt-5.4-mini") == "openai/gpt-5.4-mini"
    assert llm.model_id("meta-llama/llama-guard-4-12b") == "meta-llama/llama-guard-4-12b"

def test_openai_direct_strips_prefix(openai_direct):
    assert llm.model_id("openai/gpt-5.4-mini") == "gpt-5.4-mini"
    assert llm.model_id("gpt-5-mini") == "gpt-5-mini"
