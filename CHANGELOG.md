# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-08-27

### Added
- Initial release.
- `apdu` module: `CommandAPDU` / `ResponseAPDU` serialization (ISO 7816-4).
- `ber` module: minimal BER-TLV decoder with PIV template-tag handling.
- `piv` module: SELECT PIV application and read X.509 certificates from the
  four PIV slots (authentication, signature, key management, card
  authentication), with GET RESPONSE chaining and gzip-compressed cert support.
- `util` module: hex helpers, X.509 parsing, and ATR-based card identification.
- `reader` module: PC/SC `CardSession` (connect / transmit / disconnect) backed
  by `pyscard`, working on Windows, macOS and Linux.
- Tkinter GUI (`piv-smartcard-gui`) and CLI (`piv-smartcard`).
- Unit tests that run without a card reader.

[Unreleased]: https://github.com/amandeepsdet/piv-smartcard/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/amandeepsdet/piv-smartcard/releases/tag/v0.1.0
