"""PyInstaller entry script — uses absolute imports so the package's
relative imports resolve correctly inside the frozen bundle."""

from orf_transcriber.app import main

if __name__ == "__main__":
    main()
