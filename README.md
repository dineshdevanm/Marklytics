# Marklytics - Student Dashboard

Marklytics is a Flask web application for uploading student academic records, analyzing performance, and visualizing outcomes with charts.

## Features

- User registration and login
- Upload student data from CSV or Excel files
- Auto-filtered columns for relevant academic fields
- GPA distribution chart
- Course-wise pass/fail and grade distribution charts
- Learner categorization:
  - Slow learners (CGPA <= 6.5)
  - Fast learners (CGPA >= 9.0)
- Dashboard with latest dataset view and search filters (batch, year, section)

## Tech Stack

- Python
- Flask
- MongoDB (PyMongo)
- Pandas
- Matplotlib
- Seaborn
- Jinja2 templates + custom CSS

## Project Structure

- app.py: Main Flask application
- requirements.txt: Python dependencies
- static/style.css: Application styles
- templates/: HTML templates

## Prerequisites

- Python 3.10+ recommended
- MongoDB running locally on default port `27017`

Default MongoDB connection used in the app:

`mongodb://localhost:27017/`

Database and collections used:

- Database: `student_dashboard_db`
- Collections: `users`, `student_data`

## Setup and Run

1. Open a terminal in the project folder.
2. Create and activate a virtual environment.
3. Install dependencies.
4. Start the Flask app.

Example (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

The app will run at:

`http://127.0.0.1:5000`

## How to Use

1. Register a new user.
2. Log in.
3. Open Upload page.
4. Upload a CSV/XLSX file and provide batch, year, and section.
5. View generated analytics and learner categories.
6. Open Dashboard to view recent data or filter by batch/year/section.

## Input Data Notes

The upload flow keeps columns that include these keywords (case-insensitive):

- `register number`
- `name`
- `gpa`
- `cgpa`
- `grade obtained`

Only the first 40 rows are processed.

## Troubleshooting

- If MongoDB is not running, login/register and upload operations will fail.
- If charts do not render, ensure all plotting dependencies are installed from `requirements.txt`.
- If Excel upload fails, confirm `openpyxl` is installed.

## Security Note

The current app contains a hardcoded Flask secret key in `app.py`. For production, move secrets to environment variables.

## License

No license file is currently included. Add one if you plan to distribute this project publicly.
