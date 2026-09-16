"""Entry point: `python -m alexandria.main`."""

from __future__ import annotations

from alexandria.config import Config
from alexandria.core.orchestrator import Orchestrator


def main() -> None:
    config = Config.from_env()
    orchestrator = Orchestrator(config)
    orchestrator.run_forever()


if __name__ == "__main__":
    main()
