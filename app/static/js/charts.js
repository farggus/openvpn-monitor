/**
 * Графики трафика - Визуализация скорости передачи данных
 * Описание: Создание и обновление графиков Chart.js для отображения трафика клиентов
 */

// === ДОПОЛНИТЕЛЬНЫЕ ПЕРЕМЕННЫЕ ===
let currentChartMode = 'all'; // 'all' или 'individual'
let currentSelectedClient = null; // имя выбранного клиента для индивидуального графика
let chartStatistics = {}; // статистика для каждого клиента
let currentPeriod = 30; // текущий период в минутах
let historicalDataLoaded = false; // флаг загрузки исторических данных
let hideZeroValues = true; // скрывать нулевые значения Rx/Tx (активно по умолчанию)
let showDetailedMode = false; // режим подробного отображения (false = усредненный, max 40 точек)

/**
 * Расширенная палитра цветов для графиков
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
 * Создает градиент для заливки области под графиком
 * @param {CanvasRenderingContext2D} ctx - Контекст canvas
 * @param {string} color - Цвет градиента
 * @returns {CanvasGradient} Градиент для заливки
 */
function createGradient(ctx, color) {
  const gradient = ctx.createLinearGradient(0, 0, 0, 400);
  gradient.addColorStop(0, color);
  gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');
  return gradient;
}

/**
 * Загружает исторические данные метрик трафика из API
 * @param {number} period - Период в минутах
 * @param {string|null} clientName - Имя клиента (опционально)
 * @returns {Promise<Object>} Промис с данными метрик
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
 * Фильтрует нулевые значения, заменяя их на null для разрывов в графике
 * @param {number} value - Значение для проверки
 * @returns {number|null} Исходное значение или null если нужно скрыть ноль
 */
function filterZeroValue(value) {
  if (hideZeroValues && value === 0) {
    return null;
  }
  return value;
}

/**
 * Агрегирует данные до максимум 40 точек, усредняя значения
 * @param {Array} labels - Массив меток времени
 * @param {Array} data - Массив значений данных
 * @returns {Object} Объект с агрегированными labels и data
 */
