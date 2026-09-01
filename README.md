# vk-ext — расширение Firefox + приёмник VK-кук для Raisa

Комплекс из двух частей:

1. **Firefox-расширение** — читает куки `vk.ru`/`vk.com` из браузера и отправляет
   их на локальный приёмник (`127.0.0.1:8002`).
2. **Приёмник** (`vk_cookie_server.py`) — HTTP-сервер, который обновляет строку
   `VK_COOKIE=` в `vk.conf` проекта RaisaAI.

Нужно, чтобы ассистент Raisa всегда работал со свежими куками входа VK: как
только вы вошли/обновили сессию в браузере — куки автоматически попадают в
конфиг ассистента.

## Состав

```
background.js             # сторожевая логика: ловит изменения кук, шлёт их серверу
manifest.json             # манифест MV3 (Firefox)
popup.html / popup.js     # кнопка быстрого обновления кук вручную
vk_cookie_server.py       # приёмник: принимает куки, пишет VK_COOKIE в vk.conf
vk-cookie-server.service  # systemd-юнит для автозапуска приёмника
vk-raisacookies.xpi       # собранный пакет расширения (zip)
```

## Как это работает

1. Расширение подписано на `browser.cookies.onChanged` и при изменении кук
   `vk.ru`/`vk.com` отправляет их POST-запросом на
   `http://127.0.0.1:8002/update`.
2. Приёмник принимает куки, отбирает нужные для VK Music (`remixsid`,
   `remixsid6k`, `p`, `remixnttpid`, `httoken` и полезные `remix*`), собирает
   строку `name=value; ...` и заменяет поле `VK_COOKIE=` в конфиге.
3. Raisa читает `vk.conf` и использует свежую строку кук для запросов к VK.

Дросселирование: не чаще одного раза в 2 секунды; ручное обновление — кнопка
расширения.

## Установка расширения в Firefox

xpi не подписан Mozilla, поэтому штатная установка через `about:addons`
невозможна. Два варианта:

**Временная установка (на текущую сессию Firefox):**

1. Откройте `about:debugging#/runtime/this-firefox`.
2. Нажмите **Load Temporary Add-on…** и выберите `vk-raisacookies.xpi`
   (или `manifest.json` из распакованной папки).
3. После перезапуска Firefox расширение пропадает — ставится заново.

**Постоянная установка (для собственного использования):**

- В `about:config` установите `xpinstall.signatures.required = false`, затем
  откройте `vk-raisacookies.xpi` через `about:addons` → «Установить из файла».
- Либо соберите с подписью через [extensionworkshop.com](https://extensionworkshop.com)
  (нужна регистрация, бесплатно для личного использования).

После установки зайдите на `vk.ru` в этом же профиле — куки будут отправлены
автоматически.

## Запуск приёмника

**Способ 1 — через setup.sh RaisaAI:**

```bash
./setup.sh
```

`setup.sh` сам запустит `vk_cookie_server.py` в фоне на порту 8002.

**Способ 2 — вручную:**

```bash
python3 vk_cookie_server.py --config /путь/к/RaisaAI/vk.conf
```

По умолчанию слушает `127.0.0.1:8002`. Приёмник должен быть запущен до
отправки кук расширением.

**Способ 3 — через systemd:**

Скопируйте `vk-cookie-server.service` в `/etc/systemd/system/`, отредактируйте
`User=` и пути до `vk_cookie_server.py` и `vk.conf` под вашу систему, затем:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vk-cookie-server
```

Проверка: `systemctl status vk-cookie-server`.

## Требования к vk.conf

Приёмник только обновляет строку `VK_COOKIE`, файл `vk.conf` должен
существовать и содержать хотя бы заголовок:

```
VK_ACCESS_TOKEN=vk1.a....
VK_COOKIE=
```

Если поля `VK_COOKIE=` в файле нет, приёмник допишет его в конец.

## Вручную отправить куки

Нажмите кнопку расширения («Обновить куки сейчас»). Статус покажет результат.

## Пересборка xpi

После правок исходников пересоберите пакет из папки:

```bash
zip -r vk-raisacookies.xpi manifest.json background.js popup.html popup.js
```
