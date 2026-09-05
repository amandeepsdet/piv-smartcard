# piv-smartcard

[![CI](https://github.com/amandeepsdet/piv-smartcard/actions/workflows/ci.yml/badge.svg)](https://github.com/amandeepsdet/piv-smartcard/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/piv-smartcard.svg)](https://pypi.org/project/piv-smartcard/)
[![Python versions](https://img.shields.io/pypi/pyversions/piv-smartcard.svg)](https://pypi.org/project/piv-smartcard/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

A cross-platform Python library to read X.509 certificates from
[PIV](https://en.wikipedia.org/wiki/FIPS_201) smart cards over **PC/SC**
(Windows, macOS and Linux).

It is a Python port of [GoogleChromeLabs/web-smartcard-demo](https://github.com/GoogleChromeLabs/web-smartcard-demo).
The original is a ChromeOS-only Isolated Web Apps that uses the experimental
**Web Smart Card API** to read X.509 *Card Authentication* certificate from a
PIV smart card. That API does not exist on Windows or macOS, so this project keeps
the same architecture but talk to the **native PC/SC stack** through
[`pyscard`](https://pyscard.sourceforge.io/), which works on **Windows, macOS and Linux**.

## Features

- 🔌 **Cross-platform** — one code path for Windows (WinSCard), macOS (PCSC framework) and Linux (pcscd).
- 🪪 **Reads all four PIV certificate slots** — Authentication (9A), Digital Signature (9C), Key Management (9D) and Card Authentication (9E).
- 🧩 **Clean, layered API** — separate, independently usable modules for APDU framing, BER-TLV decoding, PIV operations and X.509 parsing.
- 🗜️ **Handles real-world cards** — GET RESPONSE chaining for large certificates and transparent gzip decompression (per NIST SP 800-73-4).
- 🖥️ **GUI + CLI + library** — use it however you like: a Tkinter app, a command-line tool, or `import smartcard_demo`.
- 🧪 **Hardware-free tests** — the core logic is verified with canned APDU responses, so CI runs without a reader.
- 🏷️ **Typed** — ships a `py.typed` marker so downstream users get full type information.

## Platform support

| OS      | PC/SC backend                     | Extra setup                                                  |
| ------- | --------------------------------- | ----------------------------------------------------------- |
| Windows | *Smart Card* service (WinSCard)   | None — built in.                                            |
| macOS   | PCSC (CryptoTokenKit) framework   | None — built in.                                            |
| Linux   | `pcscd` + `libpcsclite`           | `sudo apt install pcscd libpcsclite-dev` (or distro equiv). |

> Tested with YubiKey (PIV interface). Any CCID reader + PIV-compliant card should work.

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

## How it works

Reading a certificate is a short conversation of ISO 7816-4 **APDUs** with the card:

1. **SELECT the PIV application** — send `00 A4 04 00` with the PIV application
   identifier (AID `A0 00 00 03 08 00 00 10 00 01 00`). The card returns its
   application property template.
2. **GET DATA for the certificate object** — send `00 CB 3F FF` with the BER
   tag list (`5C 03 5F C1 xx`) identifying the slot's data object.
3. **Follow the chain** — certificates are larger than a single 256-byte
   response, so the card replies with status `61 xx` ("more data available").
   The library issues `00 C0 00 00` (GET RESPONSE) repeatedly until the card
   returns `90 00`, concatenating the fragments.
4. **Unwrap the TLV** — the reassembled bytes are a BER-TLV structure
   (`53 { 70 <cert> 71 <certinfo> ... }`). The `ber` module walks it to pull
   out tag `70` (the certificate) and tag `71` (CertInfo).
5. **Decompress if needed** — if CertInfo bit 0 is set, the certificate is
   gzip-compressed; the library inflates it transparently.
6. **Parse the X.509** — the DER bytes are handed to `cryptography` and returned
   as a `CertificateInfo` (subject, issuer, validity, SHA-256 fingerprint, PEM).

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

## API reference

Everything below is importable from the top-level `smartcard_demo` package.

### Reader (requires `pyscard`)

| Symbol | Description |
| ------ | ----------- |
| `list_readers() -> list[str]` | Names of all connected PC/SC readers. |
| `CardSession(reader_name)` | Connection to a card. Use as a context manager or call `connect()` / `disconnect()`. |
| `CardSession.transmit(cmd) -> ResponseAPDU` | Send a `CommandAPDU`, get the parsed response. |
| `CardSession.get_atr() -> list[int]` | The card's Answer-To-Reset bytes. |
| `ReaderError` | Raised for reader discovery / connection failures. |

### PIV operations

| Symbol | Description |
| ------ | ----------- |
| `select(session)` | SELECT the PIV application (call before reading). |
| `read_certificate(session, slot="card_authentication") -> CertificateInfo` | Read + parse a slot's certificate. |
| `read_certificate_der(session, slot=...) -> list[int]` | Raw DER bytes of the certificate. |
| `SLOTS` | Mapping of slot keys to `CertificateSlot(name, key_reference, object_id)`. |
| `PivError` | Raised for PIV-level failures (bad slot, missing certificate). |

### APDU / BER / X.509 helpers

| Symbol | Description |
| ------ | ----------- |
| `CommandAPDU(cla, ins, p1, p2, data=[], le=None)` | Build a command; `.serialize()` → byte list. |
| `ResponseAPDU(data, sw1, sw2)` | Parsed response; `.sw`, `.is_success`, `.raise_for_status()`. |
| `ApduError` | Raised when a card returns a non-`9000` status word. |
| `parse(bytes)` / `find(bytes, tag)` | BER-TLV decode / tag search. |
| `parse_certificate(der) -> CertificateInfo` | Parse DER into subject/issuer/validity/fingerprint/PEM. |
| `identify_card(atr) -> str` | Best-effort friendly card name from its ATR. |
| `to_hex(bytes)` / `from_hex(str)` | Hex conversion helpers. |

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

### CLI reference

| Command | Options | Description |
| ------- | ------- | ----------- |
| `piv-smartcard list` | — | List connected PC/SC readers. |
| `piv-smartcard read` | `--reader <name>` | Reader name or substring (default: first reader). |
|                      | `--slot <key>`    | One of `authentication`, `signature`, `key_management`, `card_authentication` (default). |
|                      | `--pem`           | Also print the certificate in PEM form. |

## Error handling

The library raises typed exceptions so callers can react precisely:

```python
from smartcard_demo import CardSession, ReaderError, PivError, ApduError, select, read_certificate

try:
    with CardSession("My Reader") as session:
        select(session)
        info = read_certificate(session, "card_authentication")
except ReaderError:
    ...   # no reader / no card / connection dropped
except PivError:
    ...   # unknown slot, or the slot has no certificate
except ApduError as exc:
    ...   # card returned a non-success status word
    print(f"card said 0x{exc.sw:04X}")
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

## Security considerations

- This library **reads public data** (X.509 certificates) from the card. It does
  **not** perform PIN verification, private-key operations, or signing.
- No secrets are logged. ATRs and certificates are public information.
- Only send APDUs to cards you trust; a malicious card can return crafted TLV
  data. The BER decoder is defensive (it treats unparseable values as opaque)
  but callers should still validate certificates against a trust anchor before
  relying on them for authentication.

## Contributing

Contributions are welcome!

1. Fork and clone the repo, then `pip install -e ".[dev]"`.
2. Make your change and add tests under `tests/`.
3. Run `pytest` — it must pass without a card reader.
4. Open a pull request. CI runs the suite on Windows, macOS and Linux across
   Python 3.10–3.13.

## Roadmap

- [ ] PIN verification and private-key auth (sign/decrypt) operations.
- [ ] Read the CHUID / card capability container for richer card identification.
- [ ] Optional export of certificates to `.pem` / `.der` files from the CLI.
- [ ] Publish prebuilt binaries for the GUI.

## Acknowledgements

- [GoogleChromeLabs/web-smartcard-demo](https://github.com/GoogleChromeLabs/web-smartcard-demo) — the TypeScript project this port is modelled on.
- [pyscard](https://pyscard.sourceforge.io/) — Python PC/SC bindings.
- [pyca/cryptography](https://cryptography.io/) — X.509 parsing.
- [NIST SP 800-73-4](https://csrc.nist.gov/pubs/sp/800/73/4/upd1/final) — the PIV card interface specification.

## License

Licensed under the [Apache License 2.0](LICENSE).

