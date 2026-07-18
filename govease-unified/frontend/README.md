# GovEase Portal Demo

Next.js frontend that demonstrates GovEase AI embedded in a public-service portal. It remains architecturally independent from the Python backend and communicates only through `/api/v1` HTTP endpoints.

## Run

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL` to the FastAPI origin. The full portal demo is at `/`; the iframe-compatible assistant is at `/widget`.

## Embed

```html
<script
  src="https://YOUR-FRONTEND-DOMAIN/embed.js"
  data-base-url="https://YOUR-FRONTEND-DOMAIN"
  defer
></script>
```

This is a hackathon simulation, not an official government website. It references official procedure sources but deliberately avoids copying the national emblem or presenting itself as the National Public Service Portal.
