from flask import Flask, request, jsonify, render_template, send_file
import torch
import torch.nn as nn
from torchvision import transforms
from efficientnet_pytorch import EfficientNet
from PIL import Image
import io
import base64
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from datetime import datetime

app = Flask(__name__)
os.environ.setdefault("TORCH_HOME", os.path.join(app.root_path, ".torch"))

# ── Model Setup ──────────────────────────────────────────────────────────────
MODEL_PATH = "efficientnet_b4_deepfake.pth"

class DeepfakeDetector(nn.Module):
    def __init__(self):
        super().__init__()
        self.model = EfficientNet.from_pretrained('efficientnet-b4')
        self.model._fc = nn.Linear(self.model._fc.in_features, 2)

    def forward(self, x):
        return self.model(x)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = DeepfakeDetector().to(device)

if os.path.exists(MODEL_PATH):
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    print("Loaded trained model weights.")
else:
    print("No weights found - using untrained model (replace with real weights).")

model.eval()

# ── Preprocessing ─────────────────────────────────────────────────────────────
transform = transforms.Compose([
    transforms.Resize((380, 380)),        # EfficientNet-B4 native input size
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],       # ImageNet mean
        std=[0.229, 0.224, 0.225]         # ImageNet std
    )
])

# ── Safety Resources ──────────────────────────────────────────────────────────
SAFETY_RESOURCES = {
    "India": [
        {"name": "National Cyber Crime Helpline", "phone": "1930",       "email": "cybercrime@gov.in",          "url": "https://cybercrime.gov.in"},
        {"name": "NCW (Women Helpline)",           "phone": "181",        "email": "ncw@nic.in",                 "url": "https://ncw.nic.in"},
        {"name": "Cyber Dost (MHA)",               "phone": "N/A",        "email": "cyberdost@mha.gov.in",       "url": "https://cyberdost.mha.gov.in"},
        {"name": "iCall (Mental Health)",          "phone": "9152987821", "email": "icall@tiss.edu",             "url": "https://icallhelpline.org"},
    ],
    "Global": [
        {"name": "StopNCII (Image Abuse)",         "phone": "N/A",        "email": "support@stopncii.org",       "url": "https://stopncii.org"},
        {"name": "NCMEC CyberTipline",             "phone": "1-800-843-5678","email": "cybertipline@ncmec.org",  "url": "https://www.missingkids.org"},
        {"name": "Internet Watch Foundation",      "phone": "N/A",        "email": "report@iwf.org.uk",          "url": "https://www.iwf.org.uk"},
        {"name": "Revenge Porn Helpline (UK)",     "phone": "0345 6000 459","email": "help@revengepornhelpline.org.uk","url": "https://revengepornhelpline.org.uk"},
    ]
}

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/predict", methods=["POST"])
def predict():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    img = Image.open(file.stream).convert("RGB")
    tensor = transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs  = torch.softmax(logits, dim=1)[0]
        fake_prob = round(float(probs[1]) * 100, 2)
        real_prob = round(float(probs[0]) * 100, 2)
        label = "FAKE" if fake_prob > 50 else "REAL"

    # Encode image for PDF embedding
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    return jsonify({
        "label":     label,
        "fake_prob": fake_prob,
        "real_prob": real_prob,
        "image_b64": img_b64
    })

@app.route("/generate_report", methods=["POST"])
def generate_report():
    data      = request.json
    label     = data.get("label", "FAKE")
    fake_prob = data.get("fake_prob", 0)
    real_prob = data.get("real_prob", 0)
    filename  = data.get("filename", "uploaded_image")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            rightMargin=0.75*inch, leftMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story  = []

    # Title
    title_style = ParagraphStyle("title", parent=styles["Title"],
                                 fontSize=20, textColor=colors.HexColor("#1a1a2e"),
                                 spaceAfter=6)
    story.append(Paragraph("DeepShield — Detection Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", styles["Normal"]))
    story.append(Spacer(1, 0.2*inch))

    # Verdict banner
    verdict_color = colors.HexColor("#e74c3c") if label == "FAKE" else colors.HexColor("#27ae60")
    verdict_data  = [[f"VERDICT: {label}  |  Fake: {fake_prob}%  |  Real: {real_prob}%"]]
    verdict_table = Table(verdict_data, colWidths=[6.5*inch])
    verdict_table.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), verdict_color),
        ("TEXTCOLOR",   (0,0), (-1,-1), colors.white),
        ("FONTSIZE",    (0,0), (-1,-1), 13),
        ("FONTNAME",    (0,0), (-1,-1), "Helvetica-Bold"),
        ("ALIGN",       (0,0), (-1,-1), "CENTER"),
        ("TOPPADDING",  (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0),(-1,-1), 10),
        ("ROUNDEDCORNERS", [4]),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 0.2*inch))

    # Analysis table
    story.append(Paragraph("Analysis Details", styles["Heading2"]))
    analysis_data = [
        ["File",         filename],
        ["Prediction",   label],
        ["Fake Probability",  f"{fake_prob}%"],
        ["Real Probability",  f"{real_prob}%"],
        ["Model",        "EfficientNet-B4"],
        ["Input Size",   "380 × 380 px"],
    ]
    tbl = Table(analysis_data, colWidths=[2*inch, 4.5*inch])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (0,-1), colors.HexColor("#f0f0f0")),
        ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#fafafa")]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 0.25*inch))

    # Safety resources
    if label == "FAKE":
        story.append(Paragraph("Safety & Support Resources", styles["Heading2"]))
        story.append(Paragraph("If this image is being used to harm you, please reach out immediately:", styles["Normal"]))
        story.append(Spacer(1, 0.1*inch))

        for region, resources in SAFETY_RESOURCES.items():
            story.append(Paragraph(region, styles["Heading3"]))
            res_data = [["Organisation", "Phone", "Email"]]
            for r in resources:
                res_data.append([r["name"], r["phone"], r["email"]])
            res_tbl = Table(res_data, colWidths=[2.2*inch, 1.3*inch, 3*inch])
            res_tbl.setStyle(TableStyle([
                ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
                ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",    (0,0), (-1,-1), 9),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f9f9f9")]),
                ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#dddddd")),
                ("TOPPADDING",  (0,0), (-1,-1), 5),
                ("BOTTOMPADDING",(0,0),(-1,-1), 5),
            ]))
            story.append(res_tbl)
            story.append(Spacer(1, 0.1*inch))

    # Footer note
    story.append(Spacer(1, 0.2*inch))
    footer_style = ParagraphStyle("footer", parent=styles["Normal"],
                                  fontSize=8, textColor=colors.grey)
    story.append(Paragraph(
        "This report is generated by DeepShield. AI predictions may not be 100% accurate. "
        "Always verify with human experts for legal or safety matters.", footer_style))

    doc.build(story)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name="deepshield_report.pdf")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
