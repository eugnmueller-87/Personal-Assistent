import pytest
from unittest.mock import patch, MagicMock
from auto_debug import _extract_file_path, _create_pr


# --- _extract_file_path ---

def test_extract_standard_file():
    tb = 'File "/app/bot/claude_router.py", line 42, in route'
    assert _extract_file_path(tb) == "bot/claude_router.py"


def test_extract_skills_file():
    tb = 'File "/app/bot/skills/email.py", line 10, in handler'
    assert _extract_file_path(tb) == "bot/skills/email.py"


def test_extract_nested_skills_file():
    tb = 'File "/app/bot/skills/calendar.py", line 5, in get_events'
    assert _extract_file_path(tb) == "bot/skills/calendar.py"


def test_extract_returns_last_file_in_traceback():
    tb = (
        'File "/app/bot/main.py", line 100\n'
        'File "/app/bot/claude_router.py", line 42, in route'
    )
    assert _extract_file_path(tb) == "bot/claude_router.py"


def test_extract_returns_none_when_no_match():
    assert _extract_file_path("SomeError: something went wrong") is None


def test_extract_returns_none_for_empty():
    assert _extract_file_path("") is None


# --- _create_pr ---

@patch("auto_debug.requests.get")
@patch("auto_debug.requests.post")
@patch("auto_debug.requests.put")
def test_create_pr_returns_url(mock_put, mock_post, mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: {"object": {"sha": "abc123"}},
    )
    mock_post.side_effect = [
        MagicMock(status_code=201, json=lambda: {}),
        MagicMock(status_code=201, json=lambda: {"html_url": "https://github.com/user/repo/pull/1"}),
    ]
    mock_put.return_value = MagicMock(status_code=200, json=lambda: {})

    with patch.dict("os.environ", {"RAILWAY_REPO": "user/repo", "GITHUB_TOKEN": "tok"}):
        url = _create_pr("bot/main.py", "print('fixed')", "sha123", "TestError: oops")

    assert url == "https://github.com/user/repo/pull/1"


@patch("auto_debug.requests.get")
def test_create_pr_returns_none_when_no_repo(mock_get):
    with patch.dict("os.environ", {}, clear=True):
        result = _create_pr("bot/main.py", "code", "sha", "error")
    assert result is None
    mock_get.assert_not_called()


@patch("auto_debug.requests.get")
def test_create_pr_returns_none_when_main_branch_fetch_fails(mock_get):
    mock_get.return_value = MagicMock(status_code=404)
    with patch.dict("os.environ", {"RAILWAY_REPO": "user/repo", "GITHUB_TOKEN": "tok"}):
        result = _create_pr("bot/main.py", "code", "sha", "error")
    assert result is None
