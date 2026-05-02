# Project Guidelines

## Architecture
- `app.py` contains the main Dash application, chart generation, localization strings, and calculator/tool sidebar behavior.
- `function_app.py` is the Azure Functions entrypoint that exposes the Dash server through WSGI.
- `assets/styles.css` contains shared UI styling for the Dash frontend.
- Keep UI behavior changes in `app.py` and visual styling changes in `assets/styles.css` unless there is a strong reason to split further.

## Build And Run
- Dependencies are managed with `uv` using `pyproject.toml` and `uv.lock`.
- Use `uv sync` to install dependencies.
- Use `uv run python app.py` to run the local Dash app.
- Do not treat `requirements.txt` as the source of truth; it is only exported for deployment compatibility.

## Conventions
- Keep changes minimal and localized; avoid broad refactors unless required by the task.
- Preserve the current bilingual pattern by adding both `zh` and `en` entries to `I18N` when introducing user-facing text.
- Reuse shared helpers such as figure finalization and common layout/config objects instead of duplicating chart configuration.
- Prefer project-wide consistency for chart interaction and legend behavior across all figures.

## Deployment
- Azure deployment uses `.github/workflows/deploy-azure.yml`.
- CI and deployment should follow the `uv` workflow, not direct `pip install -r requirements.txt` as the primary dependency path.