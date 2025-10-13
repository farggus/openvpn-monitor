/**
 * Connection history - VPN sessions history management
 * Description: Loading, filtering and displaying connection history, as well as map visualization
 */

// === HISTORY MODAL ===

/**
 * Displays status message in history table
 *
 * @param {string} message - Message text
 * @param {Object} options - Display options
 * @param {boolean} [options.spinner=false] - Show loading spinner
 * @param {string} [options.tone='muted'] - Message tone (muted, danger)
 */
function showHistoryStatus(message, { spinner = false, tone = 'muted' } = {}) {
  // Determine CSS class based on tone
  const toneClass = tone === 'danger' ? 'text-danger' : 'text-muted';

  // Build content with or without spinner
  const content = spinner
    ? `<div class="d-flex align-items-center justify-content-center gap-2">
         <div class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></div>
         <span>${message}</span>
       </div>`
    : message;

  // Update history table tbody
  document.getElementById('history-body').innerHTML =
    `<tr><td colspan="11" class="text-center py-4 ${toneClass}">${content}</td></tr>`;
}

/**
 * Applies filters to history data and updates the table
 * Filters by date, client name, city, and optionally zero traffic
 */
function applyFilters() {
  // Get filter values
  const dateFilter = document.getElementById("filterDate").value;
  const userFilter = document.getElementById("filterUser").value.toLowerCase();
  const cityFilter = document.getElementById("filterCity").value.toLowerCase();
  const hideZeroTraffic = document.getElementById("hideZeroTraffic")?.checked || false;

  // Filter data
  const filtered = window.fullHistoryData.filter(entry => {
    // Date filter: if not set or timestamp starts with date
    const matchesDate = !dateFilter || entry.timestamp.startsWith(dateFilter);

    // Name filter: if not set or name contains search string
    const matchesUser = !userFilter || entry.name.toLowerCase().includes(userFilter);

    // City filter: if not set or city contains search string
    const matchesCity = !cityFilter || (entry.location?.city || "").toLowerCase().includes(cityFilter);

    // Traffic filter: if checkbox is checked, hide entries where BOTH rx AND tx are zero or null
    const matchesTraffic = !hideZeroTraffic ||
      !((entry.rx === null || entry.rx === 0) && (entry.tx === null || entry.tx === 0));

    return matchesDate && matchesUser && matchesCity && matchesTraffic;
  });

  // Display filtered data
  renderHistoryTable(filtered);
}

/**
 * Renders connection history table
 *
 * @param {Array<Object>} data - Array of history entries
 */
function renderHistoryTable(data) {
  // Check for empty result
  if (!data.length) {
    document.getElementById("history-body").innerHTML =
      `<tr><td colspan="11" class="text-center py-4 text-muted">No history entries</td></tr>`;
    return;
  }

  // Build HTML table rows
  const rows = data.map(entry => {
    // === PROCESS IP ADDRESSES ===
    // Support legacy vpn_ip field and new vpn_ipv4/vpn_ipv6 fields
    const legacyVpnIp = entry.vpn_ip ?? "";

    // Determine IPv4
    const vpnIpv4 = entry.vpn_ipv4 ||
                    (legacyVpnIp && legacyVpnIp.includes('.') ? legacyVpnIp : "");

    // Determine IPv6
    const rawIpv6 = entry.vpn_ipv6 ||
                    (legacyVpnIp && legacyVpnIp.includes(':') ? legacyVpnIp : "");
    const vpnIpv6 = rawIpv6 || "—";

    // Extract city from location
    const city = entry.location?.city ?? "—";

    // Build HTML row
    return `
      <tr>
        <td>${entry.timestamp}</td>
        <td>${entry.name}</td>
        <td>${vpnIpv4}</td>
        <td>${vpnIpv6}</td>
        <td>${entry.ip}</td>
        <td>${entry.port ?? ""}</td>
        <td>${city}</td>
        <td>${entry.session_end ?? ""}</td>
        <td>${entry.duration ?? ""}</td>
        <td>${entry.rx ?? ""}</td>
        <td>${entry.tx ?? ""}</td>
      </tr>
    `;
  }).join("");

  // Update table
  document.getElementById("history-body").innerHTML = rows;
}

// === HISTORY MAP ===

/**
 * Variables for history map functionality
 * (separate map for history modal)
 */
let historyMapInstance = null;
let historyMapInitialized = false;
let historyMapMarkers = [];

/**
 * Creates or updates map with markers from filtered history
 * Uses location data saved in history entries
 *
 * @async
 * @returns {Promise<void>}
 */
