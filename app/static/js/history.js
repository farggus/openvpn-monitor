/**
 * История подключений - Управление историей VPN сессий
 * Описание: Загрузка, фильтрация и отображение истории подключений, а также визуализация на карте
 */

// === МОДАЛЬНОЕ ОКНО ИСТОРИИ ===

/**
 * Отображает статусное сообщение в таблице истории
 *
 * @param {string} message - Текст сообщения
 * @param {Object} options - Опции отображения
 * @param {boolean} [options.spinner=false] - Показывать ли спиннер загрузки
 * @param {string} [options.tone='muted'] - Тон сообщения (muted, danger)
 */
function showHistoryStatus(message, { spinner = false, tone = 'muted' } = {}) {
  // Определение CSS класса в зависимости от тона
  const toneClass = tone === 'danger' ? 'text-danger' : 'text-muted';

  // Формирование контента со спиннером или без
  const content = spinner
    ? `<div class="d-flex align-items-center justify-content-center gap-2">
         <div class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></div>
         <span>${message}</span>
       </div>`
    : message;

  // Обновление tbody таблицы истории
  document.getElementById('history-body').innerHTML =
    `<tr><td colspan="11" class="text-center py-4 ${toneClass}">${content}</td></tr>`;
}

/**
 * Применяет фильтры к данным истории и обновляет таблицу
 * Фильтрует по дате и имени клиента
 */
function applyFilters() {
  // Получение значений фильтров
  const dateFilter = document.getElementById("filterDate").value;
  const userFilter = document.getElementById("filterUser").value.toLowerCase();
  const cityFilter = document.getElementById("filterCity").value.toLowerCase();

  // Фильтрация данных
  const filtered = window.fullHistoryData.filter(entry =>
    // Фильтр по дате: если не задан или timestamp начинается с даты
    (!dateFilter || entry.timestamp.startsWith(dateFilter)) &&
    // Фильтр по имени: если не задан или имя содержит строку поиска
    (!userFilter || entry.name.toLowerCase().includes(userFilter)) &&
    // Фильтр по городу: если не задан или город содержит строку поиска
    (!cityFilter || (entry.location?.city || "").toLowerCase().includes(cityFilter))
  );

  // Отображение отфильтрованных данных
  renderHistoryTable(filtered);
}

/**
 * Отрисовывает таблицу с историей подключений
 *
 * @param {Array<Object>} data - Массив записей истории
 */
function renderHistoryTable(data) {
  // Проверка на пустой результат
  if (!data.length) {
    document.getElementById("history-body").innerHTML =
      `<tr><td colspan="11" class="text-center py-4 text-muted">Нет записей истории</td></tr>`;
    return;
  }

  // Формирование HTML строк таблицы
  const rows = data.map(entry => {
    // === ОБРАБОТКА IP АДРЕСОВ ===
    // Поддержка legacy поля vpn_ip и новых полей vpn_ipv4/vpn_ipv6
    const legacyVpnIp = entry.vpn_ip ?? "";

    // Определение IPv4
    const vpnIpv4 = entry.vpn_ipv4 ||
                    (legacyVpnIp && legacyVpnIp.includes('.') ? legacyVpnIp : "");

    // Определение IPv6
    const rawIpv6 = entry.vpn_ipv6 ||
                    (legacyVpnIp && legacyVpnIp.includes(':') ? legacyVpnIp : "");
    const vpnIpv6 = rawIpv6 || "—";

    // Извлечение города из location
    const city = entry.location?.city ?? "—";

    // Формирование HTML строки
    return `
      <tr>
        <td>${entry.timestamp}</td>
        <td>${entry.name}</td>
        <td>${vpnIpv4}</td>
        <td>${vpnIpv6}</td>
        <td>${entry.ip}</td>
        <td>${entry.port ?? ""}</td>
        <td>${city}</td>
        <td>${entry.session_end ?? ""}</td>
        <td>${entry.duration ?? ""}</td>
        <td>${entry.rx ?? ""}</td>
        <td>${entry.tx ?? ""}</td>
      </tr>
    `;
  }).join("");

  // Обновление таблицы
  document.getElementById("history-body").innerHTML = rows;
}

// === КАРТА ИСТОРИИ ===

/**
 * Переменные для работы с картой истории
 * (отдельная карта для модального окна истории)
 */
let historyMapInstance = null;
let historyMapInitialized = false;
let historyMapMarkers = [];

/**
 * Создает или обновляет карту с маркерами из отфильтрованной истории
 * Использует данные о местоположении, сохраненные в записях истории
 *
 * @async
 * @returns {Promise<void>}
 */
