/**
 * Traffic charts - Data transfer speed visualization
 * Description: Creating and updating Chart.js charts to display client traffic
 */

// === ADDITIONAL VARIABLES ===
let currentChartMode = 'all'; // 'all' or 'individual'
let currentSelectedClient = null; // selected client name for individual chart
let chartStatistics = {}; // statistics for each client
let currentPeriod = 30; // current period in minutes
let historicalDataLoaded = false; // historical data loading flag
let hideZeroValues = true; // hide zero Rx/Tx values (active by default)
let showDetailedMode = false; // detailed display mode (false = averaged, max 40 points)

/**
 * Extended color palette for charts
 */
const CHART_COLORS = [
  { primary: 'rgba(54, 162, 235, 1)', secondary: 'rgba(255, 99, 132, 1)', gradient: 'rgba(54, 162, 235, 0.2)' },
  { primary: 'rgba(75, 192, 192, 1)', secondary: 'rgba(255, 159, 64, 1)', gradient: 'rgba(75, 192, 192, 0.2)' },
  { primary: 'rgba(153, 102, 255, 1)', secondary: 'rgba(255, 205, 86, 1)', gradient: 'rgba(153, 102, 255, 0.2)' },
  { primary: 'rgba(255, 99, 132, 1)', secondary: 'rgba(54, 162, 235, 1)', gradient: 'rgba(255, 99, 132, 0.2)' },
  { primary: 'rgba(255, 159, 64, 1)', secondary: 'rgba(75, 192, 192, 1)', gradient: 'rgba(255, 159, 64, 0.2)' },
  { primary: 'rgba(201, 203, 207, 1)', secondary: 'rgba(153, 102, 255, 1)', gradient: 'rgba(201, 203, 207, 0.2)' },
];

/**
 * Creates gradient for chart area fill
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {string} color - Gradient color
 * @returns {CanvasGradient} Gradient for fill
 */
function createGradient(ctx, color) {
  const gradient = ctx.createLinearGradient(0, 0, 0, 400);
  gradient.addColorStop(0, color);
  gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
  return gradient;
}

/**
 * Loads historical traffic metrics data from API
 * @param {number} period - Period in minutes
 * @param {string|null} clientName - Client name (optional)
 * @returns {Promise<Object>} Promise with metrics data
 */
async function loadHistoricalMetrics(period, clientName = null) {
  try {
    let url = `/api/traffic-metrics?period=${period}`;
    if (clientName) {
      url += `&client=${encodeURIComponent(clientName)}`;
    }

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data.metrics || {};
  } catch (error) {
    console.error('Failed to load historical metrics:', error);
    return {};
  }
}

/**
 * Filters zero values, replacing them with null for chart gaps
 * @param {number} value - Value to check
 * @returns {number|null} Original value or null if zero should be hidden
 */
function filterZeroValue(value) {
  if (hideZeroValues && value === 0) {
    return null;
  }
  return value;
}

/**
 * Aggregates data to maximum 40 points, averaging values
 * @param {Array} labels - Array of time labels
 * @param {Array} data - Array of data values
 * @returns {Object} Object with aggregated labels and data
 */
function aggregateDataPoints(labels, data) {
  const maxPoints = 40;

  if (labels.length <= maxPoints) {
    // If points are less than or equal to 40, return as is
    return { labels, data };
  }

  // Calculate group size for aggregation
  const groupSize = Math.ceil(labels.length / maxPoints);
  const aggregatedLabels = [];
  const aggregatedData = [];

  for (let i = 0; i < labels.length; i += groupSize) {
    const group = data.slice(i, i + groupSize);

    // Take average time label from group (center)
    const middleIndex = i + Math.floor(groupSize / 2);
    aggregatedLabels.push(labels[Math.min(middleIndex, labels.length - 1)]);

    // Average values, ignoring null
    const validValues = group.filter(v => v !== null && v !== undefined);
    if (validValues.length > 0) {
      const avg = validValues.reduce((sum, val) => sum + val, 0) / validValues.length;
      aggregatedData.push(avg);
    } else {
      aggregatedData.push(null);
    }
  }

  return { labels: aggregatedLabels, data: aggregatedData };
}

