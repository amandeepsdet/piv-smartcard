"""Command-line interface for the PIV smart card demo.

Usage examples:

    python -m smartcard_demo.cli list
    python -m smartcard_demo.cli read
    python -m smartcard_demo.cli read --slot authentication --pem
    python -m smartcard_demo.cli read --reader "Yubico YubiKey ..." 
"""

from __future__ import annotations

import argparse
import sys

from . import piv
from .reader import CardSession, ReaderError, list_readers
from .util import identify_card


def cmd_list(_: argparse.Namespace) -> int:
    try:
        names = list_readers()
    except ReaderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not names:
        print("No PC/SC readers found.")
        return 0
    for i, name in enumerate(names):
        print(f"[{i}] {name}")
    return 0


def _resolve_reader(name: str | None) -> str:
    names = list_readers()
    if not names:
        raise ReaderError("No PC/SC readers found.")
    if name is None:
        return names[0]
    for candidate in names:
        if candidate == name or name.lower() in candidate.lower():
            return candidate
    raise ReaderError(f"Reader not found: {name}")


def cmd_read(args: argparse.Namespace) -> int:
    try:
        reader_name = _resolve_reader(args.reader)
        with CardSession(reader_name) as session:
            print(f"Reader: {reader_name}")
            print(f"Card:   {identify_card(session.get_atr())}")
            piv.select(session)
            info = piv.read_certificate(session, args.slot)
    except (ReaderError, piv.PivError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # APDU / crypto errors
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print()
    print(info.as_lines())
    if args.pem:
        print()
        print(info.pem)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="smartcard_demo", description="Read PIV certificates over PC/SC (Windows/macOS/Linux)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="List connected PC/SC readers.")
    p_list.set_defaults(func=cmd_list)

    p_read = sub.add_parser("read", help="Read a certificate from a PIV card.")
    p_read.add_argument("--reader", help="Reader name or substring (default: first reader).")
    p_read.add_argument(
        "--slot",
        choices=list(piv.SLOTS.keys()),
        default="card_authentication",
        help="PIV certificate slot (default: card_authentication).",
    )
    p_read.add_argument("--pem", action="store_true", help="Also print the certificate in PEM form.")
    p_read.set_defaults(func=cmd_read)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