async function buildHistoryMap() {
  // Поиск модального окна карты истории
  const modalEl = document.getElementById('historyMapModal');
  if (!modalEl) {
    alert('Добавьте модальное окно #historyMapModal в HTML');
    return;
  }

  // === ПРИМЕНЕНИЕ ФИЛЬТРОВ К ДАННЫМ ИСТОРИИ ===
  // Получение текущих значений фильтров
  const dateFilter = document.getElementById("filterDate")?.value || '';
  const userFilter = document.getElementById("filterUser")?.value.toLowerCase() || '';
  const cityFilter = document.getElementById("filterCity")?.value.toLowerCase() || '';

  // Фильтрация данных (используем window.fullHistoryData для доступа из IIFE)
  const filtered = window.fullHistoryData.filter(entry =>
    (!dateFilter || entry.timestamp.startsWith(dateFilter)) &&
    (!userFilter || entry.name.toLowerCase().includes(userFilter)) &&
    (!cityFilter || (entry.location?.city || "").toLowerCase().includes(cityFilter))
  );

  // Проверка на пустой результат
  if (filtered.length === 0) {
    alert('Нет записей для отображения на карте. Измените фильтры.');
    return;
  }

  // === ИНИЦИАЛИЗАЦИЯ КАРТЫ (ОДИН РАЗ) ===
  if (!historyMapInitialized) {
    // Создание экземпляра Leaflet карты
    historyMapInstance = L.map('historyMap').setView([20, 0], 2);

    // Добавление тайлового слоя OpenStreetMap
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: 'Map data © OpenStreetMap contributors'
    }).addTo(historyMapInstance);

    // Обработчик события показа модального окна
    // Исправление размеров карты после анимации открытия
    modalEl.addEventListener('shown.bs.modal', () => {
      setTimeout(() => {
        historyMapInstance.invalidateSize();
        // Пересчитываем bounds после invalidateSize, если есть маркеры
        if (historyMapMarkers.length > 0) {
          const bounds = historyMapMarkers.map(m => m.getLatLng());
          historyMapInstance.fitBounds(bounds, { padding: [30, 30] });
        }
      }, 50);
    });

    historyMapInitialized = true;
  }

  // === ОЧИСТКА СТАРЫХ МАРКЕРОВ ===
  historyMapMarkers.forEach(marker => historyMapInstance.removeLayer(marker));
  historyMapMarkers = [];

  // === ДЕДУПЛИКАЦИЯ ПО IP ===
  // Собираем уникальные IP адреса с их местоположением
  const ipLocationMap = new Map();

  for (const entry of filtered) {
    const ip = entry.ip;
    const location = entry.location;

    // Пропуск записей без IP или геолокации
    if (!ip || !location) continue;
    if (location.latitude == null || location.longitude == null) continue;

    // Сохраняем только первую запись для каждого IP
    if (!ipLocationMap.has(ip)) {
      ipLocationMap.set(ip, {
        ip: ip,
        latitude: location.latitude,
        longitude: location.longitude,
        city: location.city || '',
        country: location.country || ''
      });
    }
  }

  // Проверка наличия данных для отображения
  if (ipLocationMap.size === 0) {
    alert('Нет записей с геолокацией для отображения на карте.');
    return;
  }

  // === ДОБАВЛЕНИЕ МАРКЕРОВ НА КАРТУ ===
  const bounds = [];

  /**
   * Вспомогательная функция для добавления зеленого маркера
   * @param {number} lat - Широта
   * @param {number} lon - Долгота
   * @param {string} label - Текст всплывающего окна
   */
  const addGreenMarker = (lat, lon, label) => {
    const marker = L.circleMarker([lat, lon], {
      radius: 8,              // Размер маркера
      color: '#2e7d32',       // Цвет обводки (темно-зеленый)
      weight: 2,              // Толщина обводки
      fillColor: '#43a047',   // Цвет заливки (светло-зеленый)
      fillOpacity: 0.9        // Прозрачность заливки
    })
      .addTo(historyMapInstance)
      .bindPopup(label);

    historyMapMarkers.push(marker);
    bounds.push([lat, lon]);
  };

  // Добавление маркера для каждого уникального IP
  for (const [ip, loc] of ipLocationMap.entries()) {
    addGreenMarker(
      loc.latitude,
      loc.longitude,
      `${ip}<br>${loc.city} ${loc.country}`
    );
  }

  // === ОБНОВЛЕНИЕ ЗАГОЛОВКА МОДАЛЬНОГО ОКНА ===
  const modalTitle = modalEl.querySelector('.modal-title');
  if (modalTitle) {
    modalTitle.textContent = `История — Просмотр на карте (${ipLocationMap.size} уникальных мест)`;
  }

  // === АВТОМАТИЧЕСКОЕ ПОЗИЦИОНИРОВАНИЕ КАРТЫ ===
  if (bounds.length) {
    historyMapInstance.fitBounds(bounds, { padding: [30, 30] });
  }

  // === ПОКАЗ МОДАЛЬНОГО ОКНА ===
  // Показываем модальное окно после добавления всех маркеров
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
}

/**
 * Проверяет, открыто ли модальное окно карты истории
 * @returns {boolean} true если окно открыто
 */
function historyMapIsOpen() {
  const el = document.getElementById('historyMapModal');
  return el && el.classList.contains('show');
}

/**
 * Обновляет карту истории если она открыта
 * Вызывается при изменении фильтров
 */
function tryRefreshOpenHistoryMap() {
  if (historyMapIsOpen()) {
    buildHistoryMap();
  }
}
