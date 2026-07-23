from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import Response
import cv2
import numpy as np
from ultralytics import YOLO
import pathlib
import platform
from sqlalchemy import create_engine, text
from data import engine
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image
import uuid
import os
import io
from time import time
from PIL.ExifTags import TAGS, GPSTAGS


def extract_gps_and_date(image_source):
    try:
        image = Image.open(image_source)
        exif_data = image._getexif()

        if not exif_data:
            return None, None, None

        gps_info = {}
        date_taken = None

        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for gps_tag_id in value:
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag] = value[gps_tag_id]
            elif tag in ["DateTimeOriginal", "DateTime"]:
                if not date_taken:
                    date_taken = str(value)

        required_keys = ["GPSLatitude", "GPSLatitudeRef",
                         "GPSLongitude", "GPSLongitudeRef"]
        has_gps = all(key in gps_info for key in required_keys)

        if not has_gps:
            return None, None, date_taken

        def convert_to_float(val):
            if isinstance(val, tuple):
                return val[0] / val[1] if val[1] != 0 else 0.0
            return float(val)

        def dms_to_decimal(dms, ref):
            degrees = convert_to_float(dms[0])
            minutes = convert_to_float(dms[1])
            seconds = convert_to_float(dms[2])

            decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
            if ref in ['S', 'W']:
                decimal = -decimal
            return decimal

        latitude = dms_to_decimal(
            gps_info["GPSLatitude"], gps_info["GPSLatitudeRef"])
        longitude = dms_to_decimal(
            gps_info["GPSLongitude"], gps_info["GPSLongitudeRef"])

        return latitude, longitude, date_taken

    except Exception:
        return None, None, None


classifier = torch.load('severity_full_model.pth',
                        map_location='cpu', weights_only=False)
classifier.eval()

class_names = ['low', 'medium', 'severe']

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def classify_severity(crop_img):
    crop = Image.fromarray(crop_img)
    img = transform(crop).unsqueeze(0)
    with torch.no_grad():
        preds = classifier(img)
        class_idx = preds.argmax(dim=1).item()
    return class_names[class_idx]


pathlib.WindowsPath = pathlib.PosixPath
detect_model = YOLO("best_detection_model.pt")

dicti = {"severe": 5, "medium": 3, "low": 1}


def calc(listing):
    if len(listing) == 0:
        return 0

    raw_score = 0
    for item in listing:
        raw_score += dicti.get(item, 0)

    min_possible = len(listing) * 1   # all low
    max_possible = len(listing) * 5   # all severe

    # Normalize to 0-10
    normalized = 1 + (raw_score - min_possible) / \
        (max_possible - min_possible) * 9

    return round(normalized, 1)


app = FastAPI()


@app.post("/upload_image")
async def upload(
    file: UploadFile = File(...),
    client_lat: float = Form(None),
    client_lon: float = Form(None),
):

    img_binary = await file.read()
    nparr = np.frombuffer(img_binary, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    result = detect_model(img, conf=0.4)[0]
    ls = []
    new_img = img.copy()
    if len(result.boxes) == 0:
        return {"severity": 0, "report_id": "0"}
    lat, lon, t = extract_gps_and_date(io.BytesIO(img_binary))
    if lat is None or lon is None:
        lat = client_lat
        lon = client_lon
    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        cv2.rectangle(new_img, (int(x1), int(y1)),
                      (int(x2), int(y2)), (0, 0, 255), 2)
        crop = img[int(y1):int(y2), int(x1):int(x2)]
        if crop.size == 0:
            continue
        crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        severe = classify_severity(crop)
        ls.append(str(severe))
    res = calc(ls)
    report_id = str(uuid.uuid4())

    # Encode both images to JPEG bytes in memory (no disk writes,
    # since Render's filesystem is ephemeral and wipes on every restart/deploy)
    _, orig_buf = cv2.imencode(".jpg", img)
    orig_bytes = orig_buf.tobytes()

    _, annotated_buf = cv2.imencode(".jpg", new_img)
    annotated_bytes = annotated_buf.tobytes()

    with engine.connect() as conn:
        conn.execute(text("""INSERT INTO mybase (id, file, annotated_file, severity, longtitude, latitude, pothole_count, created_at) 
                     VALUES (:id, :file, :annotated_file, :severity, :longtitude, :latitude, :pothole_count, :created_at)"""),
                     {
            "id": report_id,
            "file": orig_bytes,
            "annotated_file": annotated_bytes,
            "severity": res,
            "longtitude": lon,
            "latitude": lat,
            "pothole_count": len(result.boxes),
            "created_at": str(t),
        },
        )
        conn.commit()
    return {"severity": res, "report_id": report_id}


@app.get("/health")
def health():
    return {"status": "running"}


@app.get("/")
def root():
    return {"hello": "world"}


@app.get("/reports")
def reports():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT * FROM mybase"))
        rows = res.fetchall()
    ress = []
    for row in rows:
        ress.append({"id": row[0], "image_url": f"/collected/{row[0]}",
                    "severity": row[3], "lon": row[4], "lat": row[5], "date_taken": row[7]})
    return ress


@app.post("/verify")
async def verify(file: UploadFile = File(...)):
    img_binary = await file.read()
    nparr = np.frombuffer(img_binary, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return {"Error": "no image provided"}
    return {}


@app.get("/collected/{request_id}")
def get_image(request_id: str):
    with engine.connect() as conn:
        res = conn.execute(text("SELECT annotated_file FROM mybase WHERE id = :id"), {
                           "id": request_id})
        row = res.fetchone()
    if row is None or row[0] is None:
        return {"error": "not found"}
    return Response(content=bytes(row[0]), media_type="image/jpg")
