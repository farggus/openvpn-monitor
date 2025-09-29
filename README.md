# OpenVPN Monitor

## Обзор
OpenVPN Monitor — это веб-панель для наблюдения за активностью OpenVPN-сервера в реальном времени. Сервис собирает метрики из файла `status.log`, агрегирует историю подключений, сохраняет сводную статистику по клиентам и отображает данные в интерфейсе на Flask. UI построен на Bootstrap, содержит таблицу клиентов, модальные окна с историей сессий и карта с геолокацией IP-адресов, которую обновляет вспомогательная база.

## Архитектура и ключевые компоненты
| Компонент | Назначение | Артефакты |
|-----------|------------|-----------|
| Flask-приложение | Отдаёт веб-интерфейс и REST API (`/api/clients`, `/api/history`, `/api/server-status`, `/api/clients/summary`). | `app/routes.py`, `app/templates/index.html` |
| Конфигурационный слой | Загружает часовой пояс, пути к логам и JSON-файлам из переменных окружения, гарантирует создание каталогов и пустых JSON при первом запуске. | `app/config.py` |
| Парсер статуса | Потоково читает `status.log`, синхронно обновляет JSON с активными сессиями и историей, нормализует IPv4/IPv6, работает под файловой блокировкой и атомарно обновляет файлы. | `app/parser.py`, `logger.py` |
| Фоновый логгер | Запускает парсер в цикле каждые 10 секунд, чтобы UI получал свежие данные. | `logger.py`, `supervisord.conf` |
| База геолокаций | Поддерживает JSON-реестр IP-адресов и отметок first/last seen для построения карты. | `app/geo_store.py` |
| Скрипт статуса сервера | Сохраняет операционный статус OpenVPN (PID, локальный/публичный IP, пинг) в `server_status.json`; рекомендуется запускать из cron каждую минуту. | `scripts/server_status.sh`, `crontab` |
| Контейнеризация | Dockerfile ставит Python 3.12, зависимости, копирует код и включает `supervisord`, который поднимает одновременно API и логгер. Docker Compose монтирует логи OpenVPN и данные, содержит Traefik-лейблы. | `Dockerfile`, `docker-compose.yml`, `supervisord.conf` |

### Поток данных
1. OpenVPN сервер обновляет `status.log` (обычно `/var/log/openvpn/status.log`).
2. Контейнер (или локальный процесс) каждые 10 секунд запускает `parse_status_log()`, который:
   - считывает активных клиентов, маршрутную таблицу и вычисляет длительность сессий;
   - обновляет `active_sessions.json` и дописывает историю в `session_history.json` под блокировкой;
   - вычисляет сводную статистику, кэшируемую на время HTTP-запроса.
3. UI и API извлекают кэшированные данные и, при необходимости, пополняют базу геолокаций `client_geolocation.json`.
4. Отдельный cron на хосте обновляет `server_status.json`, чтобы `/api/server-status` показывал режим работы, локальный/публичный IP, пинг и аптайм.

## Предварительные требования
- Действующий OpenVPN-сервер с включённым выводом `status` (рекомендуется `status-version 3`) и доступом к файлу статуса на хосте.
- Linux-хост с Docker (24+) и Docker Compose v2, либо Python ≥3.11 при ручном запуске.
- Директория на хосте, куда будут сохраняться файлы состояния (`active_sessions.json`, `session_history.json`, `client_geolocation.json`, `server_status.json`).
- (Опционально) Traefik v2 в режиме reverse-proxy и внешняя сеть `proxy` для публикации панели.
- (Опционально) Интернет-доступ для скрипта `server_status.sh` для определения публичного IP.

## Прединсталляционные действия
1. **Настройка OpenVPN**
   - Убедитесь, что в конфигурации сервера `/etc/openvpn/server.conf` есть строки:
     ```
     status /var/log/openvpn/status.log
     status-version 3
     ```
   - Проверьте права доступа: пользователь Docker/службы должен читать `status.log`.
2. **Структура каталогов**
   #### По умолчанию веб-приложение устанавливается по пути `/var/www`, перейдите по этому пути и склонируйте репозиторий. После клонирования появится каталог `/var/www/openvpn-monitor`. Если желаете установить приложение по другому пути, то:  
   - Создайте (или перейдите) на хосте каталог, в него скопируйте репозиторий, например: `/home/app_data/openvpn-monitor`.
   - Внутри создайте подкаталог `/data` (в нем будут храниться данные мониторинга) и убедитесь, что он доступен для записи пользователю, от имени которого будет запускаться контейнер:
     ```bash
     sudo mkdir -p /home/app_data/openvpn-monitor/data
     sudo chown -R 1000:1000 /home/app_data/openvpn-monitor
     ```

