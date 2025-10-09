/**
 * Utilities - Helper functions
 * Description: Contains common utility functions for formatting and data processing
 */

/**
 * Escapes HTML characters in a string for safe display
 * Protects against XSS attacks when outputting user data
 *
 * @param {*} value - Value to escape
 * @returns {string} Escaped string
 *
 * @example
 * escapeHtml("<script>alert('xss')</script>")
 * // Returns: "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;"
 */
function escapeHtml(value) {
  // If value is null or undefined - return empty string
  if (value === null || value === undefined) return '';

  // Convert to string and replace dangerous characters with HTML entities
  return String(value)
    .replace(/&/g, '&amp;')      // & must be first
    .replace(/</g, '&lt;')       // < less than
    .replace(/>/g, '&gt;')       // > greater than
    .replace(/"/g, '&quot;')     // " double quotes
    .replace(/'/g, '&#39;');     // ' single quotes
}

/**
 * Formats a value in gigabytes with two decimal places
 *
 * @param {number} value - Value in gigabytes
 * @returns {string} Formatted string like "X.XX GB"
 *
 * @example
 * formatGb(1.5678) // Returns: "1.57 GB"
 * formatGb(null)   // Returns: "0.00 GB"
 */
function formatGb(value) {
  // Check for valid number
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0.00 GB';
  }
  // Round to 2 decimal places and add unit of measurement
  return `${value.toFixed(2)} GB`;
}

/**
 * Calculates server uptime based on start time
 *
 * @param {string} uptimeStr - String with server start date and time
 * @returns {string} Formatted uptime string (e.g., "2d 5h 30m")
 *
 * @example
 * formatUptime("2025-10-06T10:00:00")
 * // If current time is 2025-10-08T15:30:00, returns: "2d 5h 30m"
 */
function formatUptime(uptimeStr) {
  // Parse string into Date object
  const uptime = new Date(uptimeStr);
  const now = new Date();

  // Calculate difference in milliseconds
  const diffMs = now - uptime;

  // Check for valid date and positive difference
  if (isNaN(uptime.getTime()) || diffMs < 0) {
    return "Unknown";
  }

  // Convert milliseconds to minutes and hours
  const minutes = Math.floor(diffMs / 60000);  // 1 minute = 60000 ms
  const hours = Math.floor(minutes / 60);       // 1 hour = 60 minutes
  const days = Math.floor(hours / 24);          // 1 day = 24 hours

  // Build output string
  return `${days > 0 ? days + "d " : ""}${hours % 24}h ${minutes % 60}m`;
}
