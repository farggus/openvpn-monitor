/**
 * Server - OpenVPN server status management
 * Description: Loads and displays server state information
 */

/**
 * Loads OpenVPN server status from API and updates the table
 * Called periodically to update information in real-time
 *
 * Server information includes:
 * - VPN operation mode (mode)
 * - Server status (status)
 * - Ping availability (pingable)
 * - Number of connected clients (clients)
 * - Total inbound/outbound traffic (total_rx/total_tx)
 * - Uptime (uptime)
 * - Local and public IP addresses
 *
 * @async
 * @returns {Promise<void>}
 */
function fetchServerStatus() {
  // Request to server status API
  fetch("/api/server-status")
    .then(response => response.json())  // Parse JSON response
    .then(data => {
      // Build HTML table row with server data
      const row = `<tr>
        <td>${data.mode}</td>
        <td>${data.status}</td>
        <td>${data.pingable}</td>
        <td>${data.clients}</td>
        <td>${data.total_rx} MB</td>
        <td>${data.total_tx} MB</td>
        <td>${formatUptime(data.uptime)}</td>
        <td>${data.local_ip}</td>
        <td>${data.public_ip}</td>
      </tr>`;

      // Update server status table tbody content
      document.getElementById("server-status-body").innerHTML = row;
    })
    .catch(error => {
      // Handle errors during data loading
      console.error("Error loading server status:", error);

      // Display error message in table
      document.getElementById("server-status-body").innerHTML = `
        <tr>
          <td colspan="9" class="text-center text-danger">
            Server data loading error
          </td>
        </tr>
      `;
    });
}
