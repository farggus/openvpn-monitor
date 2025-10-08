/**
 * Графики трафика - Визуализация скорости передачи данных
 * Описание: Создание и обновление графиков Chart.js для отображения трафика клиентов
 */

// === ДОПОЛНИТЕЛЬНЫЕ ПЕРЕМЕННЫЕ ===
let currentChartMode = 'all'; // 'all' или 'individual'
let currentSelectedClient = null; // имя выбранного клиента для индивидуального графика
let chartStatistics = {}; // статистика для каждого клиента

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
 * Инициализирует или переинициализирует график трафика
 * Создает отдельные линии для входящего (Rx) и исходящего (Tx) трафика каждого клиента
 *
 * @param {Array<string>} users - Массив имен клиентов для отображения на графике
 * @param {string} mode - Режим отображения ('all' или 'individual')
 * @param {string} selectedClient - Имя выбранного клиента (для режима 'individual')
 */
function initializeChart(users, mode = 'all', selectedClient = null) {
  // Если график уже существует - уничтожаем его перед созданием нового
  if (chart) {
    chart.destroy();
  }

  // Сброс данных графика
  chartData = { labels: [], datasets: [] };

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

    chartData.datasets.push(
      // Линия входящего трафика (Receive)
      {
        label: `${user} ↓ Rx`,
        data: [],
        borderColor: colorScheme.primary,
        backgroundColor: colorScheme.gradient,
        fill: mode === 'individual', // Заливка только в индивидуальном режиме
        borderWidth: 2,
        tension: 0.4, // Сглаживание линии
        pointRadius: mode === 'individual' ? 3 : 0, // Точки только в индивидуальном режиме
        pointHoverRadius: 5
      },
      // Линия исходящего трафика (Transmit)
      {
        label: `${user} ↑ Tx`,
        data: [],
        borderColor: colorScheme.secondary,
        backgroundColor: colorScheme.gradient,
        fill: false,
        borderWidth: 2,
        borderDash: [5, 5],
        tension: 0.4,
        pointRadius: mode === 'individual' ? 3 : 0,
        pointHoverRadius: 5
      }
    );
  });

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
            enabled: true,
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
            grid: {
              color: 'rgba(0, 0, 0, 0.05)'
            },
            ticks: {
              callback: function(value) {
                return value.toFixed(2);
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
 * Добавляет новые точки данных и удаляет старые (сохраняет последние 20 значений)
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

    // Ограничение количества меток (максимум 20 последних точек)
    if (chartData.labels.length > 20) {
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
    datasetMap[rxDatasetName].push(speedRx);

    // Ограничение количества точек данных
    if (datasetMap[rxDatasetName].length > 20) {
      datasetMap[rxDatasetName].shift();
    }
  }

  // Обновление данных исходящего трафика (Tx)
  const txDatasetName = `${clientName} ↑ Tx`;
  if (datasetMap[txDatasetName]) {
    datasetMap[txDatasetName].push(speedTx);

    // Ограничение количества точек данных
    if (datasetMap[txDatasetName].length > 20) {
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
}
