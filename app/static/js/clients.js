/**
 * Клиенты - Управление данными подключенных клиентов VPN
 * Описание: Загрузка, обработка и отображение информации о клиентах
 */

// === ОСНОВНАЯ ТАБЛИЦА КЛИЕНТОВ ===

/**
 * Загружает данные о подключенных клиентах из API и обновляет таблицу
 * Также обновляет графики трафика и вычисляет скорость передачи данных
 *
 * @param {boolean} [forceInitChart=false] - Принудительная инициализация графика
 * @async
 * @returns {Promise<void>}
 */
function fetchData(forceInitChart = false) {
  // Запрос данных о клиентах через jQuery AJAX
  $.getJSON("/api/clients", function(data) {
    // Текущее время для расчета скорости
    const now = Date.now();
    const timeLabel = new Date().toLocaleTimeString();

    // Переменные для общей статистики трафика
    let total_received = 0;
    let total_sent = 0;

    // Извлечение списка клиентов из ответа
    const clients = data.clients || [];
    let users = clients.map(c => c.common_name);

    // === ИНИЦИАЛИЗАЦИЯ ГРАФИКА ===
    // Проверяем, нужно ли создать или пересоздать график
    const needsChartInit = forceInitChart || !chart || chartData.datasets.length !== users.length * 2;

    if (needsChartInit) {
      // Если canvas не готов (модалка не открыта) - откладываем инициализацию
      if (!chart && !chartCanvas) {
        // График будет создан при открытии модального окна
      } else {
        // Инициализация графика с текущим списком клиентов
        initializeChart(users, currentChartMode, currentSelectedClient);
      }
    }

    // === ОБНОВЛЕНИЕ МЕТОК ВРЕМЕНИ НА ГРАФИКЕ ===
    if (chartData.labels) {
      chartData.labels.push(timeLabel);

      // Ограничение количества меток (показываем последние 20 точек)
      if (chartData.labels.length > 20) {
        chartData.labels.shift();
      }
    }

    // Создание карты наборов данных для быстрого доступа
    const datasetMap = chartData.datasets ?
      Object.fromEntries(chartData.datasets.map(ds => [ds.label, ds.data])) : {};

    // === ОБРАБОТКА ДАННЫХ КАЖДОГО КЛИЕНТА ===
    const rows = clients.map(client => {
      // Суммирование общего трафика
      total_received += client.bytes_received;
      total_sent += client.bytes_sent;

      // === РАСЧЕТ СКОРОСТИ ПЕРЕДАЧИ ДАННЫХ ===
      let speed_rx = 0;  // Скорость приема (MB/s)
      let speed_tx = 0;  // Скорость отправки (MB/s)

      // Получение предыдущих значений из кэша
      const last = lastStats[client.common_name];

      if (last) {
        // Вычисление времени между измерениями (в секундах)
        const dt = (now - last.timestamp) / 1000;

        // Расчет скорости: (новое значение - старое значение) / время / 1024 / 1024 = MB/s
        speed_rx = (client.bytes_received - last.rx) / dt / 1024 / 1024;
        speed_tx = (client.bytes_sent - last.tx) / dt / 1024 / 1024;
      }

      // Сохранение текущих значений в кэш для следующего расчета
      lastStats[client.common_name] = {
        rx: client.bytes_received,
        tx: client.bytes_sent,
        timestamp: now
      };

      // === ОБНОВЛЕНИЕ ДАННЫХ ГРАФИКА ===
      updateChartData(timeLabel, datasetMap, client.common_name, speed_rx, speed_tx);

      // === ОБРАБОТКА IP АДРЕСОВ ===
      // Приоритет отдается раздельным полям ipv4/ipv6, fallback на vpn_ip
      const ipv4Candidate = client.vpn_ipv4 ?? null;
      const ipv6Candidate = client.vpn_ipv6 ?? null;

      let vpnIPv4 = ipv4Candidate;
      let vpnIPv6 = ipv6Candidate;

      // Если раздельных полей нет, пытаемся определить тип из vpn_ip
      if (vpnIPv4 == null && vpnIPv6 == null && client.vpn_ip) {
        if (client.vpn_ip.includes(':')) {
          vpnIPv6 = client.vpn_ip;  // Содержит : → IPv6
        } else {
          vpnIPv4 = client.vpn_ip;  // Не содержит : → IPv4
        }
      }

      // Форматирование для отображения
      const displayIPv4 = vpnIPv4 ?? "";
      const displayIPv6 = vpnIPv6 && vpnIPv6.trim() ? vpnIPv6 : "—";

      // === ФОРМИРОВАНИЕ HTML СТРОКИ ТАБЛИЦЫ ===
      return `<tr>
        <td>${client.common_name}</td>
        <td>${displayIPv4}</td>
        <td>${displayIPv6}</td>
        <td>${client.real_ip}</td>
        <td>${client.port ?? ""}</td>
        <td>${client.connected_since}</td>
        <td>${client.time_online}</td>
        <td>${speed_rx.toFixed(2)} / ${speed_tx.toFixed(2)} MB/s</td>
        <td>${(client.bytes_received / 1024 / 1024).toFixed(2)} MB</td>
        <td>${(client.bytes_sent / 1024 / 1024).toFixed(2)} MB</td>
      </tr>`;
    }).join("");

    // === ОБНОВЛЕНИЕ DOM ===
    // Обновление тела таблицы клиентов
    $("#vpn-clients-body").html(rows);

    // Обновление итоговых значений в футере таблицы
    $("#total-received").text((total_received / 1024 / 1024).toFixed(2) + " MB");
    $("#total-sent").text((total_sent / 1024 / 1024).toFixed(2) + " MB");

    // Обновление графика
    refreshChart();
  });
}

