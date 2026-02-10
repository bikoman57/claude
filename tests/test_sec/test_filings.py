from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.sec.filings import classify_materiality, fetch_recent_filings

MOCK_EDGAR_RESPONSE = {
    "name": "Apple Inc.",
    "filings": {
        "recent": {
            "form": ["10-Q", "8-K", "4"],
            "filingDate": [
                "2025-01-30",
                "2025-01-15",
                "2025-01-10",
            ],
            "primaryDocDescription": [
                "10-Q",
                "Current Report",
                "Statement",
            ],
            "accessionNumber": [
                "0000320193-25-000012",
                "0000320193-25-000008",
                "0000320193-25-000005",
            ],
            "primaryDocument": [
                "aapl-20241228.htm",
                "aapl-20250115.htm",
                "wf-form4.htm",
            ],
        },
    },
}


def test_classify_materiality_10k():
    assert classify_materiality("10-K") == "HIGH"
    assert classify_materiality("10-K/A") == "HIGH"


def test_classify_materiality_10q():
    assert classify_materiality("10-Q") == "MEDIUM"


def test_classify_materiality_8k_default():
    assert classify_materiality("8-K") == "MEDIUM"


def test_classify_materiality_8k_high():
    assert classify_materiality(
        "8-K", "earnings announcement",
    ) == "HIGH"


def test_classify_materiality_other():
    assert classify_materiality("4") == "LOW"


@patch("app.sec.filings.httpx.Client")
def test_fetch_recent_filings(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_EDGAR_RESPONSE
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    filings = fetch_recent_filings(
        cik="0000320193",
        ticker="AAPL",
        email="test@test.com",
        days=730,
    )
    # Form "4" filtered out, 10-Q and 8-K remain
    assert len(filings) == 2
    assert filings[0].form_type == "10-Q"
    assert filings[1].form_type == "8-K"
    assert filings[0].company_name == "Apple Inc."
    assert filings[0].ticker == "AAPL"
