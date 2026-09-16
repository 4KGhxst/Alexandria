"""CLI to ingest a service manual PDF for a vehicle.

    python -m alexandria.manuals.ingest_cli \\
        path/to/manual.pdf \\
        --year 2015 --make Honda --model Civic \\
        --title "2015 Honda Civic Factory Service Manual"

Run this once per manual you download (e.g. from eManualOnline or
similar). It's additive — ingest as many manuals per vehicle as you like
(factory service manual, Haynes, a wiring-diagram supplement); search
will draw from all of them.
"""

from __future__ import annotations

import argparse
import sys

from alexandria.config import Config
from alexandria.manuals.manual_library import ManualLibrary
from alexandria.manuals.vehicle import Vehicle


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ingest a service manual PDF into Alexandria's manual library.")
    parser.add_argument("pdf_path", help="Path to the manual PDF")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--make", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--trim", default=None, help="Trim/engine variant, if the manual is specific to one")
    parser.add_argument("--title", required=True, help="Human-readable manual title, used in citations")
    parser.add_argument("--db", default=None, help="Override the manuals database path")
    args = parser.parse_args(argv)

    config = Config.from_env()
    db_path = args.db or config.manuals_db_path
    vehicle = Vehicle(year=args.year, make=args.make, model=args.model, trim=args.trim)

    library = ManualLibrary(db_path)
    print(f"Ingesting {args.pdf_path!r} for {vehicle} into {db_path} ...")
    chunk_count = library.add_manual(args.pdf_path, vehicle, args.title)
    library.close()
    print(f"Done — added {chunk_count} searchable chunks under vehicle key '{vehicle.key()}'.")


if __name__ == "__main__":
    main(sys.argv[1:])
