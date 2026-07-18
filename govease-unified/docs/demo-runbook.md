# Live Demo Runbook

## Public endpoints

- Portal: `https://gov-ease-ai.vercel.app`
- Widget: `https://gov-ease-ai.vercel.app/widget`
- API: `https://govease-ai.onrender.com`
- API readiness: `https://govease-ai.onrender.com/api/v1/ready`

## Three-minute scenario

1. Enter: `Tôi thuê nhà và muốn đăng ký tạm trú.`
2. Show the selected procedure, official source, required documents and ordered steps.
3. Continue to pre-submission checking.
4. Enter an invalid identity number, use the same permanent and temporary address, set the end date before the start date, and leave accommodation proof/signature empty.
5. Run validation and show field-level explanations and suggested fixes.
6. Correct the fields and run validation again until the form is ready.
7. Open `/widget` or embed `public/embed.js` to demonstrate integration without installing an application.

## Pre-demo checks

```powershell
curl.exe -f https://govease-ai.onrender.com/api/v1/health
curl.exe -i -X OPTIONS "https://govease-ai.onrender.com/api/v1/intake" `
  -H "Origin: https://gov-ease-ai.vercel.app" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: content-type"
```

The preflight must return `200` and the exact Vercel origin. Keep a short screen recording as fallback for cold-start or venue-network failures.

## Honest pilot boundary

The end-to-end pilot covers registration of birth and temporary residence. Other catalog entries are discovery data and must not be presented as having the same form-validation depth. Guidance remains advisory and links to the official National Public Service Portal record.
