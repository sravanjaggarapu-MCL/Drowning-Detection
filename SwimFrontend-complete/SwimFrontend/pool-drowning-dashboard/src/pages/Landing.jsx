/*
============================================================
Landing.jsx
============================================================

DESCRIPTION:
This file creates the landing page for the PoolGuard
swimming pool safety application.

The landing page is the first screen users see before
they reach the Login page.

MAIN SECTIONS:
1. Navigation bar
2. Hero section
3. Pool monitoring image
4. Features section
5. Call-to-action section
6. Team footer

The "Get Started" button takes the user to the Login page.
============================================================
*/

// Create the Landing component.
function Landing({ onGetStarted }) {

  // Return the complete landing page.
  return (

    // Main landing page container.
    <div className="landing-page">

      {/* --------------------------------------------------
          LANDING NAVBAR
          -------------------------------------------------- */}

      <nav className="landing-navbar">

        {/* Project branding. */}
        <div className="landing-brand">

          {/* Pool icon. */}
          <div className="landing-brand-icon">
            🏊
          </div>

          {/* Project name and subtitle. */}
          <div>
            <h2>PoolGuard</h2>
            <span>Smart Pool Safety</span>
          </div>

        </div>

        {/* Login button. */}
        <button
          className="landing-login-button"
          onClick={onGetStarted}
        >
          Login
        </button>

      </nav>


      {/* --------------------------------------------------
          HERO SECTION
          -------------------------------------------------- */}

      <section className="hero-section">

        {/* Left side of hero section. */}
        <div className="hero-content">

          {/* Small project label. */}
          <div className="hero-label">
            🛡️ AI-POWERED POOL SAFETY
          </div>

          {/* Main heading. */}
          <h1>
            Smarter Monitoring.
            <br />
            <span>Safer Swimming.</span>
          </h1>

          {/* Project description. */}
          <p>
            PoolGuard uses intelligent computer vision to monitor
            swimming pools and help detect dangerous situations
            in real time.
          </p>

          {/* Hero buttons. */}
          <div className="hero-buttons">

            {/* Get Started button. */}
            <button
              className="primary-button"
              onClick={onGetStarted}
            >
              Get Started →
            </button>

            {/* Learn more button. */}
            <a
              href="#features"
              className="secondary-button"
            >
              Learn More
            </a>

          </div>

          {/* Small safety message. */}
          <div className="hero-status">

            {/* Green status indicator. */}
            <span className="hero-status-dot"></span>

            {/* Status text. */}
            AI monitoring designed for safer pools

          </div>

        </div>


        {/* Right side of hero section. */}
        <div className="hero-visual">

          {/* Image container. */}
          <div className="hero-image-card">

            {/* Pool image. */}
            <img
              src="/240_F_89237466_uaRH2ZtcXioGsO2HijRYO7Go2QW06SBr.jpg"
              alt="Swimming pool monitoring"
            />

            {/* Image overlay. */}
            <div className="hero-image-overlay">

              {/* Live indicator. */}
              <div className="hero-live">
                <span></span>
                LIVE MONITORING
              </div>

              {/* Camera label. */}
              <div className="hero-camera">
                CAMERA 01
              </div>

            </div>

          </div>

          {/* Floating AI card. */}
          <div className="floating-ai-card">

            {/* AI icon. */}
            <div className="floating-icon">
              🤖
            </div>

            {/* AI information. */}
            <div>
              <strong>AI Detection</strong>
              <p>Monitoring Active</p>
            </div>

          </div>

        </div>

      </section>


      {/* --------------------------------------------------
          FEATURES SECTION
          -------------------------------------------------- */}

      <section
        className="features-section"
        id="features"
      >

        {/* Section heading. */}
        <div className="features-heading">

          <span>WHY POOLGUARD?</span>

          <h2>
            Safety that watches
            <br />
            when you can't.
          </h2>

        </div>


        {/* Features container. */}
        <div className="features-grid">

          {/* Feature 1. */}
          <div className="feature-card">

            <div className="feature-icon">
              📹
            </div>

            <h3>Live Monitoring</h3>

            <p>
              Keep an eye on your swimming pool through
              continuous camera monitoring.
            </p>

          </div>


          {/* Feature 2. */}
          <div className="feature-card">

            <div className="feature-icon">
              🤖
            </div>

            <h3>AI Detection</h3>

            <p>
              Intelligent computer vision helps identify
              unusual or dangerous activity.
            </p>

          </div>


          {/* Feature 3. */}
          <div className="feature-card">

            <div className="feature-icon alert-feature">
              🚨
            </div>

            <h3>Instant Alerts</h3>

            <p>
              Receive important safety alerts when a
              potential emergency is detected.
            </p>

          </div>

        </div>

      </section>


      {/* --------------------------------------------------
          CALL TO ACTION
          -------------------------------------------------- */}

      <section className="cta-section">

        {/* CTA heading. */}
        <h2>
          Ready to make your pool safer?
        </h2>

        {/* CTA description. */}
        <p>
          Access your PoolGuard monitoring dashboard
          and start monitoring your pool.
        </p>

        {/* CTA button. */}
        <button
          className="primary-button cta-button"
          onClick={onGetStarted}
        >
          Enter PoolGuard →
        </button>

      </section>


      {/* --------------------------------------------------
          FOOTER
          -------------------------------------------------- */}

      <footer className="landing-footer">

        {/* Footer project name. */}
        <div>
          <strong>🏊 PoolGuard</strong>
          <span>Smart Pool Safety</span>
        </div>

        {/* Team names. */}
        <div className="team-names">
          Vaishnavi • Sravan • Anvith • Akshay
        </div>

        {/* Copyright. */}
        <div>
          © 2026 PoolGuard
        </div>

      </footer>

    </div>
  );
}

// Export the Landing component.
export default Landing;