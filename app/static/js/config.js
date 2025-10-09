/**
 * Configuration - Application global variables
 * Description: Contains all global state variables for the application
 */

// === STATISTICS AND TRAFFIC ===

/**
 * Storage for last client traffic metrics
 * Used to calculate data transfer speed
 * Structure: { client_name: { rx: bytes_received, tx: bytes_sent, timestamp: time } }
 */
let lastStats = {};

// === CHARTS ===

/**
 * Chart.js chart instance
 * null until initialization
 */
let chart = null;

/**
 * Data for displaying on traffic chart
 * Contains time labels and datasets for each client
 */
let chartData = {
  labels: [],      // Time labels (e.g., "14:30:25")
  datasets: []     // Datasets (Rx/Tx for each client)
};

/**
 * Reference to chart canvas element in modal
 * Used for deferred chart initialization
 */
let chartCanvas = null;

// === CONNECTION HISTORY ===

/**
 * Full connection history data
 * Loaded from API when opening history modal
 * @type {Array}
 */
let fullHistoryData = [];

// === CLIENTS ===

/**
 * Client summary information (statistics, sessions, traffic)
 * Loaded from /api/clients/summary
 * @type {Array}
 */
let clientsSummary = [];

/**
 * Bootstrap clients list modal instance
 * @type {bootstrap.Modal|null}
 */
let clientsModalInstance = null;

/**
 * Bootstrap client details modal instance
 * @type {bootstrap.Modal|null}
 * (DEPRECATED - replaced with accordion)
 */
// let clientDetailsModalInstance = null;

// === MAPS ===

/**
 * Leaflet map initialization flag
 * true after first map creation
 */
let mapInitialized = false;

/**
 * Leaflet map instance
 * @type {L.Map|null}
 */
let mapInstance = null;

/**
 * Array of markers on the map
 * Used for clearing when updating map
 * @type {Array<L.Marker>}
 */
let mapMarkers = [];

/**
 * IP address geolocation cache
 * Prevents repeated geolocation API requests
 * Structure: { "IP_address": { latitude, longitude, city, country_name, ... } }
 */
const geoCache = {};
