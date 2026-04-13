# DeepShield — Deepfake Detection Web App

## Project Structure
```
deepfake_detector/
├── app.py                        # Flask backend (EfficientNet-B0 + PDF)
├── requirements.txt
├── efficientnet_b0_deepfake.pth  # ← Place your trained weights here
├── templates/
│   ├── index.html                # Login page (Firebase auth)
│   └── dashboard.html            # Main detection dashboard
└── static/
    ├── css/style.css
    └── js/
        ├── firebase-config.js    # ← Add your Firebase credentials here
        ├── auth.js
        └── dashboard.js
```

## Setup Steps

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Add your trained model weights
Place your trained EfficientNet-B0 weights at:
```
deepfake_detector/efficientnet_b0_deepfake.pth
```
The model expects a 2-class output (real=0, fake=1).
If no weights file is found, the app runs with untrained random weights.

### 2a. Train on your dataset
Expected dataset structure:
```text
dataset/
  real/
    image1.jpg
    image2.jpg
  fake/
    image1.jpg
    image2.jpg
```

Or, if you already have separate splits:
```text
dataset/
  train/
    real/
    fake/
  val/
    real/
    fake/
```

Train with an automatic validation split:
```bash
python train.py --data-dir dataset --epochs 5 --batch-size 8
```

Train with separate train/val folders:
```bash
python train.py --data-dir dataset/train --val-dir dataset/val --epochs 5 --batch-size 8
```

This will save `efficientnet_b0_deepfake.pth`, which the Flask app loads automatically.

### 3. Configure Firebase
1. Go to https://console.firebase.google.com
2. Create a project → Add a Web App
3. Enable Authentication → Sign-in methods → Email/Password + Google
4. Copy your config into `static/js/firebase-config.js`

### 4. Run the app
```bash
python app.py
```
Open http://localhost:5000

## How it works
- User logs in via Firebase (email/password or Google)
- Uploads an image on the dashboard
- Flask preprocesses it → resizes to 224×224, normalizes with ImageNet stats
- EfficientNet-B0 outputs real/fake probabilities via softmax
- If FAKE → warning shown + PDF report button appears
- PDF report includes: verdict, probabilities, model info, India + global safety helplines
- Safety resources are always visible on the dashboard

## Model Input Specs (EfficientNet-B0)
- Input size : 224 × 224 px
- Normalization mean : [0.485, 0.456, 0.406]
- Normalization std  : [0.229, 0.224, 0.225]
- Output classes    : 2  (index 0 = Real, index 1 = Fake)
