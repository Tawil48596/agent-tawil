"""Create, verify, or restore a local runtime-data backup."""

from __future__ import annotations

import argparse
import json

from shared.data_backup import create_backup, restore_backup, verify_backup


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--create", metavar="ARCHIVE")
    actions.add_argument("--verify", metavar="ARCHIVE")
    actions.add_argument("--restore", metavar="ARCHIVE")
    parser.add_argument("--data-root", default="data")
    args = parser.parse_args()

    if args.create:
        manifest = create_backup(args.data_root, args.create)
    elif args.verify:
        manifest = verify_backup(args.verify)
    else:
        manifest = restore_backup(args.restore, args.data_root)
    print(json.dumps({"ok": True, "files": len(manifest["files"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
