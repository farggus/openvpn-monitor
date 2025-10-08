/**
 * Управление темами - Переключение между светлой и темной темой
 * Описание: Обеспечивает переключение темы интерфейса и сохранение выбора пользователя
 */

/**
 * Переключает тему интерфейса между светлой и темной
 * Изменяет классы Bootstrap для body, таблиц, модальных окон и форм
 *
 * @example
 * // При клике на кнопку "Switch Theme"
 * toggleTheme(); // Переключит тему с текущей на противоположную
 */
function toggleTheme() {
  // Определяем текущую тему по наличию класса bg-dark у body
  const isDark = document.body.classList.contains("bg-dark");

  /**
   * Вспомогательная функция для переключения классов у группы элементов
   * @param {string} selector - CSS селектор элементов
   * @param {string} darkClass - Класс для темной темы
   * @param {string} lightClass - Класс для светлой темы
   */
  const toggle = (selector, darkClass, lightClass) => {
    document.querySelectorAll(selector).forEach(el => {
      // Если сейчас темная - переключаем на светлую (!isDark = true)
      // Если сейчас светлая - переключаем на темную (!isDark = false)
      el.classList.toggle(darkClass, !isDark);  // Добавить темный класс если переходим в темную тему
      el.classList.toggle(lightClass, isDark);   // Добавить светлый класс если переходим в светлую тему
    });
  };

  // === ОСНОВНОЙ ФОН ===
  // Переключаем фон body
  document.body.classList.toggle("bg-dark", !isDark);
  document.body.classList.toggle("bg-light", isDark);

  // === ТАБЛИЦЫ ===
  // Переключаем цвет таблиц
  toggle("table", "table-dark", "table-light");
  // Переключаем заголовки таблиц
  toggle("thead", "table-dark", "table-light");
  // Переключаем подвалы таблиц
  toggle("tfoot", "table-dark", "table-light");

  // === МОДАЛЬНЫЕ ОКНА ===
  // Переключаем фон модальных окон
  toggle(".modal-content, .modal-header, .modal-body", "bg-dark", "bg-light");
  // Переключаем цвет текста в модальных окнах
  toggle(".modal-content, .modal-header, .modal-body", "text-light", "text-dark");

  // === ТЕКСТОВЫЕ ЭЛЕМЕНТЫ ===
  // Переключаем цвет заголовков, ячеек таблиц и элементов форм
  toggle("h1, h2, h3, h4, h5, h6, th, label, button", "text-light", "text-dark");

  // === ЭЛЕМЕНТЫ ФОРМ ===
  // Переключаем фон полей ввода
  toggle("input, select, textarea", "bg-dark", "bg-light");
  // Переключаем цвет текста в полях ввода
  toggle("input, select, textarea", "text-light", "text-dark");
  // Переключаем цвет границ полей ввода
  toggle("input, select, textarea", "border-light", "border-dark");

  // === ВЫПАДАЮЩИЕ СПИСКИ И КАЛЕНДАРИ ===
  // Задержка необходима для элементов, которые могут быть созданы динамически
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

  // === СПИСОК КЛИЕНТОВ ===
  // Стили для списка клиентов наследуются от .modal-content.bg-dark
  // Дополнительное переключение не требуется
}
