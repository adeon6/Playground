# Playground

A small multi-app workspace with a few game and utility tools.

## Apps

### `gd`
Grim Dawn / Grimarillion resistance-reduction pair finder.

- Dev: `cd gd && npm run dev`
- Build: `cd gd && npm run build`
- Default local URL: `http://localhost:5173`

### `d2`
Diablo II Resurrected runeword helper.

- Dev: `cd d2 && npm run dev`
- Build: `cd d2 && npm run build`
- Default local URL: `http://localhost:5174`

### `wellness`
Supplement / wellness helper app.

- Dev: `cd wellness && npm run dev`
- Build: `cd wellness && npm run build`
- Default local URL: `http://localhost:5175`
- GitHub Pages: designed to be publishable directly from the `wellness` folder via the included workflow

### `poe`
Path of Exile build guide app seeded from a Path of Building import.

- Dev: `cd poe && npm run dev`
- Build: `cd poe && npm run build`
- Default local URL: `http://localhost:5176`

### `d2-grail`
Node-based Diablo II grail tooling.

### `reply-lab`
Shareable static simulator for WhatsApp lead messages and suggested replies.

## Repo Notes

- `node_modules` and build output are intentionally ignored.
- Lockfiles are committed.
- Each frontend app is self-contained in its own folder.

## Sharing `gd`

The easiest way to share the Grim Dawn app is to deploy the `gd` folder with Netlify or Vercel, or publish it from a GitHub repo.

Basic deploy flow:

1. Push this repo to GitHub.
2. Connect the repo to your hosting provider.
3. Set the project root to `gd`.
4. Use the build command `npm run build`.
5. Use the output directory `dist`.

## Sharing `wellness`

The repo includes a GitHub Actions workflow that publishes a combined GitHub Pages site for this repo.

After pushing to GitHub:

1. Open the repository on GitHub.
2. Go to `Settings -> Pages`.
3. Under `Build and deployment`, choose `GitHub Actions`.
4. Push a change to `wellness`, `reply-lab`, or `pages`, or manually run the `Deploy Playground Pages` workflow.
5. The shared landing page will be published at the Pages URL GitHub gives you.

Because these apps are plain static HTML/CSS/JS, visitors do not need to install anything.

## Pages URLs

Once deployed, you can share:

1. The repo landing page: `/Playground/`
2. Reply Lab directly: `/Playground/reply-lab/`
3. Wellness directly: `/Playground/wellness/`