## Установка и запуск (Docker Compose)
1. **Клонирование репозитория**
   ```bash
   cd /var/www
   git clone https://github.com/farggus/openvpn-monitor.git
   cd openvpn-monitor
   ```
2. **Структура каталогов**
   - Внутри `/openvpn-monitor` создайте подкаталог `/data` и убедитесь, что он доступен для записи пользователю, от имени которого будет запускаться контейнер:
     ```bash
     sudo mkdir -p /var/www/openvpn-monitor/data
     sudo chown -R 1000:1000 /var/www/openvpn-monitor
     ```
4. **Cron для статуса сервера**
   - Установите пакеты `curl`, `iproute2`, `dnsutils` (для `dig`).
     ```bash
     apt update
     apt install curl iproute2 dnsutils
     ```
   - Скопируйте `scripts/server_status.sh` на хост, сделайте исполняемым и поправьте путь вывода JSON, если директория отличается от `/var/www/openvpn-monitor/data`.
   - Добавьте задание cron (ежеминутно):
     ```cron
     * * * * * root /var/www/openvpn-monitor/scripts/server_status.sh
     ```
   - Убедитесь, что JSON обновляется:
     ```bash
     cat /var/www/openvpn-monitor/data/server_status.json
     ```
5. **Traefik (опционально)**
   - Если панель будет опубликована через Traefik, заранее создайте внешнюю сеть:
     ```bash
     docker network create proxy
     ```
   - Подготовьте TLS-сертификаты/авторизацию (Basic Auth) и откорректируйте лейблы в `docker-compose.yml`.



   
2. **Проверка переменных окружения**
   - При необходимости отредактируйте блок `environment` в `docker-compose.yml` (раскомментируйте и задайте свои пути/часовой пояс).
   - Доступные переменные:
     | Переменная | Назначение | Значение по умолчанию |
     |------------|------------|------------------------|
     | `OPENVPN_MONITOR_TZ` | Часовой пояс для расчёта длительности сессий. | `Europe/Bucharest` |
     | `OPENVPN_STATUS_LOG` | Путь к файлу статуса OpenVPN внутри контейнера. | `/var/log/openvpn/status.log` |
     | `OPENVPN_HISTORY_LOG` | JSON с историей сессий. | `/app/data/session_history.json` |
     | `OPENVPN_ACTIVE_SESSIONS` | JSON с активными сессиями. | `/app/data/active_sessions.json` |
     | `OPENVPN_SERVER_STATUS` | JSON со статусом сервера. | `/app/data/server_status.json` |
     | `OPENVPN_CLIENT_GEO_DB` | JSON с базой геолокаций. | `/app/data/client_geolocation.json` |
3. **Проброс томов**
   - Убедитесь, что в секции `volumes` проброшены:
     ```yaml
     - /var/log/openvpn:/var/log/openvpn:rw
     - ./data:/app/data:rw
     ```
     Первый том даёт доступ к `status.log`, второй — сохраняет состояние между перезапусками.
4. **Сборка и запуск**
   - Подразумевается, что Docker уже установлен на хост машине:
   ```bash
   docker compose up --build -d
   ```
   При сборке Dockerfile установит зависимости из `requirements.txt`, скопирует приложение и `logger.py`, затем запустит `supervisord`, который поднимет веб-сервер Flask и фонового логгера.
6. **Проверка состояния контейнера**
   ```bash
   docker compose logs -f
   ```
   Убедитесь, что видно сообщение `OpenVPN background logger started...` и нет ошибок чтения `status.log`.
7. **Доступ к UI**
   - Если Traefik настроен, откройте `https://<ваш-домен>`.
   - При прямом пробросе порта раскомментируйте `ports: - "5000:5000"` и зайдите на `http://<хост>:5000`.
8. **Удаление и переустановка**
   ```bash
   docker-compose down                # Удаление
   docker-compose build --no-cache    # Чистая сборка
   docker-compose up -d               # Установка
   ```
