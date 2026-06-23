# Guided Options And Folder Picker

## Goal

Replace free-text operational fields in the local UI with guided choices: RF months discovered automatically, UF list from Brazil states, friendly cleanup labels, and native folder selection through the local Python backend.

## Requirements

- `Mes RF` must be selected from months discovered from the Receita Federal WebDAV share.
- `UF` must be selected from a fixed list of Brazilian UFs.
- The UI must stop exposing the `Escopo` field and municipality recorte for now.
- The UI must remove wording about `recorte geografico` and `Brasil inteiro fora do MVP`.
- Cleanup select must display friendly labels when open and closed.
- Data and output directories must be chosen through a folder button, not typed as normal text.
- Folder selection uses the local FastAPI backend to open a native OS directory chooser with Python.

## API Design

- Extend `GET /options` with `months` and `states`.
- Keep existing `tables`, `cleanup_modes`, and `scope_types` fields for compatibility.
- Add `POST /directories/pick` with optional `initial_dir` and response `{ "path": string | null }`.
- A cancelled folder dialog returns `path: null`.

## UI Design

- `Mes RF` becomes a Select populated from `options.months`.
- `UF` becomes a Select populated from `options.states`.
- UI submits `scope_type: "uf"` and `municipio: null`.
- Directory fields become readonly displays plus a `Pasta` button.
- If folder selection fails, reuse the existing error alert.

## Verification

- Add API tests for options discovery and directory picker endpoint.
- Run `python -m pytest -q`.
- Run `npm.cmd --prefix "web" run build`.
- Run `npm.cmd --prefix "web" run lint`.