/**
 * Converts historical data to Chart.js format
 * @param {Object} metricsData - Metrics data from API
 * @returns {Object} Object with time labels and dataset data
 */
function processHistoricalData(metricsData) {
  const allTimestamps = new Set();
  const clientData = {};

  // Collect all time labels and data for each client
  for (const [clientName, points] of Object.entries(metricsData)) {
    clientData[clientName] = { rx: {}, tx: {} };

    for (const point of points) {
      const timestamp = point.timestamp;
      allTimestamps.add(timestamp);

      const rxValue = point.speed_rx || 0;
      const txValue = point.speed_tx || 0;

      clientData[clientName].rx[timestamp] = filterZeroValue(rxValue);
      clientData[clientName].tx[timestamp] = filterZeroValue(txValue);
    }
  }

  // Sort time labels
  const sortedTimestamps = Array.from(allTimestamps).sort();

  // Format time labels for display
  const formattedLabels = sortedTimestamps.map(ts => {
    const date = new Date(ts);
    return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  });

  return {
    timestamps: sortedTimestamps,
    labels: formattedLabels,
    clientData: clientData
  };
}

/**
 * Initializes or reinitializes traffic chart with historical data
 * @param {Array<string>} users - Array of client names to display on chart
 * @param {string} mode - Display mode ('all' or 'individual')
 * @param {string} selectedClient - Selected client name (for 'individual' mode)
 * @param {Object|null} historicalData - Historical data (optional)
 */