## Ручной запуск без Docker
1. **Подготовка окружения**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. **Переменные окружения**
   ```bash
   export OPENVPN_STATUS_LOG=/var/log/openvpn/status.log
   export OPENVPN_HISTORY_LOG=$(pwd)/data/session_history.json
   export OPENVPN_ACTIVE_SESSIONS=$(pwd)/data/active_sessions.json
   export OPENVPN_SERVER_STATUS=$(pwd)/data/server_status.json
   export OPENVPN_CLIENT_GEO_DB=$(pwd)/data/client_geolocation.json
   export OPENVPN_MONITOR_TZ=Europe/Moscow
   mkdir -p data
   ```
   Первичный запуск автоматически создаст пустые JSON-файлы.
3. **Запуск сервисов**
   - Способ 1: два терминала:
     ```bash
     flask --app app run --host 0.0.0.0 --port 5000
     ```
     ```bash
     python logger.py
     ```
   - Способ 2: использовать `supervisord`:
     ```bash
     pip install supervisor
     supervisord -c supervisord.conf
     ```
4. **Проверка**
   - Откройте браузер на `http://localhost:5000`.
   - Просмотрите файлы в `data/`, чтобы убедиться, что история и активные сессии обновляются.

## Постинсталляционные шаги
1. **Проверка данных**
   - Убедитесь, что в каталоге данных появились файлы `session_history.json`, `active_sessions.json`, `client_geolocation.json` и `server_status.json`.
   - Проверьте, что cron успел записать статус сервера (JSON не пустой).
2. **Настройка авторизации/HTTPS**
   - При использовании Traefik добавьте middleware с Basic Auth или иным методом аутентификации.
   - Настройте TLS-сертификат (Let’s Encrypt или собственный) для защищённого доступа.
3. **Мониторинг и алерты**
   - Добавьте проверку доступности `/api/server-status` в систему мониторинга.
   - Настройте сбор логов контейнера (stdout/stderr) в централизованное хранилище.
4. **Резервное копирование**
   - Включите `data/` каталог в регулярные бэкапы, чтобы не потерять историю подключений и кэш геолокаций.

## Эксплуатация и обновления
- Для обновления приложения:
  ```bash
  git pull
  docker compose build
  docker compose up -d
  ```
- При изменении структуры JSON-файлов рекомендуется остановить контейнер, сделать резервную копию `data/`, затем удалить устаревшие файлы — при старте они будут пересозданы автоматически конфигурационным модулем.
- Интервал парсинга (`time.sleep(10)`) можно изменить в `logger.py`, если требуется более частое/редкое обновление.

## API и полезные эндпоинты
| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/clients` | Текущие активные клиенты, включая трафик и IP-адреса. |
| GET | `/api/history` | История завершённых сессий, пригодна для построения отчётов. |
| GET | `/api/server-status` | Метаданные сервера: режим, аптайм, кол-во клиентов, трафик. |
| GET | `/api/clients/summary` | Сводка по клиентам (кол-во сессий, трафик, последний вход). |

API отдаёт JSON и может быть интегрирован с внешними системами (например, Prometheus экспортером или Slack-ботом).

## Проверка и разработка
- Для запуска тестов:
  ```bash
  pip install -r requirements-dev.txt
  pytest
  ```
- Статические анализаторы: `black` и `flake8` конфигурируются через `pyproject.toml`.
- При разработке удобно включать «горячий» перезапуск Flask (`flask run --debug`), однако в продакшне приложение запускается через `supervisord`, который обеспечивает перезапуск процессов при сбоях.

## Частые проблемы
| Симптом | Решение |
|---------|---------|
| В таблице клиентов пусто | Проверьте, что контейнер видит `/var/log/openvpn/status.log` и у него есть права чтения. |
| `/api/server-status` возвращает «Unknown» | Убедитесь, что cron запускает `server_status.sh` и путь вывода JSON совпадает с `OPENVPN_SERVER_STATUS`. |
| Не строится карта клиентов | Проверьте, что `client_geolocation.json` доступен для записи. Для наполнения координат можно дополнительно интегрировать внешние сервисы геолокации. |
| Ошибки `UnknownTimeZoneError` | Проверьте значение `OPENVPN_MONITOR_TZ` — оно должно соответствовать базе IANA (например, `Europe/Moscow`). |

Следуя инструкции, вы сможете развернуть OpenVPN Monitor «с нуля», интегрировать его с существующим OpenVPN-сервером и обеспечить наблюдаемость за подключениями.
