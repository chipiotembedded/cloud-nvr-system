"""Root runner for the package's recorder.

This allows running `python recorder.py` from the project root which
forwards execution to the real implementation at
`video_system/recorder.py`.
"""
from __future__ import annotations

import sys

from video_system.recorder import main


if __name__ == "__main__":
    # Ensure the project root is on sys.path (usually already is when
    # running from the root directory, but make it explicit).
    sys.path.insert(0, "")
    main()
