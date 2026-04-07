// ⚠️  Replace these values with your own Firebase project credentials.
// Go to: https://console.firebase.google.com → Your Project → Project Settings → Web App

const firebaseConfig = {
  apiKey:            "AIzaSyCtT7fKQ2Esqp22FmuroseHF440Qq0YYXk",
  authDomain:        "usercentric-deepfake-image-de.firebaseapp.com",
  projectId:         "usercentric-deepfake-image-de",
  storageBucket:     "usercentric-deepfake-image-de.firebasestorage.app",
  messagingSenderId: "947926476817",
  appId:             "1:947926476817:web:8316a8a8721b6ff88ca9b0",
  measurementId:     "G-59TB4T6XSP"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
