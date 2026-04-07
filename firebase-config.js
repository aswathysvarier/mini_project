const firebaseConfig = {
  apiKey: "AIzaSyCtT7fKQ2Esqp22FmuroseHF440Qq0YYXk",
  authDomain: "usercentric-deepfake-image-de.firebaseapp.com",
  projectId: "usercentric-deepfake-image-de",
  storageBucket: "usercentric-deepfake-image-de.firebasestorage.app",
  messagingSenderId: "947926476817",
  appId: "1:947926476817:web:8316a8a8721b6ff88ca9b0",
  measurementId: "G-59TB4T6XSP"
};

const DEMO_USERS_KEY = "deepshield_demo_users";
const DEMO_CURRENT_USER_KEY = "deepshield_demo_current_user";

function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    return fallback;
  }
}

function writeJson(key, value) {
  localStorage.setItem(key, JSON.stringify(value));
}

function buildDemoAuthError(message, code) {
  const error = new Error(message);
  error.code = code;
  return error;
}

window.isDemoAuth = false;
window.demoModeMessage = "";

window.enableDemoMode = function(message) {
  window.isDemoAuth = true;
  window.demoModeMessage = message || "Firebase is unavailable. Demo mode is enabled.";
  window.auth = null;
};

window.demoAuth = {
  register(name, email, password) {
    const users = readJson(DEMO_USERS_KEY, []);
    const normalizedEmail = email.toLowerCase();
    if (users.some(user => user.email === normalizedEmail)) {
      throw buildDemoAuthError("An account with this email already exists.", "demo/email-already-in-use");
    }

    const user = { displayName: name, email: normalizedEmail, password };
    users.push(user);
    writeJson(DEMO_USERS_KEY, users);
    writeJson(DEMO_CURRENT_USER_KEY, { displayName: name, email: normalizedEmail });
    return { user: { displayName: name, email: normalizedEmail } };
  },

  login(email, password) {
    const users = readJson(DEMO_USERS_KEY, []);
    const normalizedEmail = email.toLowerCase();
    const user = users.find(item => item.email === normalizedEmail && item.password === password);

    if (!user) {
      throw buildDemoAuthError("Invalid email or password.", "demo/invalid-credentials");
    }

    const currentUser = { displayName: user.displayName, email: user.email };
    writeJson(DEMO_CURRENT_USER_KEY, currentUser);
    return currentUser;
  },

  loginWithGoogle() {
    const currentUser = {
      displayName: "Demo User",
      email: "demo.user@example.com"
    };
    writeJson(DEMO_CURRENT_USER_KEY, currentUser);
    return currentUser;
  },

  logout() {
    localStorage.removeItem(DEMO_CURRENT_USER_KEY);
  },

  getCurrentUser() {
    return readJson(DEMO_CURRENT_USER_KEY, null);
  }
};

try {
  if (!window.firebase) {
    throw new Error("Firebase SDK failed to load.");
  }

  if (!firebase.apps.length) {
    firebase.initializeApp(firebaseConfig);
  }

  window.auth = firebase.auth();
} catch (error) {
  console.warn("Falling back to demo mode:", error);
  window.enableDemoMode("Firebase setup is incomplete. Running in demo mode.");
}
