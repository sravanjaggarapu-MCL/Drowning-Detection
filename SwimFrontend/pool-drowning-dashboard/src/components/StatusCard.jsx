// StatusCard.jsx
// ------------------------------------------------------------
// DESCRIPTION:
// This reusable component displays important pool monitoring
// information such as:
// - People detected
// - Active alerts
// - Camera status
// ------------------------------------------------------------

// Create the StatusCard component.
function StatusCard({ icon, title, value, description, type }) {

  // Return the status card.
  return (

    // Main status card.
    <div className={`status-card ${type || ""}`}>

      {/* Icon section. */}
      <div className="status-icon">

        {/* Display the icon passed to the component. */}
        {icon}

      </div>

      {/* Card information. */}
      <div className="status-information">

        {/* Card title. */}
        <p>{title}</p>

        {/* Main value. */}
        <h3>{value}</h3>

        {/* Small description. */}
        <span>{description}</span>

      </div>

    </div>
  );
}

// Export the StatusCard component.
export default StatusCard;