# Doc2Talk Web Interface

This directory contains the React-based web interface for Doc2Talk.

## Development Setup

For development with hot-reloading:

1. Start the backend API server in development mode:
   ```
   doc2talk web --dev
   ```

2. In a separate terminal, start the React development server:
   ```
   cd web
   npm start
   ```
   or
   ```
   python build_web.py --dev
   ```

The frontend will be available at http://localhost:3000 and will automatically proxy API requests to the backend server running on port 8000.

## Building for Production

To build and package the web interface for distribution:

```
python build_web.py
```

This will:
1. Install dependencies
2. Build the React application
3. Copy the built files to the appropriate location in the package

After building, you can run the production server with:

```
doc2talk web
```

## Structure

- `src/` - React source code
  - `components/` - React components
  - `App.tsx` - Main application component
- `public/` - Static assets
- `package.json` - Dependency and script configuration