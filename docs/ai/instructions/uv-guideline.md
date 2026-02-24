# UV Project Usage Guidelines
This project uses `uv` for Python package and environment management. 
Please follow these command patterns instead of standard `pip` or `python` commands:

### 1. Environment & Initialization
- Initialize a new project: `uv init`
- Create/Sync virtual environment: `uv sync` (Creates .venv and installs dependencies from lockfile)
- Update lockfile: `uv lock`

### 2. Dependency Management
- Add a package: `uv add <package>`
- Add a development dependency: `uv add --dev <package>`
- Remove a package: `uv remove <package>`
- Upgrade a package: `uv add --upgrade <package>`

### 3. Running Code
- Run a script: `uv run <script.py>`
- Run a module: `uv run -m <module>`
- Run an arbitrary command in venv: `uv run <command>` (e.g., `uv run pytest`)
- Open a REPL: `uv run python`

### 4. Tool & Python Management
- Install a global tool: `uv tool install <tool>` (e.g., ruff, black)
- Install a specific Python version: `uv python install 3.12`
- Run a one-off script with specific dependencies: 
  `uv run --with requests script.py`

### Key Rule:
DO NOT use `pip install` or `python -m venv`. 
ALWAYS prefix execution with `uv run` to ensure the correct virtual environment is used.