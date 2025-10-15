# ПЛАН ОЧИСТКИ ПРОЕКТА ПОСЛЕ АУДИТА
**Дата:** 14 октября 2025
**Основано на:** PROJECT_AUDIT_OCT_2025.md

---

## ПРЕДВАРИТЕЛЬНАЯ ОЦЕНКА

**Время выполнения:** ~30 минут
**Уровень риска:** Низкий (удаляются только неиспользуемые файлы)
**Требуется:** Git, Docker, текстовый редактор

---

## ШАГ 0: ПОДГОТОВКА И РЕЗЕРВНОЕ КОПИРОВАНИЕ

### 0.1. Создать резервную копию текущего состояния

```bash
# Создать бэкап всего проекта
cd /home/app_data/docker/openvpn-monitor
tar -czf ../openvpn-monitor-backup-$(date +%Y%m%d-%H%M%S).tar.gz .

# Проверить, что бэкап создан
ls -lh ../openvpn-monitor-backup-*.tar.gz
```

**Ожидаемый результат:**
```
-rw-rw-r-- 1 user user 2.5M окт 14 18:00 openvpn-monitor-backup-20251014-180000.tar.gz
```

### 0.2. Убедиться, что все изменения закоммичены

```bash
# Проверить статус Git
git status

# Если есть незакоммиченные изменения - закоммитить их
git add .
git commit -m "Состояние перед очисткой проекта"
```

**Ожидаемый результат:**
```
On branch main
nothing to commit, working tree clean
```

### 0.3. Создать новую ветку для очистки (опционально, но рекомендуется)

```bash
# Создать ветку для изменений
git checkout -b cleanup/project-audit-oct2025

# Проверить текущую ветку
git branch
```

**Ожидаемый результат:**
```
* cleanup/project-audit-oct2025
  main
```

---

## ШАГ 1: УДАЛЕНИЕ УСТАРЕВШИХ ФАЙЛОВ (Приоритет: ВЫСОКИЙ)

### 1.1. Удалить устаревшие скрипты сбора статуса

```bash
# Удалить bash-скрипт
rm scripts/server_status.sh

# Удалить Python-скрипт (хостовая версия)
rm scripts/server_status.py

# Удалить файл crontab
rm crontab

# Проверить, что файлы удалены
ls scripts/
ls crontab 2>&1 || echo "✓ crontab удален"
```

**Ожидаемый результат:**
```
ls: cannot access 'crontab': No such file or directory
✓ crontab удален

scripts/:
openvpn-install.sh
__pycache__
```

### 1.2. Очистить __pycache__ в scripts/ (необязательно)

```bash
# Удалить скомпилированные Python файлы
rm -rf scripts/__pycache__

# Проверка
ls scripts/
```

**Ожидаемый результат:**
```
scripts/:
openvpn-install.sh
```

---

## ШАГ 2: АРХИВИРОВАНИЕ МИГРАЦИОННЫХ СКРИПТОВ (Приоритет: СРЕДНИЙ)

### 2.1. Создать директорию для архива

```bash
# Создать директорию archive/migrations
mkdir -p archive/migrations

# Проверить создание
ls -la archive/
```

**Ожидаемый результат:**
```
drwxrwxr-x 2 user user 4096 окт 14 18:05 migrations
```

### 2.2. Переместить миграционные скрипты

```bash
# Переместить скрипты в архив
mv migrate_close_sessions.py archive/migrations/
mv test_refactoring.py archive/migrations/

# Проверить перемещение
ls archive/migrations/
ls migrate_close_sessions.py 2>&1 || echo "✓ migrate_close_sessions.py перемещен"
ls test_refactoring.py 2>&1 || echo "✓ test_refactoring.py перемещен"
```

**Ожидаемый результат:**
```
archive/migrations/:
migrate_close_sessions.py
test_refactoring.py

✓ migrate_close_sessions.py перемещен
✓ test_refactoring.py перемещен
```

### 2.3. Добавить README в archive/migrations/

