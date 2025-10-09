/**
 * Maps - Display geographic location of clients
 * Description: Work with Leaflet maps to visualize client and server locations
 */

/**
 * Loads client and server markers onto the map
 * Gets location data from API and displays it on interactive map
 *
 * @async
 * @returns {Promise<void>}
 */
async function loadClientAndServerMarkers() {
  // Clear existing markers from map
  mapMarkers.forEach(marker => mapInstance.removeLayer(marker));
  mapMarkers = [];

  // Array of coordinates for automatic map positioning
  const bounds = [];

  try {
    // === LOAD CLIENT MARKERS ===

    // Get client data from API
    const clientsRes = await fetch("/api/clients");
    const clientsData = await clientsRes.json();
    const clients = clientsData.clients || [];

    // Process each client
    for (const client of clients) {
      const clientName = client.common_name || 'unknown';
      const location = client.location;

      // Check for location data availability
      if (location && location.latitude != null && location.longitude != null) {
        // Create marker on map
        const marker = L.marker([location.latitude, location.longitude])
          .addTo(mapInstance)  // Add marker to map
          .bindPopup(          // Bind popup to marker
            `<strong>${clientName}</strong><br>${location.city || ''}, ${location.country || ''}`
          );

        // Save marker reference for later cleanup
        mapMarkers.push(marker);

        // Add coordinates to bounds array for auto-positioning
        bounds.push([location.latitude, location.longitude]);
      }
    }

    // === LOAD SERVER MARKER ===

    // Get server data from API
    const serverRes = await fetch("/api/server-status");
    const serverData = await serverRes.json();
    const serverLocation = serverData.location;

    // Check for server location data availability
    if (serverLocation && serverLocation.latitude != null && serverLocation.longitude != null) {
      // Create red circle for server
      const serverMarker = L.circleMarker([serverLocation.latitude, serverLocation.longitude], {
        radius: 8,           // Circle radius
        fillColor: "#ff0000", // Red fill color
        color: "#cc0000",     // Dark red border color
        weight: 2,            // Border thickness
        opacity: 1,           // Border opacity
        fillOpacity: 0.8      // Fill opacity
      })
        .addTo(mapInstance)   // Add marker to map
        .bindPopup(           // Bind popup to marker
          `<strong>VPN Server</strong><br>${serverLocation.city || ''}, ${serverLocation.country || ''}<br>IP: ${serverData.public_ip || ''}`
        );

      // Save marker reference for later cleanup
      mapMarkers.push(serverMarker);

      // Add server coordinates to bounds array for auto-positioning
      bounds.push([serverLocation.latitude, serverLocation.longitude]);
    }

    // Automatic map positioning to all markers
    if (bounds.length) {
      // fitBounds adjusts map scale and center so all markers are visible
      mapInstance.fitBounds(bounds, { padding: [30, 30] });
    }

  } catch (error) {
    console.error('Error loading markers onto map:', error);
  }
}

/**
 * Adds one marker to the map (deprecated function, kept for compatibility)
 * Recommended to use loadClientAndServerMarkers() instead
 *
 * @deprecated
 * @param {Object} location - Location data object
 * @param {number} location.latitude - Latitude
 * @param {number} location.longitude - Longitude
 * @param {string} location.city - City
 * @param {string} location.country_name - Country name
 * @param {Object} client - Client data object
 * @param {string} client.common_name - Client name
 * @param {Array} bounds - Coordinates array for map bounds
 */
function addMarker(location, client, bounds) {
  // Create marker on map
  const marker = L.marker([location.latitude, location.longitude])
    .addTo(mapInstance)
    .bindPopup(`<strong>${client.common_name}</strong><br>${location.city}, ${location.country_name}`);

  // Save marker and update bounds
  mapMarkers.push(marker);
  bounds.push([location.latitude, location.longitude]);

  // Automatic map positioning
  mapInstance.fitBounds(bounds, { padding: [30, 30] });
}
