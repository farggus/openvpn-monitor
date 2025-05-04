# Git & GitHub Cheatsheet — OpenVPN Monitor

## Сценарий 1: Редактирование локально (на сервере)

#### 1. Получить последние изменения с GitHub
```
git pull origin main
```
#### 2. Отредактировать файлы локально

#### 3. Проверить статус изменений
```
git status
```
#### 4. Добавить файлы в индекс
```
git add .
```
#### 5. Создать коммит
```
git commit -m "Your commit message"
```
#### 6. Отправить изменения на GitHub
```
git push origin main
```

## Сценарий 2: Редактирование в интерфейсе GitHub (удалённо)

### 1. Перед началом работы локально — подтянуть свежие изменения
```
git pull origin main
```

### Общие советы

Используй git status как контрольную точку.
Работай либо локально, либо удалённо, чтобы избежать конфликтов.
Названия веток: main — основная ветка.
Коммиты должны быть краткими и по делу (на английском, например: Fix graph update issue).


## SSH-подключение (если возникнут проблемы)
Проверить, есть ли SSH-ключ
```
ls ~/.ssh/id_rsa.pub
```
Если нет — сгенерировать ключ
```
ssh-keygen -t rsa -b 4096 -C "your.email@example.com"
```
Добавить ключ в GitHub: https://github.com/settings/keys

## Проверка подключения
```
ssh -T git@github.com
```
---

## 🧰 Additional Resources

- [Markdown Syntax Guide](./markdown_guide.md)
- [GitHub Docs: Working with Git](https://docs.github.com/en/get-started)

---

Author: Farggus  
Project: OpenVPN Monitor  