function aggregateDataPoints(labels, data) {
  const maxPoints = 40;

  if (labels.length <= maxPoints) {
    // Если точек меньше или равно 40, возвращаем как есть
    return { labels, data };
  }

  // Рассчитываем размер группы для агрегации
  const groupSize = Math.ceil(labels.length / maxPoints);
  const aggregatedLabels = [];
  const aggregatedData = [];

  for (let i = 0; i < labels.length; i += groupSize) {
    const group = data.slice(i, i + groupSize);

    // Берем среднюю метку времени из группы (центральную)
    const middleIndex = i + Math.floor(groupSize / 2);
    aggregatedLabels.push(labels[Math.min(middleIndex, labels.length - 1)]);

    // Усредняем значения, игнорируя null
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
 * Преобразует исторические данные в формат для Chart.js
 * @param {Object} metricsData - Данные метрик из API
 * @returns {Object} Объект с метками времени и данными наборов
 */
function processHistoricalData(metricsData) {
  const allTimestamps = new Set();
  const clientData = {};

  // Собираем все метки времени и данные для каждого клиента
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

  // Сортируем метки времени
  const sortedTimestamps = Array.from(allTimestamps).sort();

  // Форматируем метки времени для отображения
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
 * Инициализирует или переинициализирует график трафика с историческими данными
 * @param {Array<string>} users - Массив имен клиентов для отображения на графике
 * @param {string} mode - Режим отображения ('all' или 'individual')
 * @param {string} selectedClient - Имя выбранного клиента (для режима 'individual')
 * @param {Object|null} historicalData - Исторические данные (опционально)
 */
async function initializeChart(users, mode = 'all', selectedClient = null, historicalData = null) {
  // Если график уже существует - уничтожаем его перед созданием нового
  if (chart) {
    chart.destroy();
  }

  // Сброс данных графика
  chartData = { labels: [], datasets: [] };

  // Если есть исторические данные, загружаем их
  if (!historicalData) {
    const clientToLoad = mode === 'individual' ? selectedClient : null;
    const metricsData = await loadHistoricalMetrics(currentPeriod, clientToLoad);
    historicalData = processHistoricalData(metricsData);
  }

  // Заполняем график историческими данными
  if (historicalData && historicalData.labels.length > 0) {
    // В режиме усреднения (showDetailedMode = false) агрегируем данные
    if (!showDetailedMode) {
      const aggregated = aggregateDataPoints(historicalData.labels, historicalData.labels);
      chartData.labels = aggregated.labels;
      // Сохраняем информацию об агрегации для использования при обработке datasets
      historicalData.isAggregated = true;
      historicalData.aggregatedLabels = aggregated.labels;
    } else {
      chartData.labels = historicalData.labels;
      historicalData.isAggregated = false;
    }
  }

  // Инициализация статистики для клиентов
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

  // Определяем, каких клиентов отображать
  const displayUsers = mode === 'individual' && selectedClient
    ? [selectedClient]
    : users;

  // Создание наборов данных для каждого клиента
  displayUsers.forEach((user, i) => {
    const colorScheme = CHART_COLORS[i % CHART_COLORS.length];

    // Подготовка исторических данных для этого клиента
    const rxData = [];
    const txData = [];

    if (historicalData && historicalData.clientData && historicalData.clientData[user]) {
      const clientHistData = historicalData.clientData[user];

      // Заполняем данные для каждой метки времени
      historicalData.timestamps.forEach(timestamp => {
        const rxVal = clientHistData.rx[timestamp];
        const txVal = clientHistData.tx[timestamp];

        // Применяем фильтрацию (null уже может быть установлен в processHistoricalData)
        rxData.push(rxVal !== undefined && rxVal !== null ? rxVal : filterZeroValue(0));
        txData.push(txVal !== undefined && txVal !== null ? txVal : filterZeroValue(0));

        // Обновляем статистику (используем реальные значения, не null)
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

      // Текущие значения - последние в массиве
      if (rxData.length > 0) {
        chartStatistics[user].currentRx = rxData[rxData.length - 1];
        chartStatistics[user].currentTx = txData[txData.length - 1];
      }

      // Применяем агрегацию в режиме неподробного отображения
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
      // Линия входящего трафика (Receive)
      {
        label: `${user} ↓ Rx`,
        data: rxData,
        borderColor: colorScheme.primary,
        backgroundColor: colorScheme.gradient,
        fill: mode === 'individual', // Заливка только в индивидуальном режиме
        borderWidth: 2,
        tension: 0.4, // Сглаживание линии
        pointRadius: mode === 'individual' ? 3 : 0, // Точки только в индивидуальном режиме
        pointHoverRadius: 5,
        spanGaps: true // Не прерывать линию на null значениях
      },
      // Линия исходящего трафика (Transmit)
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
        spanGaps: true // Не прерывать линию на null значениях
      }
    );
  });

  // Вычисляем максимальное значение для динамической шкалы Y
  let maxValue = 0.5; // Минимальная шкала по умолчанию
  chartData.datasets.forEach(dataset => {
    if (dataset.data && dataset.data.length > 0) {
      const dataMax = Math.max(...dataset.data.filter(v => v !== null && v !== undefined));
      if (dataMax > maxValue) {
        maxValue = dataMax;
      }
    }
  });

  // Округляем вверх до ближайшего 0.1
  maxValue = Math.ceil(maxValue * 10) / 10;

  // Убеждаемся, что минимум 0.5
  if (maxValue < 0.5) {
    maxValue = 0.5;
  }

  // Проверяем, что canvas элемент доступен (модальное окно графика открыто)
  if (chartCanvas) {
    const ctx = chartCanvas.getContext('2d');

    // Создание экземпляра Chart.js с улучшенными настройками
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
            enabled: showDetailedMode, // Отключаем tooltips в режиме усреднения
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
                      `Пик Rx: ${stats.peakRx.toFixed(3)} MB/s`,
                      `Пик Tx: ${stats.peakTx.toFixed(3)} MB/s`,
                      `Средняя Rx: ${stats.avgRx.toFixed(3)} MB/s`,
                      `Средняя Tx: ${stats.avgTx.toFixed(3)} MB/s`
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
              text: 'Время',
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
              text: 'Скорость (MB/s)',
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
 * Обновляет данные графика новыми значениями скорости передачи
 * Добавляет новые точки данных в реальном времени
 *
 * @param {string} timeLabel - Метка времени для оси X (например, "14:30:25")
 * @param {Object} datasetMap - Карта наборов данных {имя_набора: массив_данных}
 * @param {string} clientName - Имя клиента
 * @param {number} speedRx - Скорость входящего трафика в MB/s
 * @param {number} speedTx - Скорость исходящего трафика в MB/s
 */
function updateChartData(timeLabel, datasetMap, clientName, speedRx, speedTx) {
  // Добавление новой метки времени на ось X
  if (chartData.labels) {
    chartData.labels.push(timeLabel);

    // Удаляем старые точки, которые выходят за пределы текущего периода
    // Рассчитываем максимальное количество точек на основе периода
    // При обновлении каждые 10 секунд: 30 мин = 180 точек, 1 час = 360 точек и т.д.
    const maxPoints = (currentPeriod * 60) / 10;

    if (chartData.labels.length > maxPoints) {
      chartData.labels.shift();
    }
  }

  // Обновление статистики клиента
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

  // Обновление данных входящего трафика (Rx)
  const rxDatasetName = `${clientName} ↓ Rx`;
  if (datasetMap[rxDatasetName]) {
    // Применяем фильтрацию нулевых значений
    datasetMap[rxDatasetName].push(filterZeroValue(speedRx));

    // Удаляем старые точки на основе текущего периода
    const maxPoints = (currentPeriod * 60) / 10;
    if (datasetMap[rxDatasetName].length > maxPoints) {
      datasetMap[rxDatasetName].shift();
    }
  }

  // Обновление данных исходящего трафика (Tx)
  const txDatasetName = `${clientName} ↑ Tx`;
  if (datasetMap[txDatasetName]) {
    // Применяем фильтрацию нулевых значений
    datasetMap[txDatasetName].push(filterZeroValue(speedTx));

    // Удаляем старые точки на основе текущего периода
    const maxPoints = (currentPeriod * 60) / 10;
    if (datasetMap[txDatasetName].length > maxPoints) {
      datasetMap[txDatasetName].shift();
    }
  }
}

/**
 * Обновляет отображение статистики на странице
 * @param {string} clientName - Имя клиента (null для общей статистики)
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
    // Суммируем статистику всех клиентов
    Object.values(chartStatistics).forEach(stats => {
      totalCurrentRx += stats.currentRx;
      totalCurrentTx += stats.currentTx;
      totalPeakRx = Math.max(totalPeakRx, stats.peakRx);
      totalPeakTx = Math.max(totalPeakTx, stats.peakTx);
    });
  }

  // Обновляем DOM элементы
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
 * Принудительно перерисовывает график
 * Вызывается после обновления всех данных
 */
function refreshChart() {
  if (chart) {
    chart.update();

    // Обновляем статистику
    if (currentChartMode === 'individual' && currentSelectedClient) {
      updateChartStatistics(currentSelectedClient);
    } else {
      updateChartStatistics();
    }
  }
}

/**
 * Обрабатывает переключение режима отображения графика
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

      // Заполняем селект клиентами, если еще не заполнен
      if (clientSelect.options.length <= 1) {
        // Получаем список клиентов из lastStats
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

    // Переинициализируем график
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

  // Обработчики фильтров периодов
  const periodRadios = document.querySelectorAll('input[name="chartPeriod"]');
  periodRadios.forEach(radio => {
    radio.addEventListener('change', (e) => {
      currentPeriod = parseInt(e.target.value, 10);

      // Переинициализируем график с новым периодом
      const users = Object.keys(lastStats);
      if (users.length > 0) {
        initializeChart(users, currentChartMode, currentSelectedClient);
      }
    });
  });

  // Обработчик чекбокса скрытия нулевых значений
  const hideZeroCheckbox = document.getElementById('hideZeroValues');
  if (hideZeroCheckbox) {
    hideZeroCheckbox.addEventListener('change', (e) => {
      hideZeroValues = e.target.checked;

      // Переинициализируем график с новой настройкой
      const users = Object.keys(lastStats);
      if (users.length > 0) {
        initializeChart(users, currentChartMode, currentSelectedClient);
      }
    });
  }

  // Обработчик чекбокса режима подробного отображения
  const showDetailedCheckbox = document.getElementById('showDetailedMode');
  if (showDetailedCheckbox) {
    showDetailedCheckbox.addEventListener('change', (e) => {
      showDetailedMode = e.target.checked;

      // Переинициализируем график с новым режимом
      const users = Object.keys(lastStats);
      if (users.length > 0) {
        initializeChart(users, currentChartMode, currentSelectedClient);
      }
    });
  }
}
