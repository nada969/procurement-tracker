# Procurement Tracker (live database)

Track procurement **Projects > Packages > Suppliers**: technical and commercial status, bids against budget,
overdue actions, side-by-side comparison. Data lives in **PostgreSQL** (Neon), with real foreign keys and cascade deletes.

Stack: FastAPI + SQLAlchemy 2 + PostgreSQL, plain HTML/JS front end (no build step).

## Screenshots (fictional demo data)
| Projects | Packages |
|---|---|
| ![Projects](docs/01-projects.png) | ![Packages](docs/02-packages.png) |

| Suppliers | Compare |
|---|---|
| ![Suppliers](docs/03-suppliers.png) | ![Compare](docs/04-compare.png) |

![Notes log](docs/05-notes.png)

## Features
- **Project > Package > Supplier** hierarchy with separate technical status and commercial stage
- **Compare tab:** suppliers side by side, non-compliant offers greyed, best compliant values highlighted
- **Notes log** on every package, optionally tied to one supplier. Notes are dated automatically and kept in the backup
- **Excel export:** per package (leveled comparison + notes) and per project (summary + one sheet per package). Variances are live formulas; sheets print landscape, one page wide. Needs Excel 2019 or Microsoft 365 (uses MINIFS)
- **Backup / restore** as one JSON file

## Deploy (free: Neon + Vercel)
1. **Neon:** create a free project at neon.com and copy the **pooled** connection string (host contains `-pooler`).
2. **GitHub:** push this repo (never commit `*.db`, `.venv` or connection strings).
3. **Vercel:** Add New > Project > import the GitHub repo. Framework preset can stay "Other" / auto-detected (FastAPI).
4. Under **Environment Variables** add `DATABASE_URL` (Neon string), `APP_USER`, `APP_PASSWORD`, then Deploy.
5. Open the `.vercel.app` link and log in. Tables are created automatically on the first request.
6. Optional demo data (fictional): run `python seed.py` once locally with `DATABASE_URL` set to a **test** database.
Vercel's free Hobby plan is for personal, non-commercial use; check their terms.

## Back up your data (important)
Neon's free plan only keeps a short restore window (about 6 hours). Use **Download backup** on the Projects page
weekly. **Restore backup** merges a backup file back in (same ids are overwritten, others kept).

## Run locally
```bash
pip install -r requirements.txt
uvicorn app:app --reload          # uses sqlite:///tracker.db unless DATABASE_URL is set
pytest                            # tests (use a throwaway database, never your real one)
```

## Files
| File | Purpose |
|---|---|
| `app.py` | API, database tables, login, notes, backup/restore, export routes |
| `export_xlsx.py` | Builds the Excel workbooks |
| `public/` | `index.html`, `main.js` (screens), `store.js` (talks to the API), `style.css` |
| `schema.sql` | Reference schema and an example analytics query |
| `seed.py` | Fictional demo data |
| `test_api.py` | Tests: hierarchy, foreign keys, cascade delete, backup/restore, login |

## Notes
- Neon's free compute sleeps after 5 idle minutes and Vercel functions start cold, so the first request after a pause is slow.
- Never commit real vendor names, prices or connection strings.