```bash
cat > archive/migrations/README.md << 'EOF'
# Migration Scripts Archive

This directory contains one-time migration scripts that have been successfully executed.

## Scripts

### migrate_close_sessions.py
- **Date executed:** 2025-10-13
- **Purpose:** Close 110 incomplete sessions in session_history.json
- **Result:** Successfully closed all incomplete sessions
- **Documentation:** See REFACTORING_SUMMARY.md

### test_refactoring.py
- **Date executed:** 2025-10-13
- **Purpose:** Validate refactoring results (no incomplete sessions, correct parser.py structure)
- **Result:** All tests passed
- **Documentation:** See REFACTORING_SUMMARY.md

## Note

These scripts are kept for historical reference only and should NOT be run again.
EOF

# Проверить создание
cat archive/migrations/README.md
```

---

## ШАГ 3: ОБНОВЛЕНИЕ REQUIREMENTS.TXT (Приоритет: ВЫСОКИЙ)

### 3.1. Удалить psutil из requirements.txt

```bash
# Показать текущее содержимое
echo "=== ДО ==="
cat requirements.txt

# Удалить строку с psutil
sed -i '/^psutil$/d' requirements.txt

# Показать новое содержимое
echo ""
echo "=== ПОСЛЕ ==="
cat requirements.txt
```

**Ожидаемый результат:**
```
=== ДО ===
flask
flask-babel
pytz
psutil
requests

=== ПОСЛЕ ===
flask
flask-babel
pytz
requests
```

### 3.2. Проверить валидность requirements.txt

```bash
# Попробовать установить зависимости в виртуальном окружении (опционально)
# python3 -m venv test_env
# source test_env/bin/activate
# pip install -r requirements.txt
# deactivate
# rm -rf test_env
```

---

## ШАГ 4: ОЧИСТКА .GITIGNORE (Приоритет: СРЕДНИЙ)

### 4.1. Удалить CLAUDE.md из .gitignore

```bash
# Показать текущее содержимое
echo "=== ДО ==="
tail -5 .gitignore

# Удалить строку CLAUDE.md
sed -i '/^CLAUDE\.md$/d' .gitignore

# Показать новое содержимое
echo ""
echo "=== ПОСЛЕ ==="
tail -5 .gitignore
```

**Ожидаемый результат:**
```
=== ДО ===
# Application runtime data
data/

# Files
CLAUDE.md

=== ПОСЛЕ ===
# Application runtime data
data/
```

---

## ШАГ 5: ОЧИСТКА DOCKER-COMPOSE.YML (Приоритет: НИЗКИЙ)

### 5.1. Удалить закомментированные строки аутентификации

```bash
# Создать резервную копию
cp docker-compose.yml docker-compose.yml.bak

# Показать строки для удаления
echo "=== Строки для удаления ==="
grep -n "openvpn-auth.basicauth.users" docker-compose.yml | grep "^#"

# Удалить закомментированные строки (19-20, 22)
sed -i '/#.*openvpn-auth.basicauth.users.*scuruci/d' docker-compose.yml
sed -i '/#.*openvpn-auth.basicauth.users.*openvpn.*scuruci/d' docker-compose.yml

# Проверить результат
echo ""
echo "=== После очистки ==="
grep -A2 -B2 "openvpn-user-auth" docker-compose.yml
```

**Ожидаемый результат:**
```
=== Строки для удаления ===
19:#      - "traefik.http.middlewares.openvpn-auth.basicauth.users=scuruci:$$apr1$$x.lN5PaD$$bKTbjAv.Z0KLTKA.VMFNp/" # Auth
20:#      - "traefik.http.middlewares.openvpn-auth.basicauth.users=openvpn:$$apr1$$AxHp9Acv$$so9EImC8Jv7YULdyknjHQ., scuruci:$$apr1$$x.lN5PaD$$bKTbjAv.Z0KLTKA.VMFNp/"

=== После очистки ===
      # NEW: local middleware
      - "traefik.http.middlewares.openvpn-user-auth.basicauth.users=openvpn:$$apr1$$AxHp9Acv$$so9EImC8Jv7YULdyknjHQ."
      # attach it to https router
```

### 5.2. Добавить комментарий в .env.example (опционально)

```bash
# Добавить пример Basic Auth в .env.example
cat >> .env.example << 'EOF'

# Optional: Traefik Basic Authentication
# Generate with: htpasswd -nb username password
# Example:
# TRAEFIK_AUTH_USERS=username:$$apr1$$xxxxxxxx$$yyyyyyyyyyyyyyyy
EOF

# Проверить
tail -5 .env.example
```