async function initializeChart(users, mode = 'all', selectedClient = null, historicalData = null) {
  // If chart already exists - destroy it before creating new one
  if (chart) {
    chart.destroy();
  }

  // Reset chart data
  chartData = { labels: [], datasets: [] };

  // If no historical data provided, load it
  if (!historicalData) {
    const clientToLoad = mode === 'individual' ? selectedClient : null;
    const metricsData = await loadHistoricalMetrics(currentPeriod, clientToLoad);
    historicalData = processHistoricalData(metricsData);
  }

  // Fill chart with historical data
  if (historicalData && historicalData.labels.length > 0) {
    // In averaging mode (showDetailedMode = false) aggregate data
    if (!showDetailedMode) {
      const aggregated = aggregateDataPoints(historicalData.labels, historicalData.labels);
      chartData.labels = aggregated.labels;
      // Save aggregation info for use when processing datasets
      historicalData.isAggregated = true;
      historicalData.aggregatedLabels = aggregated.labels;
    } else {
      chartData.labels = historicalData.labels;
      historicalData.isAggregated = false;
    }
  }

  // Initialize client statistics
  users.forEach(user => {
    if (!chartStatistics[user]) {
      chartStatistics[user] = {
        peakRx: 0,
        peakTx: 0,
        currentRx: 0,
        currentTx: 0,
        avgRx: 0,
        avgTx: 0,
        totalPoints: 0
      };
    }
  });

  // Determine which clients to display
  const displayUsers = mode === 'individual' && selectedClient
    ? [selectedClient]
    : users;

  // Create datasets for each client
  displayUsers.forEach((user, i) => {
    const colorScheme = CHART_COLORS[i % CHART_COLORS.length];

    // Prepare historical data for this client
    const rxData = [];
    const txData = [];

    if (historicalData && historicalData.clientData && historicalData.clientData[user]) {
      const clientHistData = historicalData.clientData[user];

      // Fill data for each time label
      historicalData.timestamps.forEach(timestamp => {
        const rxVal = clientHistData.rx[timestamp];
        const txVal = clientHistData.tx[timestamp];

        // Apply filtering (null may already be set in processHistoricalData)
        rxData.push(rxVal !== undefined && rxVal !== null ? rxVal : filterZeroValue(0));
        txData.push(txVal !== undefined && txVal !== null ? txVal : filterZeroValue(0));

        // Update statistics (use real values, not null)
        const rxValForStats = rxVal !== null && rxVal !== undefined ? rxVal : 0;
        const txValForStats = txVal !== null && txVal !== undefined ? txVal : 0;

        if (!chartStatistics[user]) {
          chartStatistics[user] = {
            peakRx: 0,
            peakTx: 0,
            currentRx: 0,
            currentTx: 0,
            avgRx: 0,
            avgTx: 0,
            totalPoints: 0,
            sumRx: 0,
            sumTx: 0
          };
        }

        chartStatistics[user].peakRx = Math.max(chartStatistics[user].peakRx, rxValForStats);
        chartStatistics[user].peakTx = Math.max(chartStatistics[user].peakTx, txValForStats);
        chartStatistics[user].sumRx += rxValForStats;
        chartStatistics[user].sumTx += txValForStats;
        chartStatistics[user].totalPoints++;
        chartStatistics[user].avgRx = chartStatistics[user].sumRx / chartStatistics[user].totalPoints;
        chartStatistics[user].avgTx = chartStatistics[user].sumTx / chartStatistics[user].totalPoints;
      });

      // Current values - last in array
      if (rxData.length > 0) {
        chartStatistics[user].currentRx = rxData[rxData.length - 1];
        chartStatistics[user].currentTx = txData[txData.length - 1];
      }

      // Apply aggregation in non-detailed display mode
      if (!showDetailedMode && historicalData.isAggregated) {
        const aggregatedRx = aggregateDataPoints(historicalData.labels, rxData);
        const aggregatedTx = aggregateDataPoints(historicalData.labels, txData);
        rxData.length = 0;
        txData.length = 0;
        rxData.push(...aggregatedRx.data);
        txData.push(...aggregatedTx.data);
      }
    }

    chartData.datasets.push(
      // Inbound traffic line (Receive)
      {
        label: `${user} ↓ Rx`,
        data: rxData,
        borderColor: colorScheme.primary,
        backgroundColor: colorScheme.gradient,
        fill: mode === 'individual', // Fill only in individual mode
        borderWidth: 2,
        tension: 0.4, // Line smoothing
        pointRadius: mode === 'individual' ? 3 : 0, // Points only in individual mode
        pointHoverRadius: 5,
        spanGaps: true // Don't break line on null values
      },
      // Outbound traffic line (Transmit)
      {
        label: `${user} ↑ Tx`,
        data: txData,
        borderColor: colorScheme.secondary,
        backgroundColor: colorScheme.gradient,
        fill: false,
        borderWidth: 2,
        borderDash: [5, 5],
        tension: 0.4,
        pointRadius: mode === 'individual' ? 3 : 0,
        pointHoverRadius: 5,
        spanGaps: true // Don't break line on null values
      }
    );
  });

  // Calculate maximum value for dynamic Y scale
  let maxValue = 0.5; // Minimum scale by default
  chartData.datasets.forEach(dataset => {
    if (dataset.data && dataset.data.length > 0) {
      const dataMax = Math.max(...dataset.data.filter(v => v !== null && v !== undefined));
      if (dataMax > maxValue) {
        maxValue = dataMax;
      }
    }
  });

  // Round up to nearest 0.1
  maxValue = Math.ceil(maxValue * 10) / 10;

  // Ensure minimum 0.5
  if (maxValue < 0.5) {
    maxValue = 0.5;
  }

  // Check that canvas element is available (chart modal is open)
  if (chartCanvas) {
    const ctx = chartCanvas.getContext('2d');

    // Create Chart.js instance with improved settings
    chart = new Chart(ctx, {
      type: 'line',
      data: chartData,
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              usePointStyle: true,
              padding: 15,
              font: {
                size: 11
              }
            }
          },
          tooltip: {
            enabled: showDetailedMode, // Disable tooltips in averaging mode
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleFont: { size: 13, weight: 'bold' },
            bodyFont: { size: 12 },
            padding: 10,
            displayColors: true,
            callbacks: {
              label: function(context) {
                let label = context.dataset.label || '';
                if (label) {
                  label += ': ';
                }
                if (context.parsed.y !== null) {
                  label += context.parsed.y.toFixed(3) + ' MB/s';
                }
                return label;
              },
              afterBody: function(context) {
                if (mode === 'individual' && context.length > 0) {
                  const clientName = selectedClient;
                  const stats = chartStatistics[clientName];
                  if (stats) {
                    return [
                      '',
                      `Peak Rx: ${stats.peakRx.toFixed(3)} MB/s`,
                      `Peak Tx: ${stats.peakTx.toFixed(3)} MB/s`,
                      `Average Rx: ${stats.avgRx.toFixed(3)} MB/s`,
                      `Average Tx: ${stats.avgTx.toFixed(3)} MB/s`
                    ];
                  }
                }
                return [];
              }
            }
          }
        },
        scales: {
          x: {
            display: true,
            title: {
              display: true,
              text: 'Time',
              font: { size: 12 }
            },
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            }
          },
          y: {
            display: true,
            title: {
              display: true,
              text: 'Speed (MB/s)',
              font: { size: 12 }
            },
            beginAtZero: true,
            max: maxValue,
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              stepSize: 0.1,
              callback: function(value) {
                return value.toFixed(1);
              }
            }
          }
        }
      }
    });
  }
}

