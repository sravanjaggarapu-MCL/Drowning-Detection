// Dashboard.jsx
// ------------------------------------------------------------
// DESCRIPTION:
// This is the main PoolGuard dashboard page.
// It combines:
// - Status cards
// - Live pool monitoring
// - Safety status
// - Recent events
// ------------------------------------------------------------

// Import the status card component.
import StatusCard from "../components/StatusCard";

// Import the camera component.
import CameraView from "../components/CameraView";

// Import the alert panel.
import AlertPanel from "../components/AlertPanel";

// Import the recent events component.
import RecentEvents from "../components/RecentEvents";

// Import the rescue system panel.
import RescuePanel from "../components/RescuePanel";

// Create the Dashboard component.
function Dashboard() {

  // Return the dashboard page.
  return (

    // Dashboard page container.
    <main className="page-container">

      {/* Dashboard welcome section. */}
      <section className="welcome-section">

        {/* Main heading. */}
        <div>
          <h1>Pool Safety Dashboard</h1>

          {/* Dashboard description. */}
          <p>
            Monitor your swimming pool and detect dangerous
            situations in real time.
          </p>
        </div>

        {/* Current monitoring status. */}
        <div className="monitoring-badge">

          {/* Green status dot. */}
          <span className="online-dot"></span>

          {/* Status text. */}
          Monitoring Active

        </div>

      </section>

      {/* Status cards section. */}
      <section className="status-grid">

        {/* People detected card. */}
        <StatusCard
          icon="👥"
          title="People Detected"
          value="2"
          description="Currently in pool"
        />

        {/* Active alerts card. */}
        <StatusCard
          icon="🚨"
          title="Active Alerts"
          value="0"
          description="No emergency detected"
        />

        {/* Camera status card. */}
        <StatusCard
          icon="📹"
          title="Camera Status"
          value="Online"
          description="Camera 01 connected"
          type="success"
        />

        {/* AI status card. */}
        <StatusCard
          icon="🤖"
          title="AI Detection"
          value="Active"
          description="YOLO monitoring enabled"
          type="success"
        />

      </section>

      {/* Main monitoring section. */}
      <section className="monitoring-grid">

        {/* Live camera view. */}
        <CameraView />

        {/* Safety alert panel. */}
        <AlertPanel />

      </section>

      {/* Rescue mechanism section.
          Shows the ESP32 net-rod status and the manual
          emergency trigger. */}
      <section className="rescue-section">

        {/* Rescue system panel. */}
        <RescuePanel />

      </section>

      {/* Recent events section. */}
      <section>

        {/* Recent events component. */}
        <RecentEvents />

      </section>

      {/* Simple footer. */}
      <footer className="dashboard-footer">

        {/* Project name. */}
        <span>PoolGuard © 2026</span>

        {/* Team members. */}
        <span>
          Vaishnavi • Sravan • Anvith • Akshay
        </span>

      </footer>

    </main>
  );
}

// Export the Dashboard component.
export default Dashboard;