/*
============================================================
App.jsx
============================================================

DESCRIPTION:
This file controls navigation between the main pages
of the PoolGuard application.

PAGE FLOW:

Landing Page
     ↓
Login Page
     ↓
Dashboard

Users first see the landing page.
When they click "Get Started" or "Login", they move
to the Login page.
After login, they enter the Dashboard.
============================================================
*/

// Import React state.
import { useState } from "react";

// Import the landing page.
import Landing from "./pages/Landing";

// Import the login page.
import Login from "./pages/Login";

// Import the dashboard page.
import Dashboard from "./pages/Dashboard";

// Import the events page.
import Events from "./pages/Events";

// Import the navigation bar.
import Navbar from "./components/Navbar";


// Create the main App component.
function App() {

  // Store the current page.
  const [currentPage, setCurrentPage] = useState("landing");

  // Store login status.
  const [isLoggedIn, setIsLoggedIn] = useState(false);


  // Handle login.
  const handleLogin = () => {

    // Mark the user as logged in.
    setIsLoggedIn(true);

    // Open the dashboard.
    setCurrentPage("dashboard");
  };


  // Handle logout or page navigation.
  const handleNavigation = (page) => {

    // Change the current page.
    setCurrentPage(page);
  };


  // Show landing page first.
  if (currentPage === "landing") {

    return (
      <Landing
        onGetStarted={() => setCurrentPage("login")}
      />
    );
  }


  // Show login page.
  if (currentPage === "login") {

    return (
      <Login
        onLogin={handleLogin}
      />
    );
  }


  // Show dashboard and events after login.
  return (

    <div className="app">

      {/* Display navigation bar. */}
      <Navbar
        currentPage={currentPage}
        onNavigate={handleNavigation}
      />

      {/* Display dashboard. */}
      {currentPage === "dashboard" && <Dashboard />}

      {/* Display events page. */}
      {currentPage === "events" && <Events />}

    </div>
  );
}


// Export the App component.
export default App;