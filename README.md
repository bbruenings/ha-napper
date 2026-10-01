# Napper Baby Tracking for Home Assistant

[![HACS][hacs-badge]][hacs-url]
[![GitHub Release][release-badge]][release-url]
[![License][license-badge]][license-url]
[![Validate][validate-badge]][validate-url]
[![Tests][tests-badge]][tests-url]

Custom [Home Assistant](https://www.home-assistant.io/) integration for the
**Napper baby tracking app**. Brings your baby's sleep, feeding, and diaper
data into Home Assistant as live sensors, and lets automations log new
events directly to Napper.

> [!NOTE]
> **Disclaimer:** This project is not affiliated with, endorsed by, or
> connected to Napper. "Napper" is a trademark of its respective owner.
> This integration was developed independently through protocol analysis
> of the Napper mobile app.

## Features

- 👶 Live sensors for sleep state, naps, and diaper changes
- 🧡 Entities for last diaper change (per content type), last solids, last wake up, last bedtime
- ⏰ Upcoming schedule sensors: next nap, next bedtime, expected nap duration and end time
- 🛌 Binary sensor showing when the baby is sleeping
- ✍️ Services to log diaper changes, solid food, sleep, wake ups, bedtimes, and nursing sessions
- 🔐 Email + OTP login flow with automatic token storage and refresh
- 🔁 Automatic re-authentication flow when the refresh token expires

## Requirements

- **Home Assistant** 2024.12.0 or newer
- **Napper account** - the email address you use in the Napper baby tracking app

## Installation

### HACS (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance
2. Add this repository as a custom repository:
   - Go to **HACS** → **Integrations** → **⋮** (top right) → **Custom repositories**
   - Enter `https://github.com/bbruenings/ha-napper` and select **Integration**
   - Click **Add**
3. Search for **Napper Baby Tracking** in HACS and click **Download**
4. Restart Home Assistant

### Manual Installation

1. Download the [latest release](https://github.com/bbruenings/ha-napper/releases/latest)
2. Copy the `custom_components/napper/` folder to your Home Assistant
   `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

The integration is configured through the Home Assistant UI. No YAML configuration needed.

### Manual Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **Napper Baby Tracking**
3. Enter the email address associated with your Napper account
4. Check your email for the one-time password (OTP) code and enter it
5. Select which baby to monitor (if you have multiple)
6. The integration creates all sensors and services for the selected baby

Tokens are stored and refreshed automatically.

### Entities Created

**Sensors:**

| Entity | Description |
|--------|-------------|
| Last Diaper Change | Timestamp of the last diaper change |
| Last Diaper Content | Content type of the last change (wet/mixed/poop) |
| Last Wet/Dry/Mixed/Dirty Diaper | Timestamps per diaper content type |
| Last Solid Food | Timestamp of the last solid food feeding |
| Last Wake Up | Timestamp of the last wake up |
| Last Bedtime | Timestamp of the last bedtime |
| Next Nap | When the next nap is scheduled |
| Next Bedtime | When the next bedtime is scheduled |
| Current Nap | State and attributes of the running nap |
| Nap Expected Duration | Expected nap duration in minutes |
| Nap Expected End Time | When the current/next nap is expected to end |
| Bedtime Expected Time | When the next bedtime is expected |

**Binary sensor:**

| Entity | Description |
|--------|-------------|
| Baby Sleeping | On while the baby is sleeping |

All entities belong to a device named after the selected baby.

### Services

All services are available under the `napper.` domain:

| Service | Description |
|---------|-------------|
| `napper.log_diaper_change` | Log a diaper change (`diaper_content`: WET / MIXED / POOP) |
| `napper.log_solid_food` | Log a solid food feeding |
| `napper.log_solids` | Alias for `log_solid_food` |
| `napper.log_sleep_start` | Log that the baby started sleeping |
| `napper.log_sleep_end` | Close an open nap (supports `log_id: current`) |
| `napper.log_wake_up` | Log a wake up event |
| `napper.log_bedtime` | Log a bedtime event |
| `napper.log_nursing` | Log a nursing session |
| `napper.delete_log` | Delete a log entry by ID |
| `napper.get_logs` | Retrieve logs, optionally filtered by category |

Every logging service accepts an optional `comment` and an optional
`timestamp` (ISO 8601). See the **Actions** tab on the Napper device for
the full field list.

## Automation Examples

### Notify when baby wakes up

```yaml
alias: Baby Wake Up Notification
trigger:
  - platform: state
    entity_id: binary_sensor.baby_sleeping
    to: "off"
action:
  - service: notify.mobile_app
    data:
      message: "Baby has woken up!"
```

### Log diaper change from a button

```yaml
alias: Quick Diaper Change Log
trigger:
  - platform: event
    event_type: ios.action_fired
    event_data:
      actionName: DIAPER_CHANGE
action:
  - service: napper.log_diaper_change
    data:
      diaper_content: WET
```

### Daily sleep report

```yaml
alias: Daily Sleep Report
trigger:
  - platform: time
    at: "20:00:00"
action:
  - service: persistent_notification.create
    data:
      title: "Today's Sleep Summary"
      message: >
        Next nap: {{ states('sensor.baby_next_nap') }}
        Next bedtime: {{ states('sensor.baby_next_bedtime') }}
```

## Troubleshooting

### "Invalid OTP code" error

- Verify you entered the code correctly (no extra spaces)
- OTP codes expire after a few minutes - request a new one if needed
- Check your spam folder for the email

### "Authentication failed" / re-authenticate prompt

The refresh token can become invalid. The integration detects this and shows
a **Reauthenticate** action:

1. Go to **Settings** → **Devices & Services**
2. Click on Napper
3. Click **Reauthenticate** and start the email + OTP flow again

### Entities not updating

- Check **Settings** → **Devices & Services** → Napper for errors
- Enable debug logging (below) and check the logs

The integration polls the Napper API every 60 seconds.

### Enable debug logging

Add the following to your `configuration.yaml` for detailed logs:

```yaml
logger:
  default: warning
  logs:
    custom_components.napper: debug
```

## Contributing

Contributions are welcome! Please:

1. [Open an issue](https://github.com/bbruenings/ha-napper/issues) to discuss your idea first
2. Fork the repository and create a feature branch
3. Submit a pull request

## License

This project is licensed under the [MIT License](LICENSE).

## Acknowledgements

This integration was built with the help of [Claude (Anthropic)](https://claude.ai/claude-code)
and [OpenAI Codex](https://openai.com/).

---

[hacs-badge]: https://img.shields.io/badge/HACS-Custom-orange.svg
[hacs-url]: https://github.com/hacs/integration
[release-badge]: https://img.shields.io/github/v/release/bbruenings/ha-napper
[release-url]: https://github.com/bbruenings/ha-napper/releases
[license-badge]: https://img.shields.io/github/license/bbruenings/ha-napper
[license-url]: https://github.com/bbruenings/ha-napper/blob/main/LICENSE
[validate-badge]: https://github.com/bbruenings/ha-napper/actions/workflows/validate.yml/badge.svg
[validate-url]: https://github.com/bbruenings/ha-napper/actions/workflows/validate.yml
[tests-badge]: https://github.com/bbruenings/ha-napper/actions/workflows/tests.yml/badge.svg
[tests-url]: https://github.com/bbruenings/ha-napper/actions/workflows/tests.yml
