#!/usr/bin/env python3
"""Standalone CLI entry-point for the RJoy web UI server."""
import sys
import time
from rjoy_bridge import RJoyServer


def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765

    server = RJoyServer()
    server.start(host, port)
    print(f"RJoy web UI running at http://{host}:{port}  (Ctrl-C to stop)")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
