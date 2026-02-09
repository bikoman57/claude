from __future__ import annotations

from app.__main__ import main


def test_main_runs(capsys: object) -> None:
    main()
    # Smoke test: main() should not raise