---

## ШАГ 6: ОБНОВЛЕНИЕ ДОКУМЕНТАЦИИ

### 6.1. Обновить CLAUDE.md - упомянуть об удалении старых скриптов

```bash
# Открыть CLAUDE.md в редакторе
nano CLAUDE.md

# ИЛИ добавить секцию автоматически:
cat >> CLAUDE.md << 'EOF'

## Archived Files

The following files have been moved to `archive/` after successful completion:

- `archive/migrations/migrate_close_sessions.py` - Migration script (executed 2025-10-13)
- `archive/migrations/test_refactoring.py` - Refactoring validation (executed 2025-10-13)

The following legacy files have been removed (replaced by `app/server_status_collector.py`):

- `scripts/server_status.sh` - Legacy bash script with cron
- `scripts/server_status.py` - Legacy Python script with cron
- `crontab` - Cron configuration (no longer needed)

See `PROJECT_AUDIT_OCT_2025.md` for details.
EOF
```

### 6.2. Обновить README.md (если есть упоминания crontab)

```bash
# Проверить, есть ли упоминания crontab
grep -n "cron" README.md || echo "✓ Упоминаний cron в README.md нет"
```

**Если найдены упоминания - удалить их вручную**

---

## ШАГ 7: ДОБАВЛЕНИЕ archive/ В .GITIGNORE (опционально)

### 7.1. Решить, нужен ли archive/ в репозитории

**Вариант A:** Добавить в Git (рекомендуется для истории)
```bash
# Добавить archive/ в Git
git add archive/
```

**Вариант B:** Исключить из Git (если не нужен в репозитории)
```bash
# Добавить в .gitignore
echo "" >> .gitignore
echo "# Archived migration scripts" >> .gitignore
echo "archive/" >> .gitignore
```

---

## ШАГ 8: КОММИТ ИЗМЕНЕНИЙ В GIT

### 8.1. Просмотреть все изменения

```bash
# Показать статус
git status

# Показать детали изменений
git diff
```

### 8.2. Добавить удаленные файлы в коммит

```bash
# Добавить все изменения
git add -A

# Или добавить по одному:
git add requirements.txt
git add .gitignore
git add docker-compose.yml
git add CLAUDE.md
git add archive/

# Просмотреть что будет закоммичено
git status
```

### 8.3. Создать коммит

```bash
# Коммит с подробным сообщением
git commit -m "Очистка проекта после аудита (октябрь 2025)

Удалены устаревшие файлы:
- scripts/server_status.sh (заменен на app/server_status_collector.py)
- scripts/server_status.py (заменен на app/server_status_collector.py)
- crontab (больше не используется)

Архивированы выполненные миграции:
- migrate_close_sessions.py -> archive/migrations/
- test_refactoring.py -> archive/migrations/

Обновлены зависимости:
- Удален неиспользуемый пакет psutil из requirements.txt

Очистка конфигурации:
- Удалена строка CLAUDE.md из .gitignore
- Удалены закомментированные строки из docker-compose.yml

См. PROJECT_AUDIT_OCT_2025.md для деталей."
```

### 8.4. Просмотреть коммит

```bash
# Показать последний коммит
git log -1 --stat

# Показать детали
git show
```

---

## ШАГ 9: ПЕРЕСБОРКА DOCKER-ОБРАЗА

### 9.1. Остановить текущий контейнер

```bash
# Остановить и удалить контейнер
docker compose down

# Проверить, что контейнер остановлен
docker ps | grep openvpn-admin || echo "✓ Контейнер остановлен"
```

### 9.2. Пересобрать образ без кеша

```bash
# Пересобрать образ (без psutil теперь)
docker compose build --no-cache

# Проверить размер нового образа
docker images | grep openvpn-monitor
```

**Ожидаемый результат:** Размер образа должен уменьшиться (без psutil)

### 9.3. Запустить обновленный контейнер

```bash
# Запустить контейнер
docker compose up -d

# Проверить статус
docker compose ps
```

**Ожидаемый результат:**
```
NAME                 IMAGE                      STATUS
openvpn-admin        openvpn-monitor-openvpn-admin   Up 5 seconds
```

