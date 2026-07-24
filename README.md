# 🚧 TARIQ AI

**Automated Road Hazard Analysis & Municipal Dispatch Portal**

TARIQ AI is a computer vision app that detects and scores potholes from photos. Upload an image of a road, and it automatically detects potholes, classifies their severity, and logs the report — complete with location and timestamp — onto an interactive map dashboard.

This project was built as part of a 4-week deep dive into computer vision and the beginning of a broader journey into machine learning.

---

## How it works

1. **Upload** — a user submits a photo of a road surface through the web dashboard.
2. **Detection** — a YOLO object detection model scans the image and locates potholes.
3. **Severity classification** — each detected pothole is cropped and passed through a separate classification model, which rates it `low`, `medium`, or `severe`.
4. **Scoring** — individual severities are combined into a single normalized severity score (0–10) for the whole image.
5. **Geotagging** — location and date are pulled from the image's EXIF metadata when available, with a fallback to the browser's live geolocation if the photo has no embedded GPS data.
6. **Storage** — the original photo, the annotated (bounding-box) version, and all metadata are saved to a Postgres database.
7. **Visualization** — all reports are plotted on an interactive map, with click-to-inspect details and aggregate stats (total reports, average severity).

---

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | Streamlit, PyDeck (map visualization) |
| Backend | FastAPI |
| Detection model | YOLO (Ultralytics) |
| Severity classifier | PyTorch / torchvision (custom-trained CNN) |
| Database | PostgreSQL (images stored as `BYTEA`) |
| Containerization | Docker, docker-compose |

---

## Project structure

```
.
├── docker-compose.yml
├── best_detection_model.pt     # YOLO pothole detection weights
├── severity_full_model.pth     # severity classification model weights
├── backend/
│   ├── main.py                 # FastAPI app: detection, scoring, storage, endpoints
│   ├── data.py                 # DB engine + table schema setup
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── app.py                  # Streamlit dashboard
    ├── requirements.txt
    └── Dockerfile
```

---

## Running locally

**Requirements:** Docker and Docker Compose installed.

```bash
docker compose up --build
```

This starts three services:
- `database` — Postgres, seeded with the `mybase` table on first run
- `backend` — FastAPI server on `http://localhost:8000`
- `frontend` — Streamlit dashboard on `http://localhost:8501`

Open `http://localhost:8501` in your browser to use the app.

---

## Environment variables

| Variable | Used by | Description |
|---|---|---|
| `DATABASE_URL` | backend | Postgres connection string. Defaults to a local `sqlite:///reports.db` if unset (not recommended for real use). |
| `BACKEND_URL` | frontend | URL the frontend uses to reach the backend API. Defaults to `http://backend:8000` for docker-compose's internal network. |

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload_image` | Upload a road image for detection, scoring, and storage |
| `GET` | `/reports` | Fetch all stored reports (id, severity, coordinates, date) |
| `GET` | `/collected/{report_id}` | Fetch the annotated (bounding-box) image for a report |
| `POST` | `/verify` | Validate that an uploaded file is a readable image |
| `GET` | `/health` | Health check |

---

## Notes

- Images are stored directly in Postgres as binary data rather than on disk, so the app works correctly in environments with ephemeral filesystems (e.g. container platforms that wipe local storage on restart/redeploy).
- If a photo has no EXIF GPS data, the app falls back to the browser's live location at the time of upload (requires HTTPS or `localhost`, and user permission).