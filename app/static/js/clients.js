/**
 * Clients - Connected VPN clients data management
 * Description: Loading, processing and displaying client information
 */

// === MAIN CLIENTS TABLE ===

/**
 * Loads connected clients data from API and updates the table
 * Also updates traffic charts and calculates data transfer speed
 *
 * @param {boolean} [forceInitChart=false] - Force chart initialization
 * @async
 * @returns {Promise<void>}
 */
function fetchData(forceInitChart = false) {
  // Request clients data via jQuery AJAX
  $.getJSON("/api/clients", function(data) {
    // Current time for speed calculation
    const now = Date.now();
    const timeLabel = new Date().toLocaleTimeString();

    // Variables for total traffic statistics
    let total_received = 0;
    let total_sent = 0;

    // Extract clients list from response
    const clients = data.clients || [];
    let users = clients.map(c => c.common_name);

    // === CHART INITIALIZATION ===
    // Check if we need to create or recreate the chart
    const needsChartInit = forceInitChart || !chart || chartData.datasets.length !== users.length * 2;

    if (needsChartInit) {
      // If canvas is not ready (modal not opened) - postpone initialization
      if (!chart && !chartCanvas) {
        // Chart will be created when modal opens
      } else {
        // Initialize chart with current client list
        initializeChart(users, currentChartMode, currentSelectedClient);
      }
    }

    // === UPDATE TIME LABELS ON CHART ===
    if (chartData.labels) {
      chartData.labels.push(timeLabel);

      // Limit number of labels (show last 20 points)
      if (chartData.labels.length > 20) {
        chartData.labels.shift();
      }
    }

    // Create dataset map for quick access
    const datasetMap = chartData.datasets ?
      Object.fromEntries(chartData.datasets.map(ds => [ds.label, ds.data])) : {};

    // === PROCESS EACH CLIENT'S DATA ===
    const rows = clients.map(client => {
      // Sum total traffic
      total_received += client.bytes_received;
      total_sent += client.bytes_sent;

      // === CALCULATE DATA TRANSFER SPEED ===
      let speed_rx = 0;  // Receive speed (MB/s)
      let speed_tx = 0;  // Transmit speed (MB/s)

      // Get previous values from cache
      const last = lastStats[client.common_name];

      if (last) {
        // Calculate time between measurements (in seconds)
        const dt = (now - last.timestamp) / 1000;

        // Calculate speed: (new value - old value) / time / 1024 / 1024 = MB/s
        speed_rx = (client.bytes_received - last.rx) / dt / 1024 / 1024;
        speed_tx = (client.bytes_sent - last.tx) / dt / 1024 / 1024;
      }

      // Save current values to cache for next calculation
      lastStats[client.common_name] = {
        rx: client.bytes_received,
        tx: client.bytes_sent,
        timestamp: now
      };

      // === UPDATE CHART DATA ===
      updateChartData(timeLabel, datasetMap, client.common_name, speed_rx, speed_tx);

      // === PROCESS IP ADDRESSES ===
      // Priority given to separate ipv4/ipv6 fields, fallback to vpn_ip
      const ipv4Candidate = client.vpn_ipv4 ?? null;
      const ipv6Candidate = client.vpn_ipv6 ?? null;

      let vpnIPv4 = ipv4Candidate;
      let vpnIPv6 = ipv6Candidate;

      // If no separate fields, try to determine type from vpn_ip
      if (vpnIPv4 == null && vpnIPv6 == null && client.vpn_ip) {
        if (client.vpn_ip.includes(':')) {
          vpnIPv6 = client.vpn_ip;  // Contains : → IPv6
        } else {
          vpnIPv4 = client.vpn_ip;  // No : → IPv4
        }
      }

      // Format for display
      const displayIPv4 = vpnIPv4 ?? "";
      const displayIPv6 = vpnIPv6 && vpnIPv6.trim() ? vpnIPv6 : "—";

      // === BUILD TABLE ROW HTML ===
      return `<tr>
        <td>${client.common_name}</td>
        <td>${displayIPv4}</td>
        <td>${displayIPv6}</td>
        <td>${client.real_ip}</td>
        <td>${client.port ?? ""}</td>
        <td>${client.connected_since}</td>
        <td>${client.time_online}</td>
        <td>${speed_rx.toFixed(2)} / ${speed_tx.toFixed(2)} MB/s</td>
        <td>${(client.bytes_received / 1024 / 1024).toFixed(2)} MB</td>
        <td>${(client.bytes_sent / 1024 / 1024).toFixed(2)} MB</td>
      </tr>`;
    }).join("");

    // === UPDATE DOM ===
    // Update clients table body
    $("#vpn-clients-body").html(rows);

    // Update totals in table footer
    $("#total-received").text((total_received / 1024 / 1024).toFixed(2) + " MB");
    $("#total-sent").text((total_sent / 1024 / 1024).toFixed(2) + " MB");

    // Update chart
    refreshChart();
  });
}

