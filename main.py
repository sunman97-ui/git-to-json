#!/usr/bin/env python3
from src.cli import run_app

if __name__ == "__main__":
    try:
        run_app()
    except KeyboardInterrupt:
        print("\nGoodbye!")