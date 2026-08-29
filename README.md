# piv-smartcard

[![CI](https://github.com/amandeepsdet/piv-smartcard/actions/workflows/ci.yml/badge.svg)](https://github.com/amandeepsdet/piv-smartcard/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/piv-smartcard.svg)](https://pypi.org/project/piv-smartcard/)
[![Python versions](https://img.shields.io/pypi/pyversions/piv-smartcard.svg)](https://pypi.org/project/piv-smartcard/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A cross-platform Python library to read X.509 certificates from
[PIV](https://en.wikipedia.org/wiki/FIPS_201) smart cards over **PC/SC**
(Windows, macOS and Linux).

It is a Python port of [GoogleChromeLabs/web-smartcard-demo](https://github.com/GoogleChromeLabs/web-smartcard-demo).
The original is a ChromeOS-only Isolated Web App that uses the experimental
**Web Smart Card API** to read the X.509 *Card Authentication* certificate from a
PIV smart card. That API does not exist on Windows or macOS, so this project keeps
the same architecture but talk to the **native PC/SC stack** through
[`pyscard`](https://pyscard.sourceforge.io/), which works on **Windows, macOS and Linux**.

## Architecture

| This project (`src/smartcard_demo/`) | Original (`src/`)   | Responsibility                              |
| ------------------------------------ | ------------------- | ------------------------------------------- |
| `apdu.py`                            | `apdu.ts`           | APDU command/response serialization         |
| `ber.py`                             | `ber.ts`            | BER-TLV decoding                            |
| `piv.py`                             | `piv.ts`            | PIV applet: SELECT + read certificate       |
| `util.py`                            | `util.ts`           | hex helpers, X.509 parsing, card ID         |
| `reader.py`                          | Web Smart Card API  | PC/SC reader connect / transmit / disconnect |
| `app.py`                             | `index.ts` + `.html`| Tkinter UI (Connect / Disconnect / Read)    |
| `cli.py`                             | —                   | Command-line interface                      |
| `tests/`                             | `tests/`, `*.test.ts`| Unit tests (no hardware needed)            |

```
Reader (PC/SC)
   │  pyscard  (WinSCard on Windows, PCSC framework on macOS)
   ▼
CardSession ── transmit(CommandAPDU) ──► ResponseAPDU
   │
   ▼
piv.select() ─► piv.read_certificate() ─► BER-TLV decode ─► X.509 parse
   │
   ▼
Tkinter GUI  /  CLI
```

## Prerequisites

- Python 3.10+
- A smart-card reader and a **PIV** card (e.g. a YubiKey with the PIV interface).
- **Windows:** the *Smart Card* service is built in — nothing to install.
- **macOS:** the PCSC framework is built in — nothing to install.
- **Linux:** install `pcscd` and `libpcsclite` (`sudo apt install pcscd libpcsclite-dev`).

## Install

From PyPI (once published):

```powershell
pip install piv-smartcard
```

From source (development):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1      # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
```

## Use as a library

```python
from smartcard_demo import CardSession, list_readers, select, read_certificate

reader = list_readers()[0]
with CardSession(reader) as session:
    select(session)                              # SELECT the PIV application
    info = read_certificate(session, "card_authentication")
    print(info.as_lines())
    print(info.pem)
```

The pure-Python parts (`CommandAPDU`, BER-TLV `parse`/`find`,
`parse_certificate`, `identify_card`, `SLOTS`, ...) are importable without
`pyscard`; the `CardSession` / `list_readers` reader symbols are loaded lazily
and only require `pyscard` when actually used.

## Run the apps

GUI:

```powershell
piv-smartcard-gui        # after install
python main.py           # from a source checkout
```

CLI:

```powershell
piv-smartcard list
piv-smartcard read
piv-smartcard read --slot authentication --pem

# or, from a source checkout without installing:
python -m smartcard_demo.cli list
```

## PIV certificate slots

| Slot key             | Key ref | Object id     | Purpose                |
| -------------------- | ------- | ------------- | ---------------------- |
| `authentication`     | `9A`    | `5F C1 05`    | PIV Authentication     |
| `signature`          | `9C`    | `5F C1 0A`    | Digital Signature      |
| `key_management`     | `9D`    | `5F C1 0B`    | Key Management         |
| `card_authentication`| `9E`    | `5F C1 01`    | Card Authentication (default) |

## Tests

```powershell
pip install pytest cryptography
pytest
```

The tests use canned APDU responses and a synthetic certificate, so they run
without a reader or card.

## Publishing

Build and check the distribution locally:

```powershell
python -m pip install build twine
python -m build
python -m twine check dist/*
```

Releasing to PyPI is automated: create a Git tag `vX.Y.Z` (or publish a GitHub
Release) and the `Publish to PyPI` workflow builds and uploads via PyPI
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, no token
stored). Configure the trusted publisher once on PyPI, pointing at
`amandeepsdet/piv-smartcard` and the `publish.yml` workflow.

```powershell
git tag v0.1.0
git push origin v0.1.0
```

## Troubleshooting

- **`pyscard` fails to build on install** (e.g. *"Microsoft Visual C++ 14.0 or greater is required"*):
  `pyscard` ships prebuilt wheels only for released Python versions. On very new
  interpreters (e.g. Python 3.14) pip falls back to compiling from source. Either
  use Python 3.10–3.13 (recommended), or install the
  [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
  The `apdu`, `ber`, `util` and `piv` modules do **not** import `pyscard`, so the
  test suite runs even when `pyscard` is not installed.

