# Guided Options And Folder Picker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace text entry for RF month, UF, and directories with guided options and a native folder picker.

**Architecture:** The backend owns environment-dependent operations: RF month discovery and native folder picking. The frontend consumes `/options` and `/directories/pick`, keeps the existing run payload, and submits only UF scope from the current UI.

**Tech Stack:** FastAPI, Pydantic, Python tkinter, Next.js, React, shadcn/ui, Tailwind CSS.

---

## File Structure

- Modify `rf_cnpj/api/app.py`: inject month discovery and directory picker, extend `/options`, add `/directories/pick`.
- Modify `rf_cnpj/core/ui_options.py`: add Brazilian UF labels.
- Create `rf_cnpj/core/file_dialog.py`: native directory picker wrapper.
- Modify `tests/test_api.py`: red/green tests for `/options` and `/directories/pick`.
- Modify `web/src/lib/api.ts`: add months/states types and `pickDirectory` client.
- Modify `web/src/components/pipeline-console.tsx`: replace inputs with selects and folder buttons.

### Task 1: Backend Options And Picker

- [ ] Add failing tests for discovered months, UF list, and directory picker.
- [ ] Implement `BRAZIL_STATES` and `pick_directory`.
- [ ] Extend `create_app` dependency injection for tests.
- [ ] Implement `/options` and `/directories/pick`.
- [ ] Run targeted API tests.

### Task 2: Frontend Guided Inputs

- [ ] Extend API types and add `pickDirectory`.
- [ ] Replace month and UF text inputs with Select controls.
- [ ] Remove scope/muncipio UI and recorte copy.
- [ ] Replace directory text editing with readonly fields and folder buttons.
- [ ] Render friendly cleanup labels in the closed trigger.

### Task 3: Verification

- [ ] Run `python -m pytest -q`.
- [ ] Run `npm.cmd --prefix "web" run build`.
- [ ] Run `npm.cmd --prefix "web" run lint`.
