function showError(msg) {
  const el = document.getElementById("error-msg");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function hideError() {
  document.getElementById("error-msg").classList.add("hidden");
}

function isRecoverableFirebaseError(error) {
  return Boolean(
    error &&
    [
      "auth/configuration-not-found",
      "auth/api-key-not-valid.-please-pass-a-valid-api-key.",
      "auth/operation-not-allowed"
    ].includes(error.code)
  );
}

function enterDemoMode(message) {
  if (typeof window.enableDemoMode === "function") {
    window.enableDemoMode(message);
  }

  const googleButton = document.getElementById("google-btn");
  if (googleButton) {
    googleButton.textContent = "Continue in Demo Mode";
  }

  showError(message || "Firebase setup is incomplete. Demo mode is enabled.");
}

function syncDemoUi() {
  if (!window.isDemoAuth) {
    return;
  }

  const googleButton = document.getElementById("google-btn");
  if (googleButton) {
    googleButton.textContent = "Continue in Demo Mode";
  }

  if (window.demoModeMessage) {
    showError(window.demoModeMessage);
  }
}

function toggleForm() {
  document.getElementById("login-section").classList.toggle("hidden");
  document.getElementById("register-section").classList.toggle("hidden");
  hideError();
}

function loginUser() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  if (!email || !password) return showError("Please fill in all fields.");

  if (window.isDemoAuth) {
    try {
      window.demoAuth.login(email, password);
      window.location.href = "/dashboard";
    } catch (error) {
      showError(error.message);
    }
    return;
  }

  auth.signInWithEmailAndPassword(email, password)
    .then(() => window.location.href = "/dashboard")
    .catch(error => {
      if (isRecoverableFirebaseError(error)) {
        enterDemoMode("Firebase auth is not ready. You can continue in demo mode.");
        loginUser();
        return;
      }
      showError(error.message);
    });
}

function registerUser() {
  const name = document.getElementById("reg-name").value.trim();
  const email = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  if (!name || !email || !password) return showError("Please fill in all fields.");

  if (window.isDemoAuth) {
    try {
      window.demoAuth.register(name, email, password);
      window.location.href = "/dashboard";
    } catch (error) {
      showError(error.message);
    }
    return;
  }

  auth.createUserWithEmailAndPassword(email, password)
    .then(cred => cred.user.updateProfile({ displayName: name }))
    .then(() => window.location.href = "/dashboard")
    .catch(error => {
      if (isRecoverableFirebaseError(error)) {
        enterDemoMode("Firebase auth is not ready. You can continue in demo mode.");
        registerUser();
        return;
      }
      showError(error.message);
    });
}

function googleLogin() {
  if (window.isDemoAuth) {
    window.demoAuth.loginWithGoogle();
    window.location.href = "/dashboard";
    return;
  }

  const provider = new firebase.auth.GoogleAuthProvider();
  auth.signInWithPopup(provider)
    .then(() => window.location.href = "/dashboard")
    .catch(error => {
      if (isRecoverableFirebaseError(error)) {
        enterDemoMode("Google sign-in is not ready in Firebase. Demo mode is enabled.");
        googleLogin();
        return;
      }
      showError(error.message);
    });
}

syncDemoUi();

if (window.isDemoAuth) {
  if (window.demoAuth.getCurrentUser()) {
    window.location.href = "/dashboard";
  }
} else {
  auth.onAuthStateChanged(user => {
    if (user) window.location.href = "/dashboard";
  });
}
