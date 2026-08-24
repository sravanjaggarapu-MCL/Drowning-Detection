// Login.jsx
// ------------------------------------------------------------
// DESCRIPTION:
// This component creates a simple login screen for the
// PoolGuard monitoring dashboard.
// This is only a frontend login for now.
// Real authentication can later be connected to FastAPI.
// ------------------------------------------------------------

// Import React hooks.
import { useState } from "react";

// Create the Login component.
function Login({ onLogin }) {

  // Store the username.
  const [username, setUsername] = useState("");

  // Store the password.
  const [password, setPassword] = useState("");

  // Create the login function.
  const handleSubmit = (event) => {

    // Prevent browser page refresh.
    event.preventDefault();

    // Continue to dashboard.
    onLogin();
  };

  // Return the login screen.
  return (

    // Full login page.
    <div className="login-page">

      {/* Login card. */}
      <div className="login-card">

        {/* Project icon. */}
        <div className="login-icon">
          🏊
        </div>

        {/* Project name. */}
        <h1>PoolGuard</h1>

        {/* Login description. */}
        <p>
          Sign in to monitor your swimming pool.
        </p>

        {/* Login form. */}
        <form onSubmit={handleSubmit}>

          {/* Username input. */}
          <label>
            Username
          </label>

          <input
            type="text"
            placeholder="Enter username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />

          {/* Password label. */}
          <label>
            Password
          </label>

          {/* Password input. */}
          <input
            type="password"
            placeholder="Enter password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />

          {/* Login button. */}
          <button type="submit" className="login-button">
            Login
          </button>

        </form>

      </div>

    </div>
  );
}

// Export the Login component.
export default Login;