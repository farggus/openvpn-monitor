/**
 * Карты - Отображение географического расположения клиентов
 * Описание: Работа с Leaflet картами для визуализации местоположения клиентов и сервера
 */

/**
 * Загружает маркеры клиентов и сервера на карту
 * Получает данные о местоположении из API и отображает их на интерактивной карте
 *
 * @async
 * @returns {Promise<void>}
 */
async function loadClientAndServerMarkers() {
  // Очистка существующих маркеров с карты
  mapMarkers.forEach(marker => mapInstance.removeLayer(marker));
  mapMarkers = [];

  // Массив координат для автоматического позиционирования карты
  const bounds = [];

  try {
    // === ЗАГРУЗКА МАРКЕРОВ КЛИЕНТОВ ===

    // Получение данных о клиентах из API
    const clientsRes = await fetch("/api/clients");
    const clientsData = await clientsRes.json();
    const clients = clientsData.clients || [];

    // Обработка каждого клиента
    for (const client of clients) {
      const clientName = client.common_name || 'unknown';
      const location = client.location;

      // Проверка наличия данных о местоположении
      if (location && location.latitude != null && location.longitude != null) {
        // Создание маркера на карте
        const marker = L.marker([location.latitude, location.longitude])
          .addTo(mapInstance)  // Добавление маркера на карту
          .bindPopup(          // Привязка всплывающего окна к маркеру
            `<strong>${clientName}</strong><br>${location.city || ''}, ${location.country || ''}`
          );

        // Сохранение ссылки на маркер для последующей очистки
        mapMarkers.push(marker);

        // Добавление координат в массив границ для автопозиционирования
        bounds.push([location.latitude, location.longitude]);
      }
    }

    // === ЗАГРУЗКА МАРКЕРА СЕРВЕРА ===
    // TODO: Добавить логику отображения сервера при необходимости

    // Автоматическое позиционирование карты по всем маркерам
    if (bounds.length) {
      // fitBounds подбирает масштаб и центр карты так, чтобы все маркеры были видны
      mapInstance.fitBounds(bounds, { padding: [30, 30] });
    }

  } catch (error) {
    console.error('Ошибка загрузки маркеров на карту:', error);
  }
}

/**
 * Добавляет один маркер на карту (устаревшая функция, оставлена для совместимости)
 * Рекомендуется использовать loadClientAndServerMarkers() вместо этого
 *
 * @deprecated
 * @param {Object} location - Объект с данными о местоположении
 * @param {number} location.latitude - Широта
 * @param {number} location.longitude - Долгота
 * @param {string} location.city - Город
 * @param {string} location.country_name - Название страны
 * @param {Object} client - Объект с данными о клиенте
 * @param {string} client.common_name - Имя клиента
 * @param {Array} bounds - Массив координат для границ карты
 */
function addMarker(location, client, bounds) {
  // Создание маркера на карте
  const marker = L.marker([location.latitude, location.longitude])
    .addTo(mapInstance)
    .bindPopup(`<strong>${client.common_name}</strong><br>${location.city}, ${location.country_name}`);

  // Сохранение маркера и обновление границ
  mapMarkers.push(marker);
  bounds.push([location.latitude, location.longitude]);

  // Автоматическое позиционирование карты
  mapInstance.fitBounds(bounds, { padding: [30, 30] });
}
