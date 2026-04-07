# DeepShield — Deepfake Detection Web App

## Project Structure
```
deepfake_detector/
├── app.py                        # Flask backend (EfficientNet-B4 + PDF)
├── requirements.txt
├── efficientnet_b4_deepfake.pth  # ← Place your trained weights here
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
Place your trained EfficientNet-B4 weights at:
```
deepfake_detector/efficientnet_b4_deepfake.pth
```
The model expects a 2-class output (real=0, fake=1).
If no weights file is found, the app runs with untrained random weights.

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
- Flask preprocesses it → resizes to 380×380, normalizes with ImageNet stats
- EfficientNet-B4 outputs real/fake probabilities via softmax
- If FAKE → warning shown + PDF report button appears
- PDF report includes: verdict, probabilities, model info, India + global safety helplines
- Safety resources are always visible on the dashboard

## Model Input Specs (EfficientNet-B4)
- Input size : 380 × 380 px
- Normalization mean : [0.485, 0.456, 0.406]
- Normalization std  : [0.229, 0.224, 0.225]
- Output classes    : 2  (index 0 = Real, index 1 = Fake)