/**
 * Updates chart data with new transfer speed values
 * Adds new data points in real-time
 *
 * @param {string} timeLabel - Time label for X axis (e.g., "14:30:25")
 * @param {Object} datasetMap - Dataset map {dataset_name: data_array}
 * @param {string} clientName - Client name
 * @param {number} speedRx - Inbound traffic speed in MB/s
 * @param {number} speedTx - Outbound traffic speed in MB/s
 */
function updateChartData(timeLabel, datasetMap, clientName, speedRx, speedTx) {
  // Add new time label to X axis
  if (chartData.labels) {
    chartData.labels.push(timeLabel);

    // Remove old points that are outside current period
    // Calculate maximum number of points based on period
    // With updates every 10 seconds: 30 min = 180 points, 1 hour = 360 points, etc.
    const maxPoints = (currentPeriod * 60) / 10;

    if (chartData.labels.length > maxPoints) {
      chartData.labels.shift();
    }
  }

  // Update client statistics
  if (!chartStatistics[clientName]) {
    chartStatistics[clientName] = {
      peakRx: 0,
      peakTx: 0,
      currentRx: 0,
      currentTx: 0,
      avgRx: 0,
      avgTx: 0,
      totalPoints: 0,
      sumRx: 0,
      sumTx: 0
    };
  }

  const stats = chartStatistics[clientName];
  stats.currentRx = speedRx;
  stats.currentTx = speedTx;
  stats.peakRx = Math.max(stats.peakRx, speedRx);
  stats.peakTx = Math.max(stats.peakTx, speedTx);
  stats.totalPoints++;
  stats.sumRx = (stats.sumRx || 0) + speedRx;
  stats.sumTx = (stats.sumTx || 0) + speedTx;
  stats.avgRx = stats.sumRx / stats.totalPoints;
  stats.avgTx = stats.sumTx / stats.totalPoints;

  // Update inbound traffic data (Rx)
  const rxDatasetName = `${clientName} ↓ Rx`;
  if (datasetMap[rxDatasetName]) {
    // Apply zero value filtering
    datasetMap[rxDatasetName].push(filterZeroValue(speedRx));

    // Remove old points based on current period
    const maxPoints = (currentPeriod * 60) / 10;
    if (datasetMap[rxDatasetName].length > maxPoints) {
      datasetMap[rxDatasetName].shift();
    }
  }

  // Update outbound traffic data (Tx)
  const txDatasetName = `${clientName} ↑ Tx`;
  if (datasetMap[txDatasetName]) {
    // Apply zero value filtering
    datasetMap[txDatasetName].push(filterZeroValue(speedTx));

    // Remove old points based on current period
    const maxPoints = (currentPeriod * 60) / 10;
    if (datasetMap[txDatasetName].length > maxPoints) {
      datasetMap[txDatasetName].shift();
    }
  }
}

/**
 * Updates statistics display on page
 * @param {string} clientName - Client name (null for total statistics)
 */