// === МОДАЛЬНОЕ ОКНО: СПИСОК ВСЕХ КЛИЕНТОВ ===

/**
 * Отображает статусное сообщение в модальном окне списка клиентов
 *
 * @param {string} message - Текст сообщения
 * @param {Object} options - Опции отображения
 * @param {boolean} [options.spinner=false] - Показывать ли спиннер загрузки
 * @param {string} [options.tone='muted'] - Тон сообщения (muted, success, danger)
 */
function showClientsStatus(message, { spinner = false, tone = 'muted' } = {}) {
  const listEl = document.getElementById('clientsList');
  if (!listEl) return;

  // Определение CSS класса по тону
  const toneClass = tone === 'danger' ? 'text-danger' :
                    tone === 'success' ? 'text-success' :
                    'text-muted';

  // Экранирование HTML для безопасности
  const safeMessage = escapeHtml(message);

  // Формирование контента со спиннером или без
  const content = spinner
    ? `<div class="d-flex align-items-center justify-content-center gap-2">
         <div class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></div>
         <span>${safeMessage}</span>
       </div>`
    : safeMessage;

  listEl.innerHTML = `<div class="text-center py-3 ${toneClass}">${content}</div>`;
}

/**
 * Загружает сводную информацию о клиентах из API
 * Вызывается при открытии модального окна списка клиентов
 *
 * @async
 * @returns {Promise<void>}
 */
function fetchClientsSummary() {
  fetch('/api/clients/summary')
    .then(response => {
      if (!response.ok) {
        throw new Error('Ошибка загрузки');
      }
      return response.json();
    })
    .then(data => {
      // Валидация ответа
      if (!data || !Array.isArray(data.clients)) {
        throw new Error('Некорректный формат ответа');
      }

      // Сохранение данных в глобальной переменной
      clientsSummary = data.clients;

      // Отображение списка клиентов
      renderClientsList(clientsSummary);
    })
    .catch(error => {
      console.error('Ошибка загрузки сводки клиентов:', error);
      showClientsStatus('Не удалось загрузить список клиентов', { tone: 'danger' });
    });
}

/**
 * Отрисовывает список клиентов в модальном окне с accordion-интерфейсом
 *
 * @param {Array<Object>} clients - Массив объектов с данными о клиентах
 */
