/**
 * Сервер - Управление статусом сервера OpenVPN
 * Описание: Загружает и отображает информацию о состоянии сервера
 */

/**
 * Загружает статус сервера OpenVPN из API и обновляет таблицу
 * Вызывается периодически для обновления информации в реальном времени
 *
 * Информация о сервере включает:
 * - Режим работы VPN (mode)
 * - Статус сервера (status)
 * - Доступность по ping (pingable)
 * - Количество подключенных клиентов (clients)
 * - Общий трафик входящий/исходящий (total_rx/total_tx)
 * - Время работы (uptime)
 * - Локальный и публичный IP адреса
 *
 * @async
 * @returns {Promise<void>}
 */
function fetchServerStatus() {
  // Запрос к API статуса сервера
  fetch("/api/server-status")
    .then(response => response.json())  // Парсинг JSON ответа
    .then(data => {
      // Формирование HTML строки таблицы с данными сервера
      const row = `<tr>
        <td>${data.mode}</td>
        <td>${data.status}</td>
        <td>${data.pingable}</td>
        <td>${data.clients}</td>
        <td>${data.total_rx} MB</td>
        <td>${data.total_tx} MB</td>
        <td>${formatUptime(data.uptime)}</td>
        <td>${data.local_ip}</td>
        <td>${data.public_ip}</td>
      </tr>`;

      // Обновление содержимого tbody таблицы статуса сервера
      document.getElementById("server-status-body").innerHTML = row;
    })
    .catch(error => {
      // Обработка ошибок при загрузке данных
      console.error("Ошибка загрузки статуса сервера:", error);

      // Отображение сообщения об ошибке в таблице
      document.getElementById("server-status-body").innerHTML = `
        <tr>
          <td colspan="9" class="text-center text-danger">
            Ошибка загрузки данных сервера
          </td>
        </tr>
      `;
    });
}
