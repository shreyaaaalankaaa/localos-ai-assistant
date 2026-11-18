# JARVIS Local OS frontend

See [the project's main README](../README.md) for prerequisites, voice support, backend startup, screenshots/design reference, and app setup.

```bash
npm ci
npm run dev             # Opens the browser UI on http://127.0.0.1:5173
npm run electron:dev    # Starts Electron and attempts backend auto-start
npm run typecheck       # TypeScript validation
npm run build           # Production browser assets
```

The frontend uses React, TypeScript, Vite, React Three Fiber, Drei, Three.js, Lucide icons and Framer Motion. All Earth textures live locally in `public/textures`.

Set `VITE_API_URL` to a different trusted local backend address if necessary; the default is `http://127.0.0.1:8000`.