---

## ШАГ 10: ТЕСТИРОВАНИЕ

### 10.1. Проверить логи контейнера

```bash
# Показать логи (последние 50 строк)
docker compose logs --tail=50

# Следить за логами в реальном времени
docker compose logs -f
```

**Ожидаемые строки:**
```
openvpn-admin  | OpenVPN background logger started...
openvpn-admin  | Initializing server status...
openvpn-admin  | Server status initialized successfully
```

**НЕ должно быть:**
```
ModuleNotFoundError: No module named 'psutil'
```

### 10.2. Проверить API endpoints

```bash
# Проверить server status
curl -s http://localhost:5000/api/server-status | jq '.'

# Проверить clients
curl -s http://localhost:5000/api/clients | jq '.'

# Проверить view counter
curl -s http://localhost:5000/api/view-counter | jq '.'
```

**Ожидаемый результат:** JSON-ответы без ошибок

### 10.3. Проверить обновление server_status.json

```bash
# Показать текущий server_status.json
cat data/server_status.json | jq '.'

# Подождать 60 секунд и проверить снова (должен обновиться)
sleep 65
cat data/server_status.json | jq '.uptime'
```

**Ожидаемый результат:** Файл обновляется каждые 60 секунд

### 10.4. Проверить traffic_metrics.json

```bash
# Показать последние метрики
cat data/traffic_metrics.json | jq '.'

# Проверить, что собираются данные каждые 10 секунд
watch -n 5 'cat data/traffic_metrics.json | jq "." | tail -20'
```

### 10.5. Открыть веб-интерфейс

```bash
# Если используется прямой порт (без Traefik)
xdg-open http://localhost:5000

# Или проверить через curl
curl -I http://localhost:5000/
```

**Ожидаемый результат:** HTTP 200 OK

---

## ШАГ 11: ЗАПУСК ТЕСТОВ (опционально)

### 11.1. Установить dev-зависимости

```bash
# Активировать виртуальное окружение (если есть)
source .venv/bin/activate

# Или создать новое
python3 -m venv test_venv
source test_venv/bin/activate

# Установить зависимости
pip install -r requirements.txt -r requirements-dev.txt
```

### 11.2. Запустить pytest

```bash
# Запустить все тесты
pytest -v

# Или запустить конкретные тесты
pytest tests/test_parser.py -v
pytest tests/test_routes.py -v
pytest tests/test_traffic_collector.py -v
```

**Ожидаемый результат:**
```
======================== test session starts ========================
collected X items

tests/test_parser.py::test_parse_status_log PASSED
tests/test_routes.py::test_api_clients PASSED
...
======================== X passed in X.XXs ========================
```

---

## ШАГ 12: ФИНАЛИЗАЦИЯ

### 12.1. Удалить резервные копии (если все работает)

```bash
# Удалить бэкап docker-compose.yml
rm docker-compose.yml.bak

# Оставить tar.gz бэкап на случай проблем (удалить позже)
ls -lh ../openvpn-monitor-backup-*.tar.gz
```

### 12.2. Объединить ветку с main (если использовали ветку)

```bash
# Переключиться на main
git checkout main

# Объединить изменения
git merge cleanup/project-audit-oct2025

# Удалить временную ветку
git branch -d cleanup/project-audit-oct2025

# Проверить историю
git log --oneline -5
```

### 12.3. Отправить изменения в удаленный репозиторий (опционально)

```bash
# Отправить в origin
git push origin main

# Или в другой remote
git push <remote-name> main
```

---

## ШАГ 13: ДОКУМЕНТИРОВАНИЕ ЗАВЕРШЕНИЯ

### 13.1. Создать файл CLEANUP_COMPLETED.md

