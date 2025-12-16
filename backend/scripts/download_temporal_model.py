"""Download a temporal model file for the TemporalAnalyzer.

Usage:
  python -m backend.scripts.download_temporal_model --url <MODEL_URL> --out <path>
Or set env var TEMPORAL_MODEL_URL and run without args.

This script prefers `requests` if available, otherwise falls back to urllib.
"""
from __future__ import annotations
import argparse
import os
import sys
import logging

logger = logging.getLogger("backend.scripts.download_temporal_model")
logging.basicConfig(level=logging.INFO)


def download(url: str, out_path: str) -> bool:
    try:
        import requests
    except Exception:
        requests = None

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    if requests:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(out_path, "wb") as fh:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
        return True
    else:
        from urllib.request import urlopen

        with urlopen(url, timeout=60) as r:
            with open(out_path, "wb") as fh:
                fh.write(r.read())
        return True


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", help="Model URL (overrides $TEMPORAL_MODEL_URL)")
    p.add_argument("--out", default="static/models/temporal_accident.pth", help="Output path")
    args = p.parse_args(argv)

    url = args.url or os.getenv("TEMPORAL_MODEL_URL")
    if not url:
        logger.error("No model URL provided via --url or TEMPORAL_MODEL_URL")
        return 2

    try:
        logger.info(f"Downloading temporal model from {url} to {args.out}")
        success = download(url, args.out)
        if success:
            logger.info("Download complete")
            return 0
    except Exception as e:
        logger.exception("Download failed: %s", e)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
