# Pritam Ranjan Kalita — Portfolio Website

Personal academic portfolio site for PhD applications, built with Tailwind CSS and Alpine.js and deployed on GitHub Pages.

## Pages

- `index.html` — single-page site: About, Education, Experience, Skills, Projects, and Contact, navigated via anchor links (`#about`, `#education`, `#experience`, `#skills`, `#projects`, `#contact`)
- `cv.html` — CV (embedded PDF + Overleaf link), the only separate page

`education.html`, `experience.html`, `skills.html`, and `projects.html` are kept as thin redirect stubs (to `index.html#<section>`) purely for backward compatibility with any old bookmarks or links — they contain no real content of their own. Safe to delete if you don't need that compatibility.

## Local preview

This is a fully static site — no build step. Just open `index.html` in a browser, or serve the folder locally:

```
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Deploying to GitHub Pages

1. Push this repository to GitHub (e.g. `github.com/<your-username>/<your-username>.github.io`, or any repo name).
2. In the repo settings, go to **Settings → Pages** and set **Source** to **GitHub Actions**.
3. The included workflow at `.github/workflows/deploy-pages.yml` will automatically build and deploy the site on every push to `main`.
4. Your site will be live at `https://<your-username>.github.io/<repo-name>/` (or `https://<your-username>.github.io/` if the repo is named `<your-username>.github.io`).

## Before publishing — things to update

- Double check the Overleaf CV link in `cv.html` still resolves to your latest CV.
- Swap `assets/cv/CV_Pritam_Kalita.pdf` whenever you export a fresh copy from Overleaf, so the embedded/download version stays current.

## Credits

Originally based on the "Folio" freelance portfolio template by Laurent Begey, distributed by ThemeWagon, and substantially rewritten for academic/PhD-application use.