async function buildHistoryMap() {
  // Find history map modal
  const modalEl = document.getElementById('historyMapModal');
  if (!modalEl) {
    alert('Add #historyMapModal modal to HTML');
    return;
  }

  // === APPLY FILTERS TO HISTORY DATA ===
  // Get current filter values
  const dateFilter = document.getElementById("filterDate")?.value || '';
  const userFilter = document.getElementById("filterUser")?.value.toLowerCase() || '';
  const cityFilter = document.getElementById("filterCity")?.value.toLowerCase() || '';

  // Filter data (use window.fullHistoryData for IIFE access)
  const filtered = window.fullHistoryData.filter(entry =>
    (!dateFilter || entry.timestamp.startsWith(dateFilter)) &&
    (!userFilter || entry.name.toLowerCase().includes(userFilter)) &&
    (!cityFilter || (entry.location?.city || "").toLowerCase().includes(cityFilter))
  );

  // Check for empty result
  if (filtered.length === 0) {
    alert('No entries to display on map. Change filters.');
    return;
  }

  // === MAP INITIALIZATION (ONCE) ===
  if (!historyMapInitialized) {
    // Create Leaflet map instance
    historyMapInstance = L.map('historyMap').setView([20, 0], 2);

    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'Map data © OpenStreetMap contributors'
    }).addTo(historyMapInstance);

    // Modal show event handler
    // Fix map dimensions after opening animation
    modalEl.addEventListener('shown.bs.modal', () => {
      setTimeout(() => {
        historyMapInstance.invalidateSize();
        // Recalculate bounds after invalidateSize, if there are markers
        if (historyMapMarkers.length > 0) {
          const bounds = historyMapMarkers.map(m => m.getLatLng());
          historyMapInstance.fitBounds(bounds, { padding: [30, 30] });
        }
      }, 50);
    });

    historyMapInitialized = true;
  }

  // === CLEAR OLD MARKERS ===
  historyMapMarkers.forEach(marker => historyMapInstance.removeLayer(marker));
  historyMapMarkers = [];

  // === DEDUPLICATION BY IP ===
  // Collect unique IP addresses with their locations
  const ipLocationMap = new Map();

  for (const entry of filtered) {
    const ip = entry.ip;
    const location = entry.location;

    // Skip entries without IP or geolocation
    if (!ip || !location) continue;
    if (location.latitude == null || location.longitude == null) continue;

    // Save only the first entry for each IP
    if (!ipLocationMap.has(ip)) {
      ipLocationMap.set(ip, {
        ip: ip,
        latitude: location.latitude,
        longitude: location.longitude,
        city: location.city || '',
        country: location.country || ''
      });
    }
  }

  // Check for data availability to display
  if (ipLocationMap.size === 0) {
    alert('No entries with geolocation to display on map.');
    return;
  }

  // === ADD MARKERS TO MAP ===
  const bounds = [];

  /**
   * Helper function to add green marker
   * @param {number} lat - Latitude
   * @param {number} lon - Longitude
   * @param {string} label - Popup text
   */
  const addGreenMarker = (lat, lon, label) => {
    const marker = L.circleMarker([lat, lon], {
      radius: 8,              // Marker size
      color: '#2e7d32',       // Border color (dark green)
      weight: 2,              // Border thickness
      fillColor: '#43a047',   // Fill color (light green)
      fillOpacity: 0.9        // Fill opacity
    })
      .addTo(historyMapInstance)
      .bindPopup(label);

    historyMapMarkers.push(marker);
    bounds.push([lat, lon]);
  };

  // Add marker for each unique IP
  for (const [ip, loc] of ipLocationMap.entries()) {
    addGreenMarker(
      loc.latitude,
      loc.longitude,
      `${ip}<br>${loc.city} ${loc.country}`
    );
  }

  // === UPDATE MODAL TITLE ===
  const modalTitle = modalEl.querySelector('.modal-title');
  if (modalTitle) {
    modalTitle.textContent = `History — Map View (${ipLocationMap.size} unique locations)`;
  }

  // === AUTOMATIC MAP POSITIONING ===
  if (bounds.length) {
    historyMapInstance.fitBounds(bounds, { padding: [30, 30] });
  }

  // === SHOW MODAL ===
  // Show modal after adding all markers
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
}

/**
 * Checks if history map modal is open
 * @returns {boolean} true if window is open
 */
function historyMapIsOpen() {
  const el = document.getElementById('historyMapModal');
  return el && el.classList.contains('show');
}

/**
 * Updates history map if it's open
 * Called when filters change
 */
function tryRefreshOpenHistoryMap() {
  if (historyMapIsOpen()) {
    buildHistoryMap();
  }
}
