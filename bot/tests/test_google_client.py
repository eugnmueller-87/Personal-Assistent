from unittest.mock import patch, MagicMock
from google_client import create_calendar_event


def _mock_service(summary="Test"):
    service = MagicMock()
    service.events.return_value.insert.return_value.execute.return_value = {
        "summary": summary,
        "id": "abc123",
        "conferenceData": {},
    }
    return service


# --- all-day event date bug ---

@patch("google_client.get_creds")
@patch("google_client.build")
def test_all_day_event_end_is_next_day(mock_build, mock_creds):
    """Google Calendar API requires end.date to be exclusive (day after). start == end = zero-length event."""
    mock_build.return_value = _mock_service()

    create_calendar_event(summary="Holiday", date="2026-05-01")

    body = mock_build.return_value.events.return_value.insert.call_args.kwargs["body"]
    assert body["start"]["date"] == "2026-05-01"
    assert body["end"]["date"] == "2026-05-02"


@patch("google_client.get_creds")
@patch("google_client.build")
def test_all_day_event_end_crosses_month_boundary(mock_build, mock_creds):
    mock_build.return_value = _mock_service()

    create_calendar_event(summary="End of month", date="2026-05-31")

    body = mock_build.return_value.events.return_value.insert.call_args.kwargs["body"]
    assert body["end"]["date"] == "2026-06-01"


# --- timed events ---

@patch("google_client.get_creds")
@patch("google_client.build")
def test_timed_event_defaults_to_one_hour(mock_build, mock_creds):
    mock_build.return_value = _mock_service()

    create_calendar_event(summary="Meeting", date="2026-05-01", start_time="10:00")

    body = mock_build.return_value.events.return_value.insert.call_args.kwargs["body"]
    assert body["start"]["dateTime"] == "2026-05-01T10:00:00"
    assert body["end"]["dateTime"] == "2026-05-01T11:00:00"


@patch("google_client.get_creds")
@patch("google_client.build")
def test_timed_event_uses_explicit_end_time(mock_build, mock_creds):
    mock_build.return_value = _mock_service()

    create_calendar_event(summary="Workshop", date="2026-05-01", start_time="09:00", end_time="12:00")

    body = mock_build.return_value.events.return_value.insert.call_args.kwargs["body"]
    assert body["end"]["dateTime"] == "2026-05-01T12:00:00"