function renderClientsList(clients) {
  const listEl = document.getElementById('clientsList');
  if (!listEl) return;

  // Проверка на пустой список
  if (!Array.isArray(clients) || clients.length === 0) {
    showClientsStatus('Клиенты пока не подключались');
    return;
  }

  // Сортировка: сначала онлайн клиенты по алфавиту, затем офлайн по алфавиту
  const sortedClients = [...clients].sort((a, b) => {
    // Если статус отличается, онлайн идут первыми
    if (a.is_online !== b.is_online) {
      return b.is_online - a.is_online;
    }
    // Если статус одинаковый, сортируем по имени
    const nameA = (a.name || '').toLowerCase();
    const nameB = (b.name || '').toLowerCase();
    return nameA.localeCompare(nameB, 'ru');
  });

  // Формирование HTML для каждого клиента с accordion-структурой
  const itemsHtml = sortedClients.map((client, index) => {
    const name = client.name || 'Неизвестный';
    const statusClass = client.is_online ? 'status-dot-online' : 'status-dot-offline';

    // Уникальный ID для collapse-панели
    const collapseId = `collapse-client-${index}`;

    // Массив частей подзаголовка
    const subtitleParts = [];

    // Количество сессий
    if (typeof client.sessions === 'number' && client.sessions > 0) {
      const sessionWord = client.sessions === 1 ? 'сессия' : 'сессий';
      subtitleParts.push(`${client.sessions} ${sessionWord}`);
    }

    // Общее время подключения
    if (client.total_duration_human) {
      subtitleParts.push(`Всего: ${escapeHtml(client.total_duration_human)}`);
    }

    // Трафик
    if (typeof client.total_rx_gb === 'number' && typeof client.total_tx_gb === 'number') {
      subtitleParts.push(`Трафик: ${formatGb(client.total_rx_gb)} / ${formatGb(client.total_tx_gb)}`);
    }

    // Последняя активность
    if (client.last_seen) {
      subtitleParts.push(`Последний раз: ${escapeHtml(client.last_seen)}`);
    }

    const subtitle = subtitleParts.join(' · ');

    // Генерация детальной информации
    const detailsHtml = generateClientDetailsHTML(client);

    // Формирование HTML элемента списка с collapse-панелью
    return `
      <div class="list-group-item p-0">
        <button type="button"
                class="btn btn-link text-start text-decoration-none w-100 p-3 d-flex flex-column align-items-start gap-1 collapsed client-accordion-btn"
                data-bs-toggle="collapse"
                data-bs-target="#${collapseId}"
                aria-expanded="false"
                aria-controls="${collapseId}"
                data-client-name="${escapeHtml(name)}">
          <div class="d-flex align-items-center">
            <span class="status-dot ${statusClass}"></span>
            <span class="client-name">${escapeHtml(name)}</span>
          </div>
          ${subtitle ? `<div class="small text-muted client-subtitle">${subtitle}</div>` : ''}
        </button>
        <div id="${collapseId}" class="collapse" data-bs-parent="#clientsList">
          <div class="px-3 pb-3 border-top client-details-content">
            ${detailsHtml}
          </div>
        </div>
      </div>
    `;
  }).join('');

  listEl.innerHTML = itemsHtml;
}

// === МОДАЛЬНОЕ ОКНО: ДЕТАЛИ КЛИЕНТА ===

/**
 * Генерирует HTML с детальной информацией о клиенте
 * Используется для встраивания в collapse-панель
 *
 * @param {Object} client - Объект с данными о клиенте
 * @returns {string} HTML-строка с деталями клиента
 */
