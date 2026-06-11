import sys

if "--version" in sys.argv:
    from lsr import __version__

    print(f"lsr {__version__}")
    sys.exit(0)

from .main import main

if __name__ == "__main__":
    main()
