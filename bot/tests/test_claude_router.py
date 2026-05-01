import os
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-for-ci")

from claude_router import _pick_model, HAIKU, SONNET


# --- Haiku triggers ---

def test_single_word_uses_haiku():
    assert _pick_model("emails") == HAIKU


def test_short_simple_keyword_uses_haiku():
    assert _pick_model("check emails") == HAIKU
    assert _pick_model("my calendar") == HAIKU
    assert _pick_model("open issues") == HAIKU


# --- Sonnet triggers ---

def test_long_message_uses_sonnet():
    msg = "can you please check all my emails and summarize the important ones for me today"
    assert len(msg.split()) > 12
    assert _pick_model(msg) == SONNET


def test_complex_signal_words_use_sonnet():
    assert _pick_model("explain my calendar") == SONNET
    assert _pick_model("why is this meeting recurring") == SONNET
    assert _pick_model("summarize my week") == SONNET
    assert _pick_model("what should I prioritize") == SONNET
    assert _pick_model("help me draft a reply") == SONNET


def test_context_reference_uses_sonnet():
    assert _pick_model("what did she write") == SONNET
    assert _pick_model("show me the latest") == SONNET
    assert _pick_model("what did he say about the contract") == SONNET


# --- boundary: 6-12 words, no signals, no keywords → sonnet (default) ---

def test_medium_message_no_keywords_uses_sonnet():
    assert _pick_model("please check what happened with the invoice") == SONNET
