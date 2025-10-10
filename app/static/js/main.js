/**
 * Main application module - Initialization and coordination
 * Description: Application entry point, event handler setup and periodic data updates
 */

// === APPLICATION INITIALIZATION ===

/**
 * Main initialization function
 * Executed after DOM is loaded
 */
document.addEventListener("DOMContentLoaded", function () {

  // Track keyboard navigation to show focus styling only when needed
  const body = document.body;
  if (body) {
    const navigationKeys = new Set([
      "Tab",
      "ArrowUp",
      "ArrowDown",
      "ArrowLeft",
      "ArrowRight",
      "Home",
      "End",
      "PageUp",
      "PageDown"
    ]);

    function disableKeyboardFocus() {
      body.classList.remove("user-is-tabbing");
      window.removeEventListener("mousedown", disableKeyboardFocus);
      window.removeEventListener("touchstart", disableKeyboardFocus);
      window.addEventListener("keydown", enableKeyboardFocus, { once: true });
    }

    function enableKeyboardFocus(event) {
      if (!navigationKeys.has(event.key)) {
        return;
      }

      body.classList.add("user-is-tabbing");
      window.removeEventListener("keydown", enableKeyboardFocus);
      window.addEventListener("mousedown", disableKeyboardFocus, { once: true });
      window.addEventListener("touchstart", disableKeyboardFocus, { once: true });
    }

    window.addEventListener("keydown", enableKeyboardFocus, { once: true });
  }

  // === PERIODIC DATA UPDATES ===

  /**
   * Updates server and clients data
   * Called on initialization and every second
   */
  const refreshAll = () => {
    fetchData();           // Update client data (from clients.js)
    fetchServerStatus();   // Update server status (from server.js)
  };

  // Initial data load
  refreshAll();

  // Automatic update every 10 seconds
  setInterval(refreshAll, 10000);

  // === BUTTON HANDLERS SETUP ===

  // --- Theme toggle button ---
  document.getElementById("themeToggle").addEventListener("click", toggleTheme);

  // --- "Charts" button - Open charts modal ---
  document.getElementById("chartsBtn").addEventListener("click", () => {
    const chartsModalEl = document.getElementById('chartsModal');
    const chartsModal = new bootstrap.Modal(chartsModalEl);
    chartsModal.show();
  });

  // Charts modal show event handler
  // Initialize/update chart when opening
  let chartModeHandlerInitialized = false;

  document.getElementById('chartsModal').addEventListener('shown.bs.modal', () => {
    chartCanvas = document.getElementById('trafficChartModal');

    // Initialize chart mode change handlers (only once)
    if (!chartModeHandlerInitialized) {
      handleChartModeChange();
      chartModeHandlerInitialized = true;
    }

    if (!chart) {
      // Chart will be initialized on first fetchData()
      // Force data request to ensure chart creation
      fetchData(true);
    } else {
      // Update chart size after modal opening
      chart.resize();
      chart.update();
    }
  });

  // --- "Map View" button - Open map modal ---
  document.getElementById("mapBtn").addEventListener("click", () => {
    const mapModalEl = document.getElementById('mapModal');
    const mapModal = new bootstrap.Modal(mapModalEl);
    mapModal.show();
  });

  // Map modal show event handler
  // Initialize map and load markers when opening
  document.getElementById('mapModal').addEventListener('shown.bs.modal', () => {
    if (!mapInitialized) {
      // Initial map initialization
      mapInstance = L.map('mapModalMap').setView([20, 0], 2);

      // Add OpenStreetMap tile layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data © OpenStreetMap contributors'
      }).addTo(mapInstance);

      mapInitialized = true;
    } else {
      // Update map size after modal opening
      mapInstance.invalidateSize();
    }

    // Load client and server markers
    loadClientAndServerMarkers();
  });

  // === HISTORY MODAL SETUP ===

  const historyModalEl = document.getElementById('historyModal');
  const historyModal = new bootstrap.Modal(historyModalEl);

  // History filter controls
  const historyControls = [
    document.getElementById('filterDate'),
    document.getElementById('filterUser'),
    document.getElementById('filterCity'),
    document.getElementById('resetFilters'),
    document.getElementById('viewOnMap')
  ];

  /**
   * Enables or disables filter controls
   * @param {boolean} disabled - true to disable, false to enable
   */
  const setHistoryControlsDisabled = (disabled) => {
    historyControls.forEach(ctrl => {
      if (ctrl) ctrl.disabled = disabled;
    });
  };

  // --- "Connection history" button - Open history modal ---
  document.getElementById("historyBtn").addEventListener("click", () => {
    // Reset data
    fullHistoryData = [];
    window.fullHistoryData = fullHistoryData;
    document.getElementById("userList").innerHTML = "";
    document.getElementById("cityList").innerHTML = "";

    // Show loading indicator
    showHistoryStatus("Loading history...", { spinner: true });
    setHistoryControlsDisabled(true);

    // Show modal
    historyModal.show();

    // Load history data from API
    $.getJSON("/api/history")
      .done(entries => {
        // Validate response
        if (!Array.isArray(entries)) {
          const errorMessage = entries && entries.error ? entries.error : "Failed to load history";
          showHistoryStatus(errorMessage, { tone: 'danger' });
          return;
        }

        // Filter entries with valid traffic data
        fullHistoryData = entries.filter(e => e.rx !== null && e.tx !== null);
        window.fullHistoryData = fullHistoryData;

        // Extract unique client names for autocomplete
        const names = [...new Set(fullHistoryData.map(e => e.name))];
        document.getElementById("userList").innerHTML = names.map(n => `<option value="${n}">`).join("");

        // Extract unique cities for autocomplete
        const cities = [...new Set(fullHistoryData.map(e => e.location?.city).filter(c => c))];
        document.getElementById("cityList").innerHTML = cities.map(c => `<option value="${c}">`).join("");

        // Set current date in filter by default
        document.getElementById("filterDate").value = new Date().toISOString().split('T')[0];

        // Apply filters and display table
        applyFilters();
      })
      .fail(() => {
        showHistoryStatus("Failed to load history", { tone: 'danger' });
      })
      .always(() => {
        // Enable controls after load completes
        setHistoryControlsDisabled(false);
      });
  });

  // === CLIENTS MODAL SETUP ===

  const clientsModalEl = document.getElementById('clientsModal');
  if (clientsModalEl) {
    clientsModalInstance = new bootstrap.Modal(clientsModalEl);
  }

  // Client details modal is no longer used (replaced with accordion)
  // const clientDetailsModalEl = document.getElementById('clientDetailsModal');
  // if (clientDetailsModalEl) {
  //   clientDetailsModalInstance = new bootstrap.Modal(clientDetailsModalEl);
  // }

  // --- "Clients" button - Open clients list modal ---
  const clientsBtn = document.getElementById('clientsBtn');
  if (clientsBtn) {
    clientsBtn.addEventListener('click', () => {
      showClientsStatus('Loading clients...', { spinner: true });

      if (clientsModalInstance) {
        clientsModalInstance.show();
      }

      // Load clients summary
      fetchClientsSummary();
    });
  }

  // --- Click handler for client list items ---
  // Bootstrap Collapse automatically handles clicks via data-bs-toggle="collapse"
  // Old handler for opening details modal removed

  // === HISTORY FILTERS SETUP ===

  // Date filter change handler
  document.getElementById("filterDate").addEventListener("input", () => {
    applyFilters();
    // Auto-update history map if it's open
    setTimeout(tryRefreshOpenHistoryMap, 120);
  });

  // User name filter change handler
  document.getElementById("filterUser").addEventListener("input", () => {
    applyFilters();
    // Auto-update history map if it's open
    setTimeout(tryRefreshOpenHistoryMap, 120);
  });

  // City filter change handler
  document.getElementById("filterCity").addEventListener("input", () => {
    applyFilters();
    // Auto-update history map if it's open
    setTimeout(tryRefreshOpenHistoryMap, 120);
  });

  // Reset filters button
  document.getElementById("resetFilters").addEventListener("click", () => {
    document.getElementById("filterDate").value = "";
    document.getElementById("filterUser").value = "";
    document.getElementById("filterCity").value = "";
    renderHistoryTable(window.fullHistoryData);

    // Auto-update history map if it's open
    setTimeout(tryRefreshOpenHistoryMap, 150);
  });

  // === "VIEW ON MAP" BUTTON IN HISTORY ===

  // Button already exists in HTML, attach handler
  const viewOnMapBtn = document.getElementById('viewOnMap');
  if (viewOnMapBtn) {
    viewOnMapBtn.addEventListener('click', buildHistoryMap);
  }

  // === EXPORT GLOBAL VARIABLES ===
  // For access from other modules (e.g., history.js uses window.fullHistoryData)
  window.fullHistoryData = fullHistoryData;
});
