from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.sec.institutional import (
    TRACKED_FILERS,
    fetch_institutional_filings,
)


def test_tracked_filers_count():
    assert len(TRACKED_FILERS) == 5
    names = [f.name for f in TRACKED_FILERS]
    assert "Berkshire Hathaway" in names
    assert "ARK Invest" in names


@patch("app.sec.institutional.time.sleep")
@patch("app.sec.institutional.httpx.Client")
def test_fetch_institutional_filings(mock_client_cls, _mock_sleep):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "filings": {
            "recent": {
                "form": ["13F-HR", "10-K"],
                "filingDate": ["2025-11-15", "2025-01-01"],
                "accessionNumber": [
                    "0001067983-25-000001",
                    "0001067983-25-000002",
                ],
                "primaryDocument": ["filing.htm", "annual.htm"],
            },
        },
    }
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    filings = fetch_institutional_filings(
        "test@test.com",
        days=730,
    )
    # Each of 5 filers returns 1 13F (10-K filtered out)
    assert len(filings) == 5
    assert all(f.form_type == "13F-HR" for f in filings)