function generateClientDetailsHTML(client) {
  // === ОСНОВНАЯ ИНФОРМАЦИЯ ===
  const sessions = typeof client.sessions === 'number' ? client.sessions : 0;
  const totalTime = client.total_duration_human ? escapeHtml(client.total_duration_human) : '0:00:00';
  const lastSeen = client.last_seen ? escapeHtml(client.last_seen) : 'Неизвестно';
  const totalRx = formatGb(client.total_rx_gb);
  const totalTx = formatGb(client.total_tx_gb);

  // === ТЕКУЩАЯ СЕССИЯ (если клиент онлайн) ===
  let currentSessionHtml = '';

  if (client.current_session) {
    const session = client.current_session;
    const infoItems = [];

    // Время подключения
    const connectedSince = session.connected_since ? escapeHtml(session.connected_since) : 'Неизвестно';
    const timeOnline = session.time_online ? escapeHtml(session.time_online) : 'Неизвестно';
    infoItems.push(`<li><strong>Подключен с:</strong> ${connectedSince}</li>`);
    infoItems.push(`<li><strong>Время онлайн:</strong> ${timeOnline}</li>`);

    // IP адрес клиента
    if (session.ip) {
      const withPort = session.port ?
        `${escapeHtml(session.ip)}:${escapeHtml(session.port)}` :
        escapeHtml(session.ip);
      infoItems.push(`<li><strong>IP клиента:</strong> ${withPort}</li>`);
    }

    // VPN IP адреса
    if (session.vpn_ipv4) {
      infoItems.push(`<li><strong>VPN IPv4:</strong> ${escapeHtml(session.vpn_ipv4)}</li>`);
    }
    if (session.vpn_ipv6) {
      infoItems.push(`<li><strong>VPN IPv6:</strong> ${escapeHtml(session.vpn_ipv6)}</li>`);
    }
    if (!session.vpn_ipv4 && !session.vpn_ipv6 && session.vpn_ip) {
      infoItems.push(`<li><strong>VPN IP:</strong> ${escapeHtml(session.vpn_ip)}</li>`);
    }

    // Трафик текущей сессии
    infoItems.push(`<li><strong>Получено:</strong> ${formatGb(session.bytes_received_gb)}</li>`);
    infoItems.push(`<li><strong>Отправлено:</strong> ${formatGb(session.bytes_sent_gb)}</li>`);

    currentSessionHtml = `
      <div class="mt-3">
        <h6>Текущая сессия</h6>
        <ul class="list-unstyled mb-0">
          ${infoItems.join('')}
        </ul>
      </div>
    `;
  }

  // === ФОРМИРОВАНИЕ HTML ===
  return `
    <dl class="row mb-0">
      <dt class="col-sm-5">Сессий</dt>
      <dd class="col-sm-7">${sessions}</dd>

      <dt class="col-sm-5">Общее время подключения</dt>
      <dd class="col-sm-7">${totalTime}</dd>

      <dt class="col-sm-5">Данных получено</dt>
      <dd class="col-sm-7">${totalRx}</dd>

      <dt class="col-sm-5">Данных отправлено</dt>
      <dd class="col-sm-7">${totalTx}</dd>

      <dt class="col-sm-5">Последняя активность</dt>
      <dd class="col-sm-7">${lastSeen}</dd>
    </dl>
    ${currentSessionHtml}
  `;
}

/**
 * Отрисовывает детальную информацию о выбранном клиенте
 * Показывает модальное окно с подробной статистикой
 * (УСТАРЕВШАЯ ФУНКЦИЯ - оставлена для совместимости)
 *
 * @param {Object} client - Объект с данными о клиенте
 */
function renderClientDetails(client) {
  const titleEl = document.getElementById('clientDetailsTitle');
  const bodyEl = document.getElementById('clientDetailsBody');

  if (!titleEl || !bodyEl) return;

  // === ЗАГОЛОВОК МОДАЛЬНОГО ОКНА ===
  const name = client.name || 'Детали клиента';
  titleEl.textContent = name;

  const statusClass = client.is_online ? 'status-dot-online' : 'status-dot-offline';

  // === ФОРМИРОВАНИЕ HTML ТЕЛА МОДАЛЬНОГО ОКНА ===
  bodyEl.innerHTML = `
    <div class="d-flex align-items-center gap-2 mb-3">
      <span class="status-dot ${statusClass}"></span>
      <h5 class="mb-0">${escapeHtml(name)}</h5>
    </div>
    ${generateClientDetailsHTML(client)}
  `;

  // Показать модальное окно
  if (clientDetailsModalInstance) {
    clientDetailsModalInstance.show();
  }
}
