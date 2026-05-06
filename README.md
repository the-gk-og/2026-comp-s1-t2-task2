# RSVP Event Registration

Simple event registration app with:

- Public event form pages
- Admin dashboard at `/admin`
- LocalStorage + backend submission storage
- Search, edit, delete, and CSV export

## Tech Stack

- Backend: Flask (`server.py`)
- Frontend: HTML/CSS/JS templates
- Storage: CSV by default (`data/*.csv`), optional PostgreSQL

## Quick Start

1. Create and activate a Python virtual environment
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) copy env file:

```bash
cp .env.example .env
```

4. Run the app:

```bash
python3 server.py
```

Default server: `http://localhost:3001`

## Main Routes

- `/` blank landing route
- `/admin` admin dashboard
- `/event/<event_id>` customer-facing event registration page
- `/health` health check endpoint

## Notes

- Event submissions include:
  - Name
  - Email
  - Ticket type
  - Dietary requirements
  - Session selections
  - Payment status
  - Timestamp
- Admin dashboard supports:
  - Create/delete events
  - Copy event link
  - Search submissions
  - Edit/delete submissions
  - Download CSV

woops forgot to save read me

but design is lacking becasue i didnot enjoy and have that much of a vision