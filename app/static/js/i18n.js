/**
 * i18n - Internationalization module
 * Loads translations from server and provides t() function for translation lookup
 */

// Translations storage
let translations = {};

/**
 * Load translations from the server
 * @returns {Promise<void>}
 */
async function loadTranslations() {
  try {
    const response = await fetch('/api/translations');
    if (!response.ok) {
      throw new Error('Failed to load translations');
    }
    translations = await response.json();
  } catch (error) {
    console.error('Failed to load translations:', error);
    translations = {}; // Fallback to empty object
  }
}

/**
 * Translate a key to current locale
 * @param {string} key - Translation key
 * @returns {string} - Translated string or key if not found
 */
function t(key) {
  return translations[key] || key;
}

// Load translations immediately
loadTranslations();
