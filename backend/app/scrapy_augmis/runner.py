from __future__ import annotations

import argparse
import json
import sys

from app.services.augmis_business_independent_discovery_service import run_scrapy_independent_scan


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AUGMIS Scrapy independent discovery scan.")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--connector-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stop-file", default=None)
    args = parser.parse_args()
    candidates, metadata = run_scrapy_independent_scan(
        tenant_id=args.tenant_id,
        connector_id=args.connector_id,
        run_id=args.run_id,
        stop_file=args.stop_file,
    )
    print(
        json.dumps(
            {
                "candidates": candidates,
                "metadata": metadata,
            },
            default=str,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
