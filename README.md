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

### `d2-grail`
Node-based Diablo II grail tooling.

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

The repo includes a GitHub Actions workflow that can publish the `wellness` app directly to GitHub Pages.

After pushing to GitHub:

1. Open the repository on GitHub.
2. Go to `Settings -> Pages`.
3. Under `Build and deployment`, choose `GitHub Actions`.
4. Push a change to `wellness`, or manually run the `Deploy Wellness To GitHub Pages` workflow.
5. Share the Pages URL GitHub gives you.

Because `wellness` is plain static HTML/CSS/JS, visitors do not need to install anything.