```bash
cat > CLEANUP_COMPLETED.md << EOF
# Очистка проекта завершена

**Дата выполнения:** $(date +"%Y-%m-%d %H:%M:%S")
**Выполнено на основе:** PROJECT_AUDIT_OCT_2025.md

## Выполненные действия

### Удалены файлы (3 шт):
- ✅ scripts/server_status.sh
- ✅ scripts/server_status.py
- ✅ crontab

### Архивированы файлы (2 шт):
- ✅ migrate_close_sessions.py → archive/migrations/
- ✅ test_refactoring.py → archive/migrations/

### Обновлены конфигурации:
- ✅ requirements.txt (удален psutil)
- ✅ .gitignore (удалена строка CLAUDE.md)
- ✅ docker-compose.yml (удалены закомментированные строки)

### Обновлена документация:
- ✅ CLAUDE.md (добавлена секция Archived Files)

## Результаты тестирования

- ✅ Docker образ успешно пересобран
- ✅ Контейнер запускается без ошибок
- ✅ API endpoints работают корректно
- ✅ server_status_collector.py обновляет данные
- ✅ traffic_collector.py собирает метрики
- ✅ Веб-интерфейс доступен

## Изменения в размере

**До очистки:**
- Docker образ: XXX MB
- Количество файлов: XXX

**После очистки:**
- Docker образ: XXX MB (уменьшение на ~XX MB из-за psutil)
- Количество файлов: XXX (уменьшение на 3)

## Git коммит

Commit hash: $(git rev-parse HEAD)
Commit message: "Очистка проекта после аудита (октябрь 2025)"

## Примечания

Все изменения протестированы и работают корректно.
Резервная копия сохранена в: ../openvpn-monitor-backup-*.tar.gz

EOF

# Показать файл
cat CLEANUP_COMPLETED.md
```

### 13.2. Добавить в Git

```bash
git add CLEANUP_COMPLETED.md
git commit -m "Документирование завершения очистки проекта"
```

---

## ОТКАТ ИЗМЕНЕНИЙ (если что-то пошло не так)

### Вариант 1: Откат через Git (если изменения закоммичены)

```bash
# Найти коммит перед очисткой
git log --oneline

# Откатиться к предыдущему коммиту
git reset --hard <commit-hash>

# ИЛИ откатить последний коммит
git reset --hard HEAD~1

# Пересобрать контейнер
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Вариант 2: Восстановление из tar.gz бэкапа

```bash
# Остановить контейнер
docker compose down

# Перейти в родительскую директорию
cd /home/app_data/docker/

# Удалить текущую версию
rm -rf openvpn-monitor

# Восстановить из бэкапа
tar -xzf openvpn-monitor-backup-YYYYMMDD-HHMMSS.tar.gz
mv openvpn-monitor openvpn-monitor  # если нужно

# Перейти обратно
cd openvpn-monitor

# Запустить контейнер
docker compose up -d
```

### Вариант 3: Ручной откат отдельных файлов через Git

```bash
# Восстановить конкретный файл
git checkout HEAD~1 -- requirements.txt
git checkout HEAD~1 -- docker-compose.yml

# Пересобрать контейнер
docker compose down
docker compose build --no-cache
docker compose up -d
```

---

## ЧЕКЛИСТ ВЫПОЛНЕНИЯ

Отметьте выполненные шаги:

- [ ] **Шаг 0:** Создан бэкап проекта
- [ ] **Шаг 1:** Удалены устаревшие файлы (server_status.sh, server_status.py, crontab)
- [ ] **Шаг 2:** Миграционные скрипты перемещены в archive/migrations/
- [ ] **Шаг 3:** Удален psutil из requirements.txt
- [ ] **Шаг 4:** Очищен .gitignore (удалена строка CLAUDE.md)
- [ ] **Шаг 5:** Очищен docker-compose.yml (удалены закомментированные строки)
- [ ] **Шаг 6:** Обновлена документация (CLAUDE.md)
- [ ] **Шаг 7:** Решено с archive/ (.gitignore или добавить в Git)
- [ ] **Шаг 8:** Изменения закоммичены в Git
- [ ] **Шаг 9:** Docker-образ пересобран без ошибок
- [ ] **Шаг 10:** Все тесты пройдены успешно
- [ ] **Шаг 11:** pytest запущен (если используется)
- [ ] **Шаг 12:** Изменения объединены с main и отправлены в remote
- [ ] **Шаг 13:** Создан CLEANUP_COMPLETED.md

---

## ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

- **Отчет аудита:** PROJECT_AUDIT_OCT_2025.md
- **История рефакторинга:** REFACTORING_SUMMARY.md
- **Документация разработчика:** CLAUDE.md
- **Основная документация:** README.md

---

**Конец плана**