function updateChartStatistics(clientName = null) {
  let totalCurrentRx = 0;
  let totalCurrentTx = 0;
  let totalPeakRx = 0;
  let totalPeakTx = 0;

  if (clientName && chartStatistics[clientName]) {
    const stats = chartStatistics[clientName];
    totalCurrentRx = stats.currentRx;
    totalCurrentTx = stats.currentTx;
    totalPeakRx = stats.peakRx;
    totalPeakTx = stats.peakTx;
  } else {
    // Sum statistics for all clients
    Object.values(chartStatistics).forEach(stats => {
      totalCurrentRx += stats.currentRx;
      totalCurrentTx += stats.currentTx;
      totalPeakRx = Math.max(totalPeakRx, stats.peakRx);
      totalPeakTx = Math.max(totalPeakTx, stats.peakTx);
    });
  }

  // Update DOM elements
  const statCurrentRx = document.getElementById('statCurrentRx');
  const statCurrentTx = document.getElementById('statCurrentTx');
  const statPeakRx = document.getElementById('statPeakRx');
  const statPeakTx = document.getElementById('statPeakTx');

  if (statCurrentRx) statCurrentRx.textContent = totalCurrentRx.toFixed(3) + ' MB/s';
  if (statCurrentTx) statCurrentTx.textContent = totalCurrentTx.toFixed(3) + ' MB/s';
  if (statPeakRx) statPeakRx.textContent = totalPeakRx.toFixed(3) + ' MB/s';
  if (statPeakTx) statPeakTx.textContent = totalPeakTx.toFixed(3) + ' MB/s';
}

/**
 * Force chart redraw
 * Called after updating all data
 */
function refreshChart() {
  if (chart) {
    chart.update();

    // Update statistics
    if (currentChartMode === 'individual' && currentSelectedClient) {
      updateChartStatistics(currentSelectedClient);
    } else {
      updateChartStatistics();
    }
  }
}

/**
 * Handles chart display mode switching
 */
function handleChartModeChange() {
  const viewAllRadio = document.getElementById('chartViewAll');
  const viewIndividualRadio = document.getElementById('chartViewIndividual');
  const clientSelect = document.getElementById('clientSelect');
  const clientSelectLabel = document.getElementById('clientSelectLabel');

  if (!viewAllRadio || !viewIndividualRadio || !clientSelect) return;

  const updateMode = () => {
    currentChartMode = viewAllRadio.checked ? 'all' : 'individual';

    if (currentChartMode === 'individual') {
      clientSelect.style.display = 'block';
      clientSelectLabel.style.display = 'block';

      // Fill select with clients if not already filled
      if (clientSelect.options.length <= 1) {
        // Get client list from lastStats
        const clients = Object.keys(lastStats);
        clients.forEach(clientName => {
          const option = document.createElement('option');
          option.value = clientName;
          option.textContent = clientName;
          clientSelect.appendChild(option);
        });
      }
    } else {
      clientSelect.style.display = 'none';
      clientSelectLabel.style.display = 'none';
    }

    // Reinitialize chart
    const users = Object.keys(lastStats);
    if (users.length > 0) {
      initializeChart(users, currentChartMode, currentSelectedClient);
    }
  };

  viewAllRadio.addEventListener('change', updateMode);
  viewIndividualRadio.addEventListener('change', updateMode);

  clientSelect.addEventListener('change', (e) => {
    currentSelectedClient = e.target.value;
    if (currentSelectedClient) {
      const users = Object.keys(lastStats);
      initializeChart(users, currentChartMode, currentSelectedClient);
    }
  });

  // Period filter handlers
  const periodRadios = document.querySelectorAll('input[name="chartPeriod"]');
  periodRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      currentPeriod = parseInt(e.target.value, 10);

      // Reinitialize chart with new period
      const users = Object.keys(lastStats);
      if (users.length > 0) {
        initializeChart(users, currentChartMode, currentSelectedClient);
      }
    });
  });

  // Hide zero values checkbox handler
  const hideZeroCheckbox = document.getElementById('hideZeroValues');
  if (hideZeroCheckbox) {
    hideZeroCheckbox.addEventListener('change', (e) => {
      hideZeroValues = e.target.checked;

      // Reinitialize chart with new setting
      const users = Object.keys(lastStats);
      if (users.length > 0) {
        initializeChart(users, currentChartMode, currentSelectedClient);
      }
    });
  }

  // Detailed display mode checkbox handler
  const showDetailedCheckbox = document.getElementById('showDetailedMode');
  if (showDetailedCheckbox) {
    showDetailedCheckbox.addEventListener('change', (e) => {
      showDetailedMode = e.target.checked;

      // Reinitialize chart with new mode
      const users = Object.keys(lastStats);
      if (users.length > 0) {
        initializeChart(users, currentChartMode, currentSelectedClient);
      }
    });
  }
}
