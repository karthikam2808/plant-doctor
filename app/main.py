# ==== FastAPI App ====

# ==== Imports (move all to top) ====
import io
import json
import torch
import timm
from torch import nn
from torchvision import transforms
from PIL import Image
from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os
import sqlite3
from report.pdf_generator import generate_pdf_report
import re

app = FastAPI()

# ==== Helper ==== 
def is_logged_in(request: Request):
    return request.cookies.get("logged_in") == "true"

# ==== Mount Static Folder ====
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ==== Database Setup ====
DB_PATH = "users.db"
if not os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)
    conn.commit()
    conn.close()
    print("✅ Users database created.")
# ==== Prediction History Table ====
def create_history_table():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        prediction TEXT,
        confidence REAL,
        loss REAL,
        timestamp TEXT
    )
    """)
    conn.commit()
    conn.close()
create_history_table()

# ==== Load Class Indices ====
with open("model/class_indices.json", "r") as f:
    class_indices = json.load(f)
index_to_class = {int(k): v for k, v in class_indices.items()}

# ==== Load Model ====
model_path = "model/model.pth"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = timm.create_model("tf_efficientnetv2_b3", pretrained=False, num_classes=len(index_to_class))
model.load_state_dict(torch.load(model_path, map_location=device))
model.eval()

# ==== Transform ====
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])

# Load disease info JSON once
with open("report/disease_info.json", "r", encoding="utf-8") as f:
    DISEASE_INFO = json.load(f)

# ==== Routes ====
# Prediction graph page route
@app.get("/prediction_graph")
def prediction_graph_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")
    return FileResponse("app/static/prediction_graph.html")
@app.get("/about")
def about(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")
    return FileResponse("app/static/about.html")

@app.get("/services")
def services(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")
    return FileResponse("app/static/services.html")

@app.get("/aiassist")
def aiassist(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")
    return FileResponse("app/static/aiassist.html")

@app.get("/")
def root(request: Request):
    if not is_logged_in(request):
        return FileResponse("app/static/login.html")
    return FileResponse("app/static/index.html")

@app.get("/login")
def login_page():
    return FileResponse("app/static/login.html")

@app.get("/history")
def history_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")
    return FileResponse("app/static/history.html")

@app.get("/api/history")
def api_history(request: Request):
    print("[DEBUG] /api/history endpoint called")
    if not is_logged_in(request):
        print("[DEBUG] Not logged in, redirecting to /login")
        return JSONResponse(content={"error": "Not logged in."}, status_code=401)
    email = request.cookies.get("email")
    print(f"[DEBUG] Email from cookie: {email}")
    if not email:
        print("[DEBUG] No email found in cookie")
        return JSONResponse(content={"error": "User not found."}, status_code=401)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT prediction, confidence, timestamp FROM history WHERE email = ? ORDER BY timestamp DESC", (email,))
    rows = cursor.fetchall()
    conn.close()
    print(f"[DEBUG] History rows for user '{email}': {rows}")
    return JSONResponse(content={"history": rows})

@app.post("/api/clear_history")
def clear_history(request: Request):
    print("[DEBUG] /api/clear_history called")
    if not is_logged_in(request):
        print("[DEBUG] Not logged in")
        return JSONResponse(content={"error": "Not logged in."}, status_code=401)
    email = request.cookies.get("email")
    print(f"[DEBUG] Email from cookie: {email}")
    if not email:
        print("[DEBUG] No email found in cookie")
        return JSONResponse(content={"error": "User not found."}, status_code=401)
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history WHERE email = ?", (email,))
        conn.commit()
        conn.close()
        print(f"[DEBUG] Cleared history for user: {email}")
        return JSONResponse(content={"success": True})
    except Exception as e:
        print(f"[ERROR] Failed to clear history: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/signup")
def signup(email: str = Form(...), password: str = Form(...)):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        conn.close()
        print(f"✅ New user registered: {email}")
        return RedirectResponse(url="/login", status_code=303)
    except sqlite3.IntegrityError:
        return JSONResponse(content={"error": "Email already exists"}, status_code=400)

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    conn.close()
    if user:
        print(f"✅ User logged in: {email}")
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="logged_in", value="true", httponly=True)
        response.set_cookie(key="email", value=email, httponly=True)
        return response
    else:
        return JSONResponse(content={"error": "Invalid email or password"}, status_code=401)

@app.post("/predict")
async def predict(file: UploadFile = File(...), request: Request = None):
    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image = transform(image).unsqueeze(0)

        with torch.no_grad():
            outputs = model(image)
            probabilities = torch.nn.functional.softmax(outputs, dim=1)[0]
            confidence, predicted_idx = torch.max(probabilities, 0)
            class_name = index_to_class[predicted_idx.item()]
            confidence_score = round(confidence.item() * 100, 2)
            # Example loss calculation (cross-entropy with predicted class)
            criterion = nn.CrossEntropyLoss()
            target = torch.tensor([predicted_idx.item()])
            loss = criterion(outputs, target).item()

        # Debug: print username from cookie
        email = None
        if request:
            email = request.cookies.get("email")
            print(f"[DEBUG] Email from cookie: {email}")
        if email:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO history (email, prediction, confidence, loss, timestamp) VALUES (?, ?, ?, ?, ?)",
                               (email, class_name, confidence_score, loss, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                conn.close()
                print(f"[DEBUG] Saved prediction to history for user: {email}")
            except Exception as db_exc:
                print(f"[ERROR] Failed to save history: {db_exc}")
        else:
            print("[DEBUG] No email found in cookie. Prediction not saved to history.")

        return {"prediction": class_name, "confidence": confidence_score, "loss": loss}

    except Exception as e:
        print(f"[ERROR] Exception in /predict: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
# API endpoint for graph data (confidence & loss)

@app.post("/generate_report")
async def generate_report(prediction: str = Form(...), image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return generate_pdf_report(prediction, image_bytes, timestamp)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/calculator")
def calculator_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/login")
    return FileResponse("app/static/calculator.html")

@app.post("/api/calculate_cost")
def calculate_cost(request: Request, farm_size: float = Form(...), unit: str = Form(...)):
    # Example logic: 50kg fertilizer/acre, 2L pesticide/acre, costs
    FERTILIZER_PER_ACRE = 50  # kg
    PESTICIDE_PER_ACRE = 2    # liters
    FERTILIZER_COST_PER_KG = 20  # currency units
    PESTICIDE_COST_PER_L = 150   # currency units
    if unit == "hectare":
        farm_size = farm_size * 2.47105  # convert hectares to acres
    fertilizer_qty = farm_size * FERTILIZER_PER_ACRE
    pesticide_qty = farm_size * PESTICIDE_PER_ACRE
    fertilizer_cost = fertilizer_qty * FERTILIZER_COST_PER_KG
    pesticide_cost = pesticide_qty * PESTICIDE_COST_PER_L
    total_cost = fertilizer_cost + pesticide_cost
    return JSONResponse(content={
        "fertilizer_qty": round(fertilizer_qty, 2),
        "pesticide_qty": round(pesticide_qty, 2),
        "fertilizer_cost": round(fertilizer_cost, 2),
        "pesticide_cost": round(pesticide_cost, 2),
        "total_cost": round(total_cost, 2)
    })

@app.post("/api/aiassist")
async def aiassist_api(request: Request):
    data = await request.json()
    query = data.get("query", "").lower().strip()
    # Greeting detection
    if query in ["hi", "hello", "hey", "hai", "hii", "helo"] or re.match(r"^(hi|hello|hey)[.! ]*$", query):
        return JSONResponse(content={"response": "Hello, how can I assist you?"})
    # Thank you detection
    if query in ["thank you", "thanks", "thanku", "thankyou", "thx", "ty","THANK U"] or re.match(r"^(thank(s| you|u)?)[.! ]*$", query):
        return JSONResponse(content={"response": "You're welcome! If you have more questions, just ask."})
    # If user asks for disease list
    if query in ["diseases", "disease list", "show diseases", "list diseases", "all diseases"]:
        disease_names = [key.replace("_", " ").replace("__", " ") for key in DISEASE_INFO.keys()]
        return JSONResponse(content={"diseases": disease_names, "response": "Select a disease from the list above to get details."})
    # If user selects a disease name
    for key in DISEASE_INFO.keys():
        norm_key = key.replace("_", " ").replace("__", " ").replace("-", " ").lower()
        if query == norm_key:
            info = DISEASE_INFO[key]
            response = f"Fertilizer: {info.get('fertilizer', 'N/A')}\nTreatment: {info.get('treatment', 'N/A')}\nOrganic: {info.get('organic_treatment', 'N/A')}\nChemical: {info.get('chemical_treatment', 'N/A')}\nTips: {info.get('tips', 'N/A')}"
            return JSONResponse(content={"response": response})
    # Find disease/crop in query
    best_match = None
    for key in DISEASE_INFO.keys():
        # Normalize key for matching
        norm_key = key.replace("_", " ").replace("__", " ").replace("-", " ").lower()
        if all(word in norm_key for word in query.split() if len(word) > 2):
            best_match = key
            break
        # Fuzzy match: check if any main word in key is in query
        for part in norm_key.split():
            if part in query:
                best_match = key
                break
        if best_match:
            break
    if not best_match:
        return JSONResponse(content={"response": "Sorry, I couldn't find info for your query."})
    info = DISEASE_INFO[best_match]
    # Build response based on keywords
    response = ""
    if "fertilizer" in query:
        response += f"Fertilizer: {info.get('fertilizer', 'N/A')}\n"
    if "treatment" in query:
        response += f"Treatment: {info.get('treatment', 'N/A')}\n"
    if "organic" in query:
        response += f"Organic Treatment: {info.get('organic_treatment', 'N/A')}\n"
    if "chemical" in query:
        response += f"Chemical Treatment: {info.get('chemical_treatment', 'N/A')}\n"
    if "tips" in query:
        response += f"Tips: {info.get('tips', 'N/A')}\n"
    # If no keyword, give summary
    if not response:
        response = f"Symptoms: {info.get('symptoms', 'N/A')}\nTreatment: {info.get('treatment', 'N/A')}\nFertilizer: {info.get('fertilizer', 'N/A')}\nTips: {info.get('tips', 'N/A')}"
    return JSONResponse(content={"response": response.strip()})