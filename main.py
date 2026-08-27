"""Launch the Tkinter GUI.

Run from the repo root:  python main.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from smartcard_demo.app import main  # noqa: E402

if __name__ == "__main__":
    main()
