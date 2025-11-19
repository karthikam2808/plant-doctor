import io
import json
import os
import re
import yaml
from PIL import Image
import qrcode
import matplotlib.pyplot as plt
from fpdf import FPDF
from fastapi.responses import StreamingResponse

def remove_special_chars(text):
    return re.sub(r'[^\x00-\x7F]+', ' ', text)

def generate_pdf_report(class_name, image_bytes, dt, confidence=0.0):
    # Load disease info
    info_path = os.path.join("report", "disease_info.json")
    with open(info_path, "r", encoding="utf-8") as f:
        disease_info = json.load(f)
    info = disease_info.get(class_name, {})

    # Load model name with fallback
    config_path = "train/config.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        model_name = config.get("model_name", "Unknown")
    else:
        model_name = "EfficientNetV2-B3"

    pdf = FPDF()
    pdf.add_page()

    # Outer border for page 1
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.8)
    pdf.rect(5, 5, 200, 287)

    # Header
    pdf.set_fill_color(180, 238, 180)
    pdf.rect(6, 6, 198, 18, 'F')
    pdf.set_xy(6, 10)
    pdf.set_font("Arial", 'B', 16)
    pdf.set_text_color(0, 60, 0)
    pdf.cell(198, 10, "Plant Disease Detection Report", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.set_text_color(0, 100, 0)
    pdf.set_xy(6, 18)
    pdf.cell(198, 8, f"Confidence Score: {confidence:.2f}%", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)

    # QR Code
    qr_url = f"https://www.google.com/search?q={remove_special_chars(class_name)}+plant+disease"
    qr = qrcode.make(qr_url)
    qr_path = "temp_qr.png"
    qr.save(qr_path)
    pdf.image(qr_path, x=12, y=26, w=40)
    os.remove(qr_path)

    # Uploaded image
    if image_bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_path = "temp_image.jpg"
            img.thumbnail((100, 100))
            img.save(img_path, "JPEG", quality=95)
            pdf.image(img_path, x=158, y=26, w=40)
            os.remove(img_path)
        except Exception as e:
            pdf.set_text_color(255, 0, 0)
            pdf.set_font("Arial", size=10)
            pdf.cell(0, 10, f"Image error: {e}", ln=True)
            pdf.set_text_color(0, 0, 0)

    # Details
    pdf.set_y(72)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, f"Class: {remove_special_chars(class_name)}", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Confidence Score: {confidence:.2f}%", ln=True)
    pdf.cell(0, 8, f"Date: {remove_special_chars(dt)}", ln=True)
    pdf.cell(0, 8, f"Model: {remove_special_chars(model_name)}", ln=True)
    pdf.ln(3)

    # Summary
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(0, 8, "Summary", ln=True, fill=True)
    pdf.set_font("Arial", '', 12)
    summary_keys = ["symptoms", "causes", "treatment", "fertilizer", "water", "soil", "humidity", "temperature"]
    for key in summary_keys:
        if key in info:
            value = remove_special_chars(info[key])[:80]
            pdf.cell(45, 7, f"{key.capitalize()}:", border=1)
            pdf.cell(0, 7, value, border=1, ln=True)
    pdf.ln(2)

    # Overview
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(220, 255, 220)
    pdf.cell(0, 8, "Disease Overview", ln=True, fill=True)
    pdf.set_font("Arial", '', 12)
    for key in ["symptoms", "causes", "treatment"]:
        if key in info:
            pdf.multi_cell(0, 7, f"{key.capitalize()}: {remove_special_chars(info[key])}")
    pdf.ln(1)

    # Growing Conditions
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(220, 255, 220)
    pdf.cell(0, 8, "Growing Conditions", ln=True, fill=True)
    pdf.set_font("Arial", '', 12)
    for key in ["fertilizer", "water", "soil", "humidity", "temperature"]:
        if key in info:
            pdf.multi_cell(0, 7, f"{key.capitalize()}: {remove_special_chars(info[key])}")
    pdf.ln(1)

    # Tips
    if "tips" in info:
        pdf.set_font("Arial", 'B', 14)
        pdf.set_fill_color(220, 255, 220)
        pdf.cell(0, 8, "Tips", ln=True, fill=True)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, 7, remove_special_chars(info["tips"]))

    # Chart
    chart_labels = ['Nitrogen', 'Water', 'Humidity', 'Temp']
    chart_values = [80, 60, 75, 65]  # Example
    colors = ['#2E8B57', '#1E90FF', '#FFA500', '#8A2BE2']
    plt.figure(figsize=(4, 2))
    plt.bar(chart_labels, chart_values, color=colors)
    plt.title('Environmental Factors Overview')
    plt.tight_layout()
    chart_path = "temp_chart.png"
    plt.savefig(chart_path)
    plt.close()

    pdf.add_page()
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.8)
    pdf.rect(5, 5, 200, 287)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Environmental Insight Chart", ln=True)
    pdf.image(chart_path, x=40, w=130)
    os.remove(chart_path)
    pdf.set_font("Arial", '', 12)
    pdf.multi_cell(0, 7, "This chart visually summarizes the general environmental requirements for healthy plant growth such as nitrogen, water, humidity, and temperature. These conditions play a critical role in either promoting or preventing plant diseases.")

    # Footer
    pdf.set_y(-15)
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Generated by Plant Disease Detector", 0, 0, 'C')

    # Output
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=plant_report.pdf"
    })
