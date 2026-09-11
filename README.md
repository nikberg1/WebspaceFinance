# Касса студии — каркас Mini App

Внутренняя касса на двоих. Клиенты не заходят. Проекты, договоры и чаты не входят.

Цвета: тёмно-синий фон, белый текст, красный акцент.

## Что умеет

- факт за месяц: пришло / ушло / прибыль
- ещё придёт / ещё заплатить
- приход и расход в рублях
- статус: план / оплачено / просрочено
- статьи: предоплата, акт, подряд, реклама, сервисы, налоги, зарплата, прочее
- доступ только по Telegram ID из `STAFF_IDS`

## Быстрый локальный запуск

```bash
cd studio-cash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Откройте http://127.0.0.1:8080

`DEV_MODE=true` пускает без настоящей подписи Telegram, пользователь — заглушка `111`.

## Запуск бота + Mini App вместе

1. Создайте бота у [@BotFather](https://t.me/BotFather).
2. В `.env` пропишите:

```
BOT_TOKEN=реальный_токен
WEBAPP_URL=https://ваш-домен
STAFF_IDS=111,222
DEV_MODE=false
```

3. Замените `111,222` на ваши Telegram ID.
4. Mini App обязан быть на HTTPS. Локальный `http://127.0.0.1` Telegram не откроет как WebApp.
5. Запуск:

```bash
python run.py
```

В BotFather: `/setmenubutton` или просто откройте бота — кнопка «Открыть кассу» придёт на /start.

## Как узнать свой Telegram ID

Напишите [@userinfobot](https://t.me/userinfobot) и подставьте число в `STAFF_IDS`.

## Структура

```
app/        API, бот, база
webapp/     Mini App
data/       SQLite, появится после первого запуска
```

## Что не входит в каркас

вложения чеков, Excel, проекты, роли сложнее «свой / чужой», автосоздание чатов.
