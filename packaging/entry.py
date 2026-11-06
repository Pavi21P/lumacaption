"""Entry shared by console and windowed executables."""

import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from lumacaption.packaged import main

    raise SystemExit(main())
