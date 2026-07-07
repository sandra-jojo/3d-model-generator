# Frontend — LLM-Based 3D Model Generator

Next.js (App Router) + TailwindCSS + shadcn/ui frontend for the [3D Model Generator](../README.md). Deployed on Vercel: https://frontend-mocha-three-73.vercel.app

## Features

- Prompt input for text → 3D generation
- Image upload for photo → 3D generation
- Live PNG preview of the generated model
- One-click refinement (bigger / smaller / taller)
- STL download for 3D printing

## Development

```bash
npm install
npm run dev    # http://localhost:3000
```

The backend URL is configured in `app/page.tsx`; point it to `http://localhost:8000` when running the API locally (see the root README for backend setup).

## Quality checks

```bash
npm run lint
npm run build
```

Both run automatically in CI on every push.
