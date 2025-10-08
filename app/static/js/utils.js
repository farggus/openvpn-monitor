/**
 * Утилиты - Вспомогательные функции
 * Описание: Содержит общие вспомогательные функции для форматирования и обработки данных
 */

/**
 * Экранирует HTML-символы в строке для безопасного отображения
 * Защищает от XSS-атак при выводе пользовательских данных
 *
 * @param {*} value - Значение для экранирования
 * @returns {string} Экранированная строка
 *
 * @example
 * escapeHtml("<script>alert('xss')</script>")
 * // Вернет: "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;"
 */
function escapeHtml(value) {
  // Если значение null или undefined - вернуть пустую строку
  if (value === null || value === undefined) return '';

  // Преобразовать в строку и заменить опасные символы на HTML-сущности
  return String(value)
    .replace(/&/g, '&amp;')      // & должен быть первым
    .replace(/</g, '&lt;')       // < меньше
    .replace(/>/g, '&gt;')       // > больше
    .replace(/"/g, '&quot;')     // " двойные кавычки
    .replace(/'/g, '&#39;');     // ' одинарные кавычки
}

/**
 * Форматирует значение в гигабайтах с двумя знаками после запятой
 *
 * @param {number} value - Значение в гигабайтах
 * @returns {string} Отформатированная строка вида "X.XX GB"
 *
 * @example
 * formatGb(1.5678) // Вернет: "1.57 GB"
 * formatGb(null)   // Вернет: "0.00 GB"
 */
function formatGb(value) {
  // Проверка на валидное число
  if (typeof value !== 'number' || Number.isNaN(value)) {
    return '0.00 GB';
  }
  // Округление до 2 знаков и добавление единицы измерения
  return `${value.toFixed(2)} GB`;
}

/**
 * Вычисляет время работы сервера на основе времени запуска
 *
 * @param {string} uptimeStr - Строка с датой и временем запуска сервера
 * @returns {string} Форматированная строка времени работы (например, "2d 5h 30m")
 *
 * @example
 * formatUptime("2025-10-06T10:00:00")
 * // Если сейчас 2025-10-08T15:30:00, вернет: "2d 5h 30m"
 */
function formatUptime(uptimeStr) {
  // Парсинг строки в объект Date
  const uptime = new Date(uptimeStr);
  const now = new Date();

  // Вычисление разницы в миллисекундах
  const diffMs = now - uptime;

  // Проверка на валидность даты и положительную разницу
  if (isNaN(uptime.getTime()) || diffMs < 0) {
    return "Unknown";
  }

  // Конвертация миллисекунд в минуты и часы
  const minutes = Math.floor(diffMs / 60000);  // 1 минута = 60000 мс
  const hours = Math.floor(minutes / 60);       // 1 час = 60 минут
  const days = Math.floor(hours / 24);          // 1 день = 24 часа

  // Формирование строки вывода
  return `${days > 0 ? days + "d " : ""}${hours % 24}h ${minutes % 60}m`;
}
