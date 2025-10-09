/**
 * Theme management - Toggle between light and dark theme
 * Description: Provides interface theme switching and saves user preference
 */

/**
 * Toggles interface theme between light and dark
 * Changes Bootstrap classes for body, tables, modals, and forms
 *
 * @example
 * // On "Switch Theme" button click
 * toggleTheme(); // Switches theme from current to opposite
 */
function toggleTheme() {
  // Determine current theme by presence of bg-dark class on body
  const isDark = document.body.classList.contains("bg-dark");

  /**
   * Helper function to toggle classes for a group of elements
   * @param {string} selector - CSS selector for elements
   * @param {string} darkClass - Class for dark theme
   * @param {string} lightClass - Class for light theme
   */
  const toggle = (selector, darkClass, lightClass) => {
    document.querySelectorAll(selector).forEach(el => {
      // If currently dark - switch to light (!isDark = true)
      // If currently light - switch to dark (!isDark = false)
      el.classList.toggle(darkClass, !isDark);  // Add dark class if switching to dark theme
      el.classList.toggle(lightClass, isDark);   // Add light class if switching to light theme
    });
  };

  // === MAIN BACKGROUND ===
  // Toggle body background
  document.body.classList.toggle("bg-dark", !isDark);
  document.body.classList.toggle("bg-light", isDark);

  // === TABLES ===
  // Toggle table color
  toggle("table", "table-dark", "table-light");
  // Toggle table headers
  toggle("thead", "table-dark", "table-light");
  // Toggle table footers
  toggle("tfoot", "table-dark", "table-light");

  // === MODALS ===
  // Toggle modal background
  toggle(".modal-content, .modal-header, .modal-body", "bg-dark", "bg-light");
  // Toggle text color in modals
  toggle(".modal-content, .modal-header, .modal-body", "text-light", "text-dark");

  // === TEXT ELEMENTS ===
  // Toggle color for headings, table cells, and form elements
  toggle("h1, h2, h3, h4, h5, h6, th, label, button", "text-light", "text-dark");

  // === FORM ELEMENTS ===
  // Toggle input field background
  toggle("input, select, textarea", "bg-dark", "bg-light");
  // Toggle text color in input fields
  toggle("input, select, textarea", "text-light", "text-dark");
  // Toggle border color of input fields
  toggle("input, select, textarea", "border-light", "border-dark");

  // === DROPDOWNS AND CALENDARS ===
  // Delay necessary for elements that may be created dynamically
  setTimeout(() => {
    toggle(
      ".dropdown-menu, .select2-dropdown, datalist, .datepicker, .flatpickr-calendar, .ui-datepicker",
      "bg-dark",
      "bg-light"
    );
    toggle(
      ".dropdown-menu, .select2-dropdown, datalist, .datepicker, .flatpickr-calendar, .ui-datepicker",
      "text-light",
      "text-dark"
    );
  }, 100);

  // === CLIENTS LIST ===
  // Styles for clients list are inherited from .modal-content.bg-dark
  // No additional toggling required
}
