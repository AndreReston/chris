# Project setup & run (Windows PowerShell)

1. Create and activate a virtual environment:

```powershell
python -m venv venv
# If PowerShell blocks activation, run this once in the same shell:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the app:

```powershell
python .\templates\bookworm\app.py
```

Alternate quick install (no `requirements.txt`):

```powershell
pip install Flask Flask-SQLAlchemy Werkzeug
```

Notes:
- The Flask app file is `templates\bookworm\app.py`. Running it directly uses `app.run(debug=True)`.
- If you prefer `flask run`, set the environment variable like:

```powershell
$env:FLASK_APP = 'templates/bookworm/app.py'
flask run
```
