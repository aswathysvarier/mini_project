function showError(msg) {
  const el = document.getElementById("error-msg");
  el.textContent = msg;
  el.classList.remove("hidden");
}

function toggleForm() {
  document.getElementById("login-section").classList.toggle("hidden");
  document.getElementById("register-section").classList.toggle("hidden");
  document.getElementById("error-msg").classList.add("hidden");
}

function loginUser() {
  const email    = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  if (!email || !password) return showError("Please fill in all fields.");
  auth.signInWithEmailAndPassword(email, password)
    .then(() => window.location.href = "/dashboard")
    .catch(err => showError(err.message));
}

function registerUser() {
  const name     = document.getElementById("reg-name").value.trim();
  const email    = document.getElementById("reg-email").value.trim();
  const password = document.getElementById("reg-password").value;
  if (!name || !email || !password) return showError("Please fill in all fields.");
  auth.createUserWithEmailAndPassword(email, password)
    .then(cred => cred.user.updateProfile({ displayName: name }))
    .then(() => window.location.href = "/dashboard")
    .catch(err => showError(err.message));
}

function googleLogin() {
  const provider = new firebase.auth.GoogleAuthProvider();
  auth.signInWithPopup(provider)
    .then(() => window.location.href = "/dashboard")
    .catch(err => showError(err.message));
}

// Redirect if already logged in
auth.onAuthStateChanged(user => {
  if (user) window.location.href = "/dashboard";
});
