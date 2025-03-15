#!/usr/bin/env python
"""
Main entry point for the doc2talk CLI or web interface
"""

import asyncio
import sys

def main_entry_point():
    """Entry point for console_scripts"""
    # Check if web mode is requested
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        # Remove the 'web' argument so it doesn't confuse the server
        sys.argv.pop(1)
        
        # Import and run web server
        from .web.server import run_server
        
        # Get host and port from command line if provided
        host = "127.0.0.1"
        port = 8000
        dev_mode = False
        
        # Parse additional arguments
        i = 1
        while i < len(sys.argv):
            if sys.argv[i] == "--host" and i + 1 < len(sys.argv):
                host = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--port" and i + 1 < len(sys.argv):
                try:
                    port = int(sys.argv[i + 1])
                except ValueError:
                    print(f"Invalid port: {sys.argv[i + 1]}")
                    sys.exit(1)
                i += 2
            elif sys.argv[i] == "--dev":
                dev_mode = True
                i += 1
            else:
                i += 1
        
        if dev_mode:
            # Start development mode - backend API server only
            print(f"Starting Doc2Talk API server in development mode at http://{host}:{port}")
            print("Frontend should be started separately with 'cd web && npm start'")
            print("Frontend will be available at http://localhost:3000")
            run_server(host=host, port=port, dev_mode=True)
        else:
            # Run the web server in production mode
            print(f"Starting Doc2Talk web server at http://{host}:{port}")
            run_server(host=host, port=port)
    else:
        # Run CLI mode
        from .cli import main
        asyncio.run(main())

if __name__ == "__main__":
    main_entry_point()