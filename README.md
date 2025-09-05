# SDUI Timetable for Home Assistant

Кастомная интеграция для Home Assistant, показывающая расписание SDUI.

## Установка через HACS
1. Открой HACS → Custom repositories → Добавь `https://github.com/ToperGamesYT/sdui_timetable` как **Integration**.
2. Установи интеграцию.
3. Добавь в `configuration.yaml`:

```yaml
sensor:
  - platform: sdui_timetable
    user_id: "2349208"
    token: "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9..."
