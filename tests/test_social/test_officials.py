from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.social.officials import (
    build_officials_summary,
    fetch_fed_speeches,
    fetch_sec_press_releases,
)

_FED_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Fed Speeches</title>
    <item>
      <title>Chair Powell: Inflation remains above target</title>
      <link>https://fed.gov/1</link>
      <pubDate>Mon, 10 Feb 2026</pubDate>
      <description>Price stability is our mandate. Tighten.</description>
    </item>
    <item>
      <title>Governor Waller: Rate cut path is clear</title>
      <link>https://fed.gov/2</link>
      <pubDate>Sun, 09 Feb 2026</pubDate>
      <description>Easing conditions warrant accommodation.</description>
    </item>
  </channel>
</rss>
"""

_SEC_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>SEC Press</title>
    <item>
      <title>SEC charges company with fraud</title>
      <link>https://sec.gov/1</link>
      <pubDate>Mon, 10 Feb 2026</pubDate>
    </item>
  </channel>
</rss>
"""


@patch("app.social.officials.httpx.Client")
def test_fetch_fed_speeches(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = _FED_RSS
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    speeches = fetch_fed_speeches()
    assert len(speeches) == 2
    assert speeches[0].speaker == "Federal Reserve"
    assert speeches[0].sentiment == "HAWKISH"
    assert speeches[1].sentiment == "DOVISH"


@patch("app.social.officials.httpx.Client")
def test_fetch_sec_press(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = _SEC_RSS
    mock_ctx = MagicMock()
    mock_ctx.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__.return_value = mock_ctx

    releases = fetch_sec_press_releases()
    assert len(releases) == 1
    assert releases[0].speaker == "SEC"


def test_build_officials_summary_hawkish():
    from app.social.officials import OfficialStatement

    stmts = [
        OfficialStatement(
            "Federal Reserve",
            "",
            "Inflation above target",
            "",
            "HAWKISH",
        ),
        OfficialStatement(
            "Federal Reserve",
            "",
            "Tighten policy",
            "",
            "HAWKISH",
        ),
        OfficialStatement(
            "Federal Reserve",
            "",
            "Patience needed",
            "",
            "DOVISH",
        ),
    ]
    summary = build_officials_summary(stmts)
    assert summary.fed_tone == "HAWKISH"
    assert summary.policy_direction == "CONTRACTIONARY"


def test_build_officials_summary_dovish():
    from app.social.officials import OfficialStatement

    stmts = [
        OfficialStatement("Federal Reserve", "", "Rate cut", "", "DOVISH"),
        OfficialStatement("Federal Reserve", "", "Easing", "", "DOVISH"),
    ]
    summary = build_officials_summary(stmts)
    assert summary.fed_tone == "DOVISH"
    assert summary.policy_direction == "EXPANSIONARY"


def test_build_officials_summary_empty():
    summary = build_officials_summary([])
    assert summary.fed_tone == "NEUTRAL"
    assert summary.total_statements == 0
