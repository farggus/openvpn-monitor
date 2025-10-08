# 0) Выполнять под пользователем github
cd /home/app_data/docker/openvpn-monitor || exit 1

# 1) Кандидаты-ключи (упорядочил по вероятности)
CANDIDATES=(
  "$HOME/.ssh/openvpn-monitor_deploy"
  "$HOME/.ssh/openvpn-monitor_actions"
  "$HOME/.ssh/openvpn-monitor-pullrequest"
  "$HOME/.ssh/family-tree"
  "$HOME/.ssh/family-tree_deploy"
)

echo "[i] Проверяю приватные ключи..."
WORKING_KEY=""
for k in "${CANDIDATES[@]}"; do
  if [ -f "$k" ]; then
    chmod 600 "$k"
    echo "===> Тест: $k"
    # Пробуем аутентифицироваться именно этим ключом
    OUT=$(ssh -i "$k" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new -T git@github.com -v 2>&1 | head -n 5)
    echo "$OUT"
    if echo "$OUT" | grep -qiE "Hi .*!|successfully authenticated"; then
      WORKING_KEY="$k"
      echo "[OK] Подошёл ключ: $WORKING_KEY"
      break
    fi
  fi
done

if [ -z "$WORKING_KEY" ]; then
  echo "[ERR] Ни один из ключей не подошёл. Нужно добавить *.pub в GitHub (Settings → SSH keys) или включить write у deploy key."
  exit 2
fi

# 2) Прописываем рабочий ключ в ~/.ssh/config
mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
cat > "$HOME/.ssh/config" <<EOF
Host github.com
  HostName github.com
  User git
  IdentityFile $WORKING_KEY
  IdentitiesOnly yes
EOF
chmod 600 "$HOME/.ssh/config"
echo "[i] ~/.ssh/config обновлён, ключ: $WORKING_KEY"

# 3) Проверяем, куда смотрит origin
echo "[i] git remote -v:"
git remote -v

# (Необязательно) Если нужен другой форк — раскомментируй и подставь свой логин:
# git remote set-url origin git@github.com:scuruci/openvpn-monitor.git

# 4) Быстрый тест чтения из origin этим же ключом
echo "[i] Тест ls-remote:"
GIT_SSH_COMMAND="ssh -i $WORKING_KEY -o IdentitiesOnly=yes -v" git ls-remote origin | head || exit 3

# 5) Пробуем пуш (создаст пустой пуш, если нечего пушить — просто проверим соединение)
echo "[i] Пробую git push:"
GIT_SSH_COMMAND="ssh -i $WORKING_KEY -o IdentitiesOnly=yes -v" git push