// === MODAL WINDOW: ALL CLIENTS LIST ===

/**
 * Displays status message in clients list modal
 *
 * @param {string} message - Message text
 * @param {Object} options - Display options
 * @param {boolean} [options.spinner=false] - Show loading spinner
 * @param {string} [options.tone='muted'] - Message tone (muted, success, danger)
 */
function showClientsStatus(message, { spinner = false, tone = 'muted' } = {}) {
  const listEl = document.getElementById('clientsList');
  if (!listEl) return;

  // Determine CSS class by tone
  const toneClass = tone === 'danger' ? 'text-danger' :
                    tone === 'success' ? 'text-success' :
                    'text-muted';

  // Escape HTML for security
  const safeMessage = escapeHtml(message);

  // Build content with or without spinner
  const content = spinner
    ? `<div class="d-flex align-items-center justify-content-center gap-2">
         <div class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></div>
         <span>${safeMessage}</span>
       </div>`
    : safeMessage;

  listEl.innerHTML = `<div class="text-center py-3 ${toneClass}">${content}</div>`;
}

/**
 * Loads clients summary from API
 * Called when opening clients list modal
 *
 * @async
 * @returns {Promise<void>}
 */
function fetchClientsSummary() {
  fetch('/api/clients/summary')
    .then(response => {
      if (!response.ok) {
        throw new Error(t('error_load'));
      }
      return response.json();
    })
    .then(data => {
      // Validate response
      if (!data || !Array.isArray(data.clients)) {
        throw new Error(t('error_invalid_response'));
      }

      // Save data to global variable
      clientsSummary = data.clients;

      // Display clients list
      renderClientsList(clientsSummary);
    })
    .catch(error => {
      console.error('Error loading clients summary:', error);
      showClientsStatus(t('error_load_clients_list'), { tone: 'danger' });
    });
}

/**
 * Renders clients list in modal with accordion interface
 *
 * @param {Array<Object>} clients - Array of client data objects
 */
function renderClientsList(clients) {
  const listEl = document.getElementById('clientsList');
  if (!listEl) return;

  // Check for empty list
  if (!Array.isArray(clients) || clients.length === 0) {
    showClientsStatus(t('no_clients_connected'));
    return;
  }

  // Sort: online clients alphabetically first, then offline alphabetically
  const sortedClients = [...clients].sort((a, b) => {
    // If status differs, online comes first
    if (a.is_online !== b.is_online) {
      return b.is_online - a.is_online;
    }
    // If status is the same, sort by name
    const nameA = (a.name || '').toLowerCase();
    const nameB = (b.name || '').toLowerCase();
    return nameA.localeCompare(nameB, 'ru');
  });

  // Build HTML for each client with accordion structure
  const itemsHtml = sortedClients.map((client, index) => {
    const name = client.name || t('unknown_client');
    const statusClass = client.is_online ? 'status-dot-online' : 'status-dot-offline';

    // Unique ID for collapse panel
    const collapseId = `collapse-client-${index}`;

    // Subtitle parts array
    const subtitleParts = [];

    // Sessions count
    if (typeof client.sessions === 'number' && client.sessions > 0) {
      const sessionWord = client.sessions === 1 ? t('session') : t('sessions');
      subtitleParts.push(`${client.sessions} ${sessionWord}`);
    }

    // Total connection time
    if (client.total_duration_human) {
      subtitleParts.push(`${t('total_time')}: ${escapeHtml(client.total_duration_human)}`);
    }

    // Traffic
    if (typeof client.total_rx_gb === 'number' && typeof client.total_tx_gb === 'number') {
      subtitleParts.push(`${t('traffic')}: ${formatGb(client.total_rx_gb)} / ${formatGb(client.total_tx_gb)}`);
    }

    // Last activity
    if (client.last_seen) {
      subtitleParts.push(`${t('last_seen_time')} ${escapeHtml(client.last_seen)}`);
    }

    const subtitle = subtitleParts.join(' · ');

    // Generate detailed information
    const detailsHtml = generateClientDetailsHTML(client);

    // Build list item HTML with collapse panel
    return `
      <div class="list-group-item p-0">
        <button type="button"
                class="btn btn-link text-start text-decoration-none w-100 p-3 d-flex flex-column align-items-start gap-1 collapsed client-accordion-btn"
                data-bs-toggle="collapse"
                data-bs-target="#${collapseId}"
                aria-expanded="false"
                aria-controls="${collapseId}"
                data-client-name="${escapeHtml(name)}">
          <div class="d-flex align-items-center">
            <span class="status-dot ${statusClass}"></span>
            <span class="client-name">${escapeHtml(name)}</span>
          </div>
          ${subtitle ? `<div class="small text-muted client-subtitle">${subtitle}</div>` : ''}
        </button>
        <div id="${collapseId}" class="collapse" data-bs-parent="#clientsList">
          <div class="px-3 pb-3 border-top client-details-content">
            ${detailsHtml}
          </div>
        </div>
      </div>
    `;
  }).join('');

  listEl.innerHTML = itemsHtml;
}

