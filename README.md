[![Made for Home Assistant](https://img.shields.io/badge/Made%20for-Home%20Assistant-blue?style=for-the-badge&logo=homeassistant)](https://www.home-assistant.io/)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

# SDUI Timetable
![Logo](/assets/logo.png)
A custom Home Assistant integration to display your school timetable from SDUI.

## Features
- Shows the number of lessons for today
- Displays the first lesson with time, subject, and status
- Filters out cancelled lessons
- Updates automatically every 15 minutes

## Installation via HACS
1. Open **HACS → Integrations → Custom repositories**.
2. Add  
   `https://github.com/topergamesyt/sdui_timetable`  
   and select **Integration**.
3. Install the integration.
4. Add the following to your `configuration.yaml`:

```yaml
sensor:
  - platform: sdui_timetable
    user_id: "your_user_id"
    token: "your_token"
