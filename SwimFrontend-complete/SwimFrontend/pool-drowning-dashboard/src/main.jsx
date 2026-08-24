// main.jsx
// ------------------------------------------------------------
// DESCRIPTION:
// This file starts the React application.
// It connects the App component to the HTML element
// with the id "root" inside index.html.
// ------------------------------------------------------------

// Import React.
import React from "react";

// Import ReactDOM for rendering React components.
import ReactDOM from "react-dom/client";

// Import the main App component.
import App from "./App";

// Import the global CSS file.
import "./index.css";

// Find the HTML element with id="root".
const rootElement = document.getElementById("root");

// Create a React root and render the application.
ReactDOM.createRoot(rootElement).render(

  // StrictMode helps identify potential React problems.
  <React.StrictMode>

    {/* Display the main application. */}
    <App />

  </React.StrictMode>
);