// === MODAL WINDOW: CLIENT DETAILS ===

/**
 * Generates HTML with detailed client information
 * Used for embedding in collapse panel
 *
 * @param {Object} client - Client data object
 * @returns {string} HTML string with client details
 */
function generateClientDetailsHTML(client) {
  // === BASIC INFORMATION ===
  const sessions = typeof client.sessions === 'number' ? client.sessions : 0;
  const totalTime = client.total_duration_human ? escapeHtml(client.total_duration_human) : '0:00:00';
  const lastSeen = client.last_seen ? escapeHtml(client.last_seen) : t('unknown');
  const totalRx = formatGb(client.total_rx_gb);
  const totalTx = formatGb(client.total_tx_gb);

  // === CURRENT SESSION (if client is online) ===
  let currentSessionHtml = '';

  if (client.current_session) {
    const session = client.current_session;
    const infoItems = [];

    // Connection time
    const connectedSince = session.connected_since ? escapeHtml(session.connected_since) : t('unknown');
    const timeOnline = session.time_online ? escapeHtml(session.time_online) : t('unknown');
    infoItems.push(`<li><strong>${t('connected_since_label')}</strong> ${connectedSince}</li>`);
    infoItems.push(`<li><strong>${t('time_online_label')}</strong> ${timeOnline}</li>`);

    // Client IP address
    if (session.ip) {
      const withPort = session.port ?
        `${escapeHtml(session.ip)}:${escapeHtml(session.port)}` :
        escapeHtml(session.ip);
      infoItems.push(`<li><strong>${t('client_ip_label')}</strong> ${withPort}</li>`);
    }

    // VPN IP addresses
    if (session.vpn_ipv4) {
      infoItems.push(`<li><strong>VPN IPv4:</strong> ${escapeHtml(session.vpn_ipv4)}</li>`);
    }
    if (session.vpn_ipv6) {
      infoItems.push(`<li><strong>VPN IPv6:</strong> ${escapeHtml(session.vpn_ipv6)}</li>`);
    }
    if (!session.vpn_ipv4 && !session.vpn_ipv6 && session.vpn_ip) {
      infoItems.push(`<li><strong>VPN IP:</strong> ${escapeHtml(session.vpn_ip)}</li>`);
    }

    // Current session traffic
    infoItems.push(`<li><strong>${t('received_label')}</strong> ${formatGb(session.bytes_received_gb)}</li>`);
    infoItems.push(`<li><strong>${t('sent_label')}</strong> ${formatGb(session.bytes_sent_gb)}</li>`);

    currentSessionHtml = `
      <div class="mt-3">
        <h6>${t('current_session')}</h6>
        <ul class="list-unstyled mb-0">
          ${infoItems.join('')}
        </ul>
      </div>
    `;
  }

  // === BUILD HTML ===
  return `
    <dl class="row mb-0">
      <dt class="col-sm-5">${t('sessions')}</dt>
      <dd class="col-sm-7">${sessions}</dd>

      <dt class="col-sm-5">${t('total_connection_time')}</dt>
      <dd class="col-sm-7">${totalTime}</dd>

      <dt class="col-sm-5">${t('data_received')}</dt>
      <dd class="col-sm-7">${totalRx}</dd>

      <dt class="col-sm-5">${t('data_sent')}</dt>
      <dd class="col-sm-7">${totalTx}</dd>

      <dt class="col-sm-5">${t('last_activity')}</dt>
      <dd class="col-sm-7">${lastSeen}</dd>
    </dl>
    ${currentSessionHtml}
  `;
}

/**
 * Renders detailed information for selected client
 * Shows modal with detailed statistics
 * (DEPRECATED FUNCTION - kept for compatibility)
 *
 * @param {Object} client - Client data object
 */
function renderClientDetails(client) {
  const titleEl = document.getElementById('clientDetailsTitle');
  const bodyEl = document.getElementById('clientDetailsBody');

  if (!titleEl || !bodyEl) return;

  // === MODAL TITLE ===
  const name = client.name || t('client_details');
  titleEl.textContent = name;

  const statusClass = client.is_online ? 'status-dot-online' : 'status-dot-offline';

  // === BUILD MODAL BODY HTML ===
  bodyEl.innerHTML = `
    <div class="d-flex align-items-center gap-2 mb-3">
      <span class="status-dot ${statusClass}"></span>
      <h5 class="mb-0">${escapeHtml(name)}</h5>
    </div>
    ${generateClientDetailsHTML(client)}
  `;

  // Show modal
  if (clientDetailsModalInstance) {
    clientDetailsModalInstance.show();
  }
}
