/**
 * Графики трафика - Визуализация скорости передачи данных
 * Описание: Создание и обновление графиков Chart.js для отображения трафика клиентов
 */

/**
 * Инициализирует или переинициализирует график трафика
 * Создает отдельные линии для входящего (Rx) и исходящего (Tx) трафика каждого клиента
 *
 * @param {Array<string>} users - Массив имен клиентов для отображения на графике
 */
function initializeChart(users) {
  // Если график уже существует - уничтожаем его перед созданием нового
  if (chart) {
    chart.destroy();
  }

  // Сброс данных графика
  chartData = { labels: [], datasets: [] };

  // Палитра цветов для линий графика
  const colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown'];

  // Создание наборов данных для каждого клиента
  // Для каждого клиента создается 2 линии: Rx (сплошная) и Tx (пунктирная)
  users.forEach((user, i) => {
    chartData.datasets.push(
      // Линия входящего трафика (Receive)
      {
        label: `${user} Rx`,                    // Метка на легенде
        data: [],                               // Пустой массив данных (заполнится при обновлении)
        borderColor: colors[i % colors.length], // Цвет линии из палитры
        fill: false                             // Не заливать область под линией
      },
      // Линия исходящего трафика (Transmit)
      {
        label: `${user} Tx`,                         // Метка на легенде
        data: [],                                    // Пустой массив данных
        borderColor: colors[(i + 1) % colors.length], // Другой цвет из палитры
        borderDash: [5, 5],                          // Пунктирная линия (5px линия, 5px пробел)
        fill: false                                  // Не заливать область под линией
      }
    );
  });

  // Проверяем, что canvas элемент доступен (модальное окно графика открыто)
  if (chartCanvas) {
    // Создание экземпляра Chart.js
    chart = new Chart(chartCanvas, {
      type: 'line',          // Тип графика - линейный
      data: chartData,       // Данные для отображения
      options: {
        responsive: true,    // Адаптивный размер графика
        animation: false     // Отключение анимации для повышения производительности
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
      chartData.labels.shift(); // Удаляем самую старую метку
    }
  }

  // Обновление данных входящего трафика (Rx)
  const rxDatasetName = `${clientName} Rx`;
  if (datasetMap[rxDatasetName]) {
    datasetMap[rxDatasetName].push(speedRx);

    // Ограничение количества точек данных
    if (datasetMap[rxDatasetName].length > 20) {
      datasetMap[rxDatasetName].shift(); // Удаляем самую старую точку
    }
  }

  // Обновление данных исходящего трафика (Tx)
  const txDatasetName = `${clientName} Tx`;
  if (datasetMap[txDatasetName]) {
    datasetMap[txDatasetName].push(speedTx);

    // Ограничение количества точек данных
    if (datasetMap[txDatasetName].length > 20) {
      datasetMap[txDatasetName].shift(); // Удаляем самую старую точку
    }
  }
}

/**
 * Принудительно перерисовывает график
 * Вызывается после обновления всех данных
 */
function refreshChart() {
  if (chart) {
    chart.update(); // Метод Chart.js для обновления отображения
  }
}
