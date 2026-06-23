# Technical Panel Redesign

## Goal

Replace the current generic, serif-looking CNPJ pipeline screen with a modern technical panel: clean typography, sophisticated light background, dense professional cards, and clearer execution hierarchy.

## Scope

- Keep the existing Next.js, shadcn/ui, Tailwind, FastAPI, and pipeline behavior.
- Do not add new UI libraries.
- Redesign only the local web interface shell and form presentation.
- Preserve all existing form inputs, selected table behavior, submit behavior, progress display, error display, and result display.

## Visual Direction

- Use a clean sans-serif stack wired correctly through Next font variables.
- Replace the oversized hero with a compact product-console header.
- Use a light neutral surface with subtle blue/indigo accents and restrained gradients.
- Make cards denser and more structured, with stronger labels and less decorative whitespace.
- Make the execution panel feel like a professional data tool rather than a landing page.

## Layout

- Full page remains responsive.
- Desktop uses a two-column workbench: main configuration on the left and a sticky execution/sidebar panel on the right.
- Mobile stacks sections vertically with the execution panel after configuration.
- Header contains product name, concise title, short description, and status badges for local processing, CSV + Parquet output, and FastAPI.

## Components

- `layout.tsx`: ensure font CSS variables map to the active font names.
- `globals.css`: update design tokens, background utility, card/input polish, and typography defaults.
- `pipeline-console.tsx`: reorganize markup and class names while keeping state and API flow unchanged.

## States

- Pending state disables submit and shows spinner text.
- Progress remains deterministic for now: idle, pending, complete.
- Errors appear in the execution column with clear destructive styling.
- Results show row count and output paths in a compact success card.

## Verification

- Run `python -m pytest -q`.
- Run `npm.cmd --prefix "web" run build` on Windows.
