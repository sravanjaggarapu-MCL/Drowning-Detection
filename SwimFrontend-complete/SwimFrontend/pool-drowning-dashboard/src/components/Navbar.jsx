// Navbar.jsx
// ------------------------------------------------------------
// DESCRIPTION:
// This component creates the top navigation bar.
// It displays the project name and buttons for:
// - Dashboard
// - Events
// ------------------------------------------------------------

// Create the Navbar component.
function Navbar({ currentPage, onNavigate }) {

  // Return the navigation bar.
  return (

    // Main navigation container.
    <nav className="navbar">

      {/* Project logo and name. */}
      <div className="brand">

        {/* Simple pool icon. */}
        <div className="brand-icon">🏊</div>

        {/* Project name. */}
        <div>
          <h2>PoolGuard</h2>
          <span>Smart Pool Safety</span>
        </div>

      </div>

      {/* Navigation buttons. */}
      <div className="nav-links">

        {/* Dashboard button. */}
        <button
          className={currentPage === "dashboard" ? "nav-button active" : "nav-button"}
          onClick={() => onNavigate("dashboard")}
        >
          Dashboard
        </button>

        {/* Events button. */}
        <button
          className={currentPage === "events" ? "nav-button active" : "nav-button"}
          onClick={() => onNavigate("events")}
        >
          Events
        </button>

      </div>

      {/* System indicator. */}
      <div className="system-online">

        {/* Green status dot. */}
        <span className="online-dot"></span>

        {/* Status text. */}
        System Online

      </div>

    </nav>
  );
}

// Export the Navbar component.
export default Navbar;