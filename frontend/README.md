# AKILI frontend

React + TypeScript + Vite application. **Not initialized yet.**

This directory is deliberately empty. There is no `package.json` here yet, and
there must not be one at the repository root — when the app is scaffolded, its
manifest belongs at `frontend/package.json`.

Like the backend, the frontend is run from inside its own folder:

```bash
cd frontend
npm install
npm run dev
```

The frontend never receives secrets. It talks to the backend over HTTP; only
non-secret, build-time-public values (such as the backend URL) may reach it.

Node available on this machine: v24.13.0 (npm 11.6.2).
