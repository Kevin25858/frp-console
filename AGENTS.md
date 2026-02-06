> This file provides guidance to CodeBuddy when working with code in this repository.

## Technology Stack

This section provides a comprehensive list of technologies, frameworks, and major libraries used in the project.

### Backend

- **Language**: Python 3
- **Web Framework**: Flask
- **Web Server**: Werkzeug (as Flask's development server), Gunicorn could be used for production but is not explicitly configured.
- **Real-time Communication**: Flask-SocketIO
- **Authentication**: Flask-Login for session management.
- **Database**: SQLite, accessed via Python's built-in `sqlite3` module.
- **Configuration**: Native Python file parsing for `.conf` files.

### Frontend

- **Language**: TypeScript
- **Framework**: React 18
- **Build Tool**: Vite
- **UI Components**: `shadcn/ui` - A collection of customizable components built on top of Radix UI and Tailwind CSS.
- **Styling**: Tailwind CSS
- **Routing**: `react-router-dom`
- **Data Fetching**: Native `fetch` API, wrapped in custom utilities (`src/lib/api.ts`).
- **State Management**: React Context API (`useAuth` for authentication status) and local component state (`useState`, `useEffect`).
- **Form Handling & Validation**: `zod` for schema validation.

### Tooling & Environment

- **Package Management**: `pip` for Python, `npm` for Node.js.
- **Runtime Environment**: Node.js (for frontend build process), Python 3.
- **Process Management (for frpc)**: Standard Linux commands like `subprocess.Popen` in Python, `nohup`, `pgrep`, `kill`.

## Commands

- **Install dependencies**
  ```bash
  pip install -r requirements.txt && npm --prefix frontend install
  ```
  Installs both backend (Python) and frontend (Node.js) dependencies.

- **Run in Development Mode**
  ```bash
  # Terminal 1: Run the Flask backend
  export ADMIN_PASSWORD=your_password
  python /opt/frp-console/app/app.py

  # Terminal 2: Run the Vite frontend dev server
  npm --prefix frontend run dev
  ```
  The frontend is at `http://localhost:5173` (proxies to backend). The backend serves on `http://localhost:7600`.

- **Run in Production Mode**
  ```bash
  # 1. Build the frontend static files
  npm --prefix frontend run build

  # 2. Run the production server
  export ADMIN_PASSWORD=your_password
  python /opt/frp-console/app/app.py
  ```
  The application will be self-contained and served at `http://localhost:7600`.

- **Check for running processes**
  ```bash
  # Find the main Flask server process
  lsof -t -i:7600

  # Kill a process by its PID
  kill -9 <PID>
  ```

## Architecture

This project is a web console for managing `frpc` (Fast Reverse Proxy) clients, architected as a modern Single-Page Application (SPA).

### Backend (`app/app.py`)

- **Framework**: Flask, with Flask-SocketIO for real-time capabilities.
- **Entrypoint**: `app/app.py` is a monolithic file containing the entire backend logic, including API endpoints, process management, and SPA hosting.
- **Configuration**:
  1.  **Environment Variables (Highest Priority)**: `ADMIN_PASSWORD` and `SECRET_KEY` are read from the environment.
  2.  **Config File (Optional Fallback)**: If env vars are not set, it attempts to read from `/opt/frp-console/frp-console.conf`. This file is optional.
- **Authentication**:
  - A session-based system. The `POST /login` endpoint validates credentials and sets a session cookie.
  - The login endpoint expects `application/x-www-form-urlencoded` data, not JSON, due to the current frontend implementation in `login.tsx`.
  - API routes under `/api` are protected by the `@login_required` decorator. The main SPA pages are not, as protection is handled by the frontend.
- **Serving**: In production, the Flask app serves two roles:
  1.  Provides the backend API at `/api/*`.
  2.  Serves the compiled React frontend as static files from the `frontend/dist` directory. A catch-all route (`serve_spa`) directs all non-API traffic to `index.html`, allowing React Router to manage frontend navigation.
- **Process Management**: The backend starts and stops `frpc` clients as daemonized `subprocess.Popen` processes. It tracks their status by searching for processes whose command line includes the path to the client's `.toml` config file.

### Frontend (`/frontend`)

- **Framework**: React, built with Vite.
- **Key Directories & Files**:
  - `src/pages`: Top-level page components (Dashboard, Clients, Settings, Login).
  - `src/components`: Reusable UI components, built with `shadcn/ui`.
  - `src/lib/api.ts`: A critical utility centralizing `fetch` calls. It automatically handles CSRF tokens for authenticated requests.
  - `src/components/protected-route.tsx`: A wrapper component that enforces authentication. If the user is not logged in, it redirects them to the `/login` page.
- **Authentication Flow**: The `login.tsx` page submits credentials directly to the `POST /login` endpoint. Upon success, the app stores the session and `ProtectedRoute` allows access to other pages. Subsequent API calls use the `apiFetch` utility, which includes the necessary CSRF token.
- **Build**: Running `npm run build` in `/frontend` compiles the application into `frontend/dist`, which is then served by the Flask backend in production.
