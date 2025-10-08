/**
 * Главный модуль приложения - Инициализация и координация
 * Описание: Точка входа приложения, настройка обработчиков событий и периодического обновления данных
 */

// === ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ ===

/**
 * Главная функция инициализации
 * Выполняется после загрузки DOM
 */
document.addEventListener("DOMContentLoaded", function () {

  // === ПЕРИОДИЧЕСКОЕ ОБНОВЛЕНИЕ ДАННЫХ ===

  /**
   * Обновляет данные сервера и клиентов
   * Вызывается при инициализации и каждую секунду
   */
  const refreshAll = () => {
    fetchData();           // Обновление данных клиентов (из clients.js)
    fetchServerStatus();   // Обновление статуса сервера (из server.js)
  };

  // Первоначальная загрузка данных
  refreshAll();

  // Автоматическое обновление каждые 10 секунд
  setInterval(refreshAll, 10000);

  // === НАСТРОЙКА ОБРАБОТЧИКОВ КНОПОК ===

  // --- Кнопка переключения темы ---
  document.getElementById("themeToggle").addEventListener("click", toggleTheme);

  // --- Кнопка "Charts" - Открытие модального окна с графиками ---
  document.getElementById("chartsBtn").addEventListener("click", () => {
    const chartsModalEl = document.getElementById('chartsModal');
    const chartsModal = new bootstrap.Modal(chartsModalEl);
    chartsModal.show();
  });

  // Обработчик события показа модального окна графиков
  // Инициализация/обновление графика при открытии
  let chartModeHandlerInitialized = false;

  document.getElementById('chartsModal').addEventListener('shown.bs.modal', () => {
    chartCanvas = document.getElementById('trafficChartModal');

    // Инициализация обработчиков переключения режима графика (только один раз)
    if (!chartModeHandlerInitialized) {
      handleChartModeChange();
      chartModeHandlerInitialized = true;
    }

    if (!chart) {
      // График будет инициализирован при первом fetchData()
      // Принудительный запрос данных для гарантии создания графика
      fetchData(true);
    } else {
      // Обновление размеров графика после открытия модального окна
      chart.resize();
      chart.update();
    }
  });

  // --- Кнопка "Map View" - Открытие модального окна с картой ---
  document.getElementById("mapBtn").addEventListener("click", () => {
    const mapModalEl = document.getElementById('mapModal');
    const mapModal = new bootstrap.Modal(mapModalEl);
    mapModal.show();
  });

  // Обработчик события показа модального окна карты
  // Инициализация карты и загрузка маркеров при открытии
  document.getElementById('mapModal').addEventListener('shown.bs.modal', () => {
    if (!mapInitialized) {
      // Первоначальная инициализация карты
      mapInstance = L.map('mapModalMap').setView([20, 0], 2);

      // Добавление слоя тайлов OpenStreetMap
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'Map data © OpenStreetMap contributors'
      }).addTo(mapInstance);

      mapInitialized = true;
    } else {
      // Обновление размеров карты после открытия модального окна
      mapInstance.invalidateSize();
    }

    // Загрузка маркеров клиентов и сервера
    loadClientAndServerMarkers();
  });

  // === НАСТРОЙКА МОДАЛЬНОГО ОКНА ИСТОРИИ ===

  const historyModalEl = document.getElementById('historyModal');
  const historyModal = new bootstrap.Modal(historyModalEl);

  // Элементы управления фильтрами истории
  const historyControls = [
    document.getElementById('filterDate'),
    document.getElementById('filterUser'),
    document.getElementById('filterCity'),
    document.getElementById('resetFilters'),
    document.getElementById('viewOnMap')
  ];

  /**
   * Включает или отключает элементы управления фильтрами
   * @param {boolean} disabled - true для отключения, false для включения
   */
  const setHistoryControlsDisabled = (disabled) => {
    historyControls.forEach(ctrl => {
      if (ctrl) ctrl.disabled = disabled;
    });
  };

  // --- Кнопка "Connection history" - Открытие модального окна истории ---
  document.getElementById("historyBtn").addEventListener("click", () => {
    // Сброс данных
    fullHistoryData = [];
    window.fullHistoryData = fullHistoryData;
    document.getElementById("userList").innerHTML = "";
    document.getElementById("cityList").innerHTML = "";

    // Отображение индикатора загрузки
    showHistoryStatus("Загрузка истории...", { spinner: true });
    setHistoryControlsDisabled(true);

    // Показать модальное окно
    historyModal.show();

    // Загрузка данных истории из API
    $.getJSON("/api/history")
      .done(entries => {
        // Валидация ответа
        if (!Array.isArray(entries)) {
          const errorMessage = entries && entries.error ? entries.error : "Не удалось загрузить историю";
          showHistoryStatus(errorMessage, { tone: 'danger' });
          return;
        }

        // Фильтрация записей с валидными данными трафика
        fullHistoryData = entries.filter(e => e.rx !== null && e.tx !== null);
        window.fullHistoryData = fullHistoryData;

        // Извлечение уникальных имен клиентов для автозаполнения
        const names = [...new Set(fullHistoryData.map(e => e.name))];
        document.getElementById("userList").innerHTML = names.map(n => `<option value="${n}">`).join("");

        // Извлечение уникальных городов для автозаполнения
        const cities = [...new Set(fullHistoryData.map(e => e.location?.city).filter(c => c))];
        document.getElementById("cityList").innerHTML = cities.map(c => `<option value="${c}">`).join("");

        // Установка текущей даты в фильтр по умолчанию
        document.getElementById("filterDate").value = new Date().toISOString().split('T')[0];

        // Применение фильтров и отображение таблицы
        applyFilters();
      })
      .fail(() => {
        showHistoryStatus("Не удалось загрузить историю", { tone: 'danger' });
      })
      .always(() => {
        // Включение элементов управления после завершения загрузки
        setHistoryControlsDisabled(false);
      });
  });

  // === НАСТРОЙКА МОДАЛЬНОГО ОКНА КЛИЕНТОВ ===

  const clientsModalEl = document.getElementById('clientsModal');
  if (clientsModalEl) {
    clientsModalInstance = new bootstrap.Modal(clientsModalEl);
  }

  // Модальное окно деталей клиента больше не используется (заменено на accordion)
  // const clientDetailsModalEl = document.getElementById('clientDetailsModal');
  // if (clientDetailsModalEl) {
  //   clientDetailsModalInstance = new bootstrap.Modal(clientDetailsModalEl);
  // }

  // --- Кнопка "Clients" - Открытие модального окна списка клиентов ---
  const clientsBtn = document.getElementById('clientsBtn');
  if (clientsBtn) {
    clientsBtn.addEventListener('click', () => {
      showClientsStatus('Загрузка клиентов...', { spinner: true });

      if (clientsModalInstance) {
        clientsModalInstance.show();
      }

      // Загрузка сводной информации о клиентах
      fetchClientsSummary();
    });
  }

  // --- Обработчик клика по элементу списка клиентов ---
  // Bootstrap Collapse автоматически обрабатывает клики через data-bs-toggle="collapse"
  // Старый обработчик для открытия модального окна деталей удален

  // === НАСТРОЙКА ФИЛЬТРОВ ИСТОРИИ ===

  // Обработчик изменения фильтра по дате
  document.getElementById("filterDate").addEventListener("input", () => {
    applyFilters();
    // Автоматическое обновление карты истории если она открыта
    setTimeout(tryRefreshOpenHistoryMap, 120);
  });

  // Обработчик изменения фильтра по имени пользователя
  document.getElementById("filterUser").addEventListener("input", () => {
    applyFilters();
    // Автоматическое обновление карты истории если она открыта
    setTimeout(tryRefreshOpenHistoryMap, 120);
  });

  // Обработчик изменения фильтра по городу
  document.getElementById("filterCity").addEventListener("input", () => {
    applyFilters();
    // Автоматическое обновление карты истории если она открыта
    setTimeout(tryRefreshOpenHistoryMap, 120);
  });

  // Кнопка сброса фильтров
  document.getElementById("resetFilters").addEventListener("click", () => {
    document.getElementById("filterDate").value = "";
    document.getElementById("filterUser").value = "";
    document.getElementById("filterCity").value = "";
    renderHistoryTable(window.fullHistoryData);

    // Автоматическое обновление карты истории если она открыта
    setTimeout(tryRefreshOpenHistoryMap, 150);
  });

  // === КНОПКА "VIEW ON MAP" В ИСТОРИИ ===

  // Кнопка уже существует в HTML, привязываем обработчик
  const viewOnMapBtn = document.getElementById('viewOnMap');
  if (viewOnMapBtn) {
    viewOnMapBtn.addEventListener('click', buildHistoryMap);
  }

  // === ЭКСПОРТ ГЛОБАЛЬНЫХ ПЕРЕМЕННЫХ ===
  // Для доступа из других модулей (например, history.js использует window.fullHistoryData)
  window.fullHistoryData = fullHistoryData;
});
