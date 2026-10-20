#!/usr/bin/env python3
"""Remove the weather bar entry while preserving the installed shell layout."""
import argparse
import copy
import json
import os
from pathlib import Path
import tempfile


def without_weather(config):
    result = copy.deepcopy(config)
    if not isinstance(result, dict) or result.get("version") != 1:
        raise ValueError("expected shell configuration version 1")
    bar = result.get("bar")
    layout = bar.get("layout") if isinstance(bar, dict) else None
    if not isinstance(layout, dict) or not layout:
        raise ValueError("expected a nonempty bar layout")
    for name, entries in layout.items():
        if not isinstance(entries, list) or any(
            not isinstance(e, dict) or not isinstance(e.get("id"), str)
            for e in entries
        ):
            raise ValueError("invalid widget list: " + name)
        layout[name] = [e for e in entries if e["id"] != "omarchy.weather"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = without_weather(json.loads(args.source.read_text()))
    # Source and destination may be the same. A failed write keeps the original.
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=args.output.parent,
                                         delete=False) as stream:
            tmp = Path(stream.name)
            json.dump(result, stream, indent=2)
            stream.write("\n")
        os.replace(tmp, args.output)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    print("PASS: weather entries removed; all other configuration preserved")


if __name__ == "__main__":
    main()
