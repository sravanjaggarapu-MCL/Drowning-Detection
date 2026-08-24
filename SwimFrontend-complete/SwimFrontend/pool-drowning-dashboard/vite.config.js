// vite.config.js
// ------------------------------------------------------------
// DESCRIPTION:
// This file contains the Vite configuration.
// It enables React support in the PoolGuard project.
// ------------------------------------------------------------

// Import the React plugin for Vite.
import { defineConfig } from "vite";

// Import the Vite React plugin.
import react from "@vitejs/plugin-react";

// Export the Vite configuration.
export default defineConfig({

  // Enable React support.
  plugins: [react()],

});