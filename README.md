# LiftLog
A web application designed for the fitness community and those wishing to join. Get started by creating new workouts, tracking your progress, and having fun!

## Running LiftLog on your computer

LiftLog is a Python + Flask web app. These steps are for Windows (PowerShell, e.g. the VS Code terminal). Run them from the `LiftLog` folder.

**You need:** Git and Python 3.11 or newer (`python --version` should print a version).

1. **Create a virtual environment** (a private folder for this project's packages), once:
   ```
   python -m venv venv
   ```
2. **Turn it on** (every time you open a new terminal):
   ```
   venv\Scripts\Activate.ps1
   ```
   Success: the prompt starts with `(venv)`. If PowerShell says running scripts is disabled, run
   `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, answer `Y`, and try again.
   (Mac/Linux: `source venv/bin/activate`)
3. **Install the packages**, once (and again whenever `requirements.txt` changes):
   ```
   pip install -r requirements.txt
   ```
4. **Create your settings file**, once:
   ```
   copy .env.example .env
   ```
   Then open `.env` and replace `SECRET_KEY` with the output of
   `python -c "import secrets; print(secrets.token_hex(32))"`.
   `.env` is ignored by git, so never commit it.
5. **Create the database tables** (once, and again whenever someone adds a migration):
   ```
   flask --app run db upgrade
   ```
   Success: it ends with lines like `Running upgrade  -> xxxx, Create users table`.
6. **Start the app:**
   ```
   python run.py
   ```
   Open http://127.0.0.1:5000 . You should see "Welcome to LiftLog".
   http://127.0.0.1:5000/health should show `{"database": "ok", "status": "ok"}`. Press `Ctrl+C` to stop.
7. **Run the tests:**
   ```
   pytest
   ```
   Success: every test passes.

### Database

By default the app uses a SQLite file (`instance/liftlog.db`), so nothing else needs installing.
The project plan is to use **MySQL**: install MySQL, create a database and user, then set
`DATABASE_URL` in `.env` (see the example in `.env.example`). No code changes are needed.

### Changing the database tables (migrations)

Tables are defined as Python classes in `app/models.py`. After you add or change a model:
```
flask --app run db migrate -m "Describe the change"
flask --app run db upgrade
```
The first command writes a new file in `migrations/versions/`. Read it, then commit it with your
code so teammates get the same change when they run `flask --app run db upgrade`.

## Project layout

```
app/
  __init__.py      builds the app (create_app)
  config.py        settings, read from .env
  extensions.py    database, login manager, password hashing, CSRF protection
  models.py        database tables (User so far)
  main/            general pages (home, dashboard, /health)
  auth/            register, log in, log out
  templates/       HTML pages (base.html is the shared layout)
  static/          CSS, JavaScript and images
migrations/        database table changes (made by Flask-Migrate)
tests/             automated tests (run with pytest)
docs/              course documents (RD, IT, progress reports)
run.py             starts the app
```
Each new feature (login, exercises, workout templates, sessions...) gets its own folder in `app/`, like `app/main/`.
