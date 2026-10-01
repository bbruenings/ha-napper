# Napper Baby Tracking Integration for Home Assistant

A custom Home Assistant integration for the Napper baby tracking app. Exposes baby data as sensors and provides services for logging events.

## Features

- **Binary Sensors**: Track when baby is sleeping
- **Sensors**: 
  - Last diaper change timestamp and content type
  - Last solid food feeding
  - Last wake up time
  - Last bedtime
  - Next scheduled nap time
  - Next scheduled bedtime
- **Services**: Log diaper changes, feedings, sleep events, and more
- **Automatic Token Refresh**: Tokens are automatically refreshed before expiration

## Installation

### Option 1: HACS (Recommended)

1. Open HACS in Home Assistant
2. Click "Custom Repositories"
3. Add this repository URL
4. Search for "Napper" and install
5. Restart Home Assistant

### Option 2: Manual Installation

1. Copy the `napper` folder to your `custom_components` directory:
   ```bash
   cp -r custom_components/napper /config/custom_components/
   ```
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for **Napper**
4. Follow the authentication flow:
   - **Step 1**: Enter your email address associated with your Napper account
   - **Step 2**: Check your email for the OTP (one-time password) code and enter it
   - **Step 3**: Select which baby to monitor (if you have multiple)

The integration will automatically handle token storage and refresh.

## Authentication Flow

The Napper integration uses a secure OTP (One-Time Password) authentication flow:

```
┌─────────────────┐
│  Step 1: Email  │
│  Enter email    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ POST /auth/     │
│ send-otp        │
│ Send OTP email  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Step 2: OTP    │
│  Enter code     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ POST /auth/     │
│ email-login     │
│ Get JWT tokens  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Step 3: Baby   │
│  Select baby    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GET /babies     │
│ Fetch baby list │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Store tokens    │
│ Start polling   │
└─────────────────┘
```

### API Endpoints Used

**Important:** The Napper API returns `Content-Type: text/plain; charset=utf-8` for ALL endpoints, even when the response body contains valid JSON. This is a known quirk of the API. The integration handles this by reading responses as text first, then parsing as JSON.

1. **POST /auth/send-otp**
   - Body: `{"email": "user@example.com", "useDeviceId": true, "source": "APP", "language": "en"}`
   - Response: Empty string `""` (Content-Type: text/plain)
   - Sends 6-digit OTP to user's email

2. **POST /auth/email-login**
   - Body: `{"email": "user@example.com", "otp": "123456", "useDeviceId": true}`
   - Response (as JSON, but Content-Type: text/plain):
   ```json
   {
     "item": {
       "idToken": {
         "token": "eyJhbG...",
         "payload": {"exp": 1790932448, "sub": "user-id"}
       },
       "refreshToken": {
         "token": "abc123...",
         "payload": {"exp": 1819876448}
       }
     }
   }
   ```

3. **GET /babies**
   - Headers: `Authorization: Bearer ***`
   - Response: `{"items": [...]}` (Content-Type: text/plain)
   - Returns array of baby objects with id, name, birthday, etc.

### Token Management

- **ID Token**: JWT token, expires in ~30 days
- **Refresh Token**: Used to obtain new ID token when expired
- **Automatic Refresh**: The integration automatically refreshes tokens 5 days before expiration
- **Secure Storage**: Tokens are stored in Home Assistant's encrypted config entry storage

## Entities

### Binary Sensors

| Entity ID | Description |
|-----------|-------------|
| `binary_sensor.{baby_name}_sleeping` | True when baby is currently napping/sleeping |

### Sensors

| Entity ID | Description |
|-----------|-------------|
| `sensor.{baby_name}_last_diaper_change` | Timestamp of last diaper change |
| `sensor.{baby_name}_last_diaper_content` | Content type (WET/MIXED/POOP) |
| `sensor.{baby_name}_last_solid_food` | Timestamp of last solid food feeding |
| `sensor.{baby_name}_last_wake_up` | Timestamp of last wake up |
| `sensor.{baby_name}_last_bedtime` | Timestamp of last bedtime |
| `sensor.{baby_name}_next_nap` | Scheduled time for next nap |
| `sensor.{baby_name}_next_bedtime` | Scheduled time for next bedtime |

## Services

### `napper.log_diaper_change`

Log a diaper change event.

**Fields:**
- `diaper_content` (required): WET, MIXED, or POOP
- `comment` (optional): Note about the change
- `timestamp` (optional): ISO 8601 timestamp

**Example:**
```yaml
service: napper.log_diaper_change
data:
  diaper_content: WET
  comment: "Morning change"
```

### `napper.log_solids`

Log a solid food feeding.

**Fields:**
- `comment` (optional): Note about the feeding
- `timestamp` (optional): ISO 8601 timestamp

### `napper.log_sleep_start`

Log when baby starts sleeping.

**Fields:**
- `comment` (optional): Note
- `timestamp` (optional): ISO 8601 timestamp

### `napper.log_sleep_end`

Log when baby wakes up from sleep.

**Fields:**
- `log_id` (required): ID of the nap log to close

### `napper.log_wake_up`

Log a wake up event.

**Fields:**
- `comment` (optional): Note
- `timestamp` (optional): ISO 8601 timestamp

### `napper.log_bedtime`

Log bedtime event.

**Fields:**
- `comment` (optional): Note
- `timestamp` (optional): ISO 8601 timestamp

### `napper.log_nursing`

Log a nursing session.

**Fields:**
- `comment` (optional): Note
- `timestamp` (optional): ISO 8601 timestamp

### `napper.delete_log`

Delete a log entry.

**Fields:**
- `log_id` (required): ID of the log to delete

### `napper.get_logs`

Retrieve logs from Napper.

**Fields:**
- `category` (optional): Filter by category (NAP, CHANGED_DIAPER, SOLIDS, etc.)

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

### Log diaper change from button

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

### Track sleep patterns

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
        Baby slept: {{ states('sensor.baby_last_wake_up') }}
        Next bedtime: {{ states('sensor.baby_next_bedtime') }}
```

## Polling

The integration polls the Napper API every 60 seconds for updates. This interval is a balance between:
- Getting timely updates when baby state changes
- Not overwhelming the API with requests

## Troubleshooting

### "Invalid OTP code" error

- Verify you entered the code correctly (no extra spaces)
- OTP codes expire after a few minutes - request a new one if needed
- Check your spam folder for the email

### "Authentication failed. Please re-authenticate." error

Your tokens may have become invalid. To re-authenticate:
1. Go to Settings → Devices & Services
2. Click on Napper
3. Click Configure
4. The flow will start over with email entry

### "No babies found" error

- Verify your Napper account has at least one baby registered
- Make sure you're using the correct email address

### Entities not updating

Check the Home Assistant logs for API errors:
```bash
tail -f /config/home-assistant.log | grep napper
```

## Development

### Testing the Authentication Flow

To test the API calls without going through the full config flow:

```python
import aiohttp
import asyncio

async def test_auth():
    async with aiohttp.ClientSession() as session:
        # Step 1: Send OTP (don't actually send during testing)
        # await session.post("https://api.napper.app/auth/send-otp", ...)
        
        # Step 2: Verify OTP with test credentials
        response = await session.post(
            "https://api.napper.app/auth/email-login",
            json={"email": "test@example.com", "otp": "123456"}
        )
        tokens = await response.json()
        print(tokens)

asyncio.run(test_auth())
```

### Structure

```
custom_components/napper/
├── __init__.py          # Integration setup
├── config_flow.py       # Configuration UI (multi-step OTP flow)
├── const.py            # Constants and API endpoints
├── coordinator.py      # Data update coordinator with token refresh
├── binary_sensor.py    # Binary sensor platform
├── sensor.py           # Sensor platform
├── services.py         # Service definitions
├── services.yaml       # Service documentation
├── strings.json        # Translations
└── manifest.json       # Integration metadata
```

## API Reference

- **Base URL**: `https://api.napper.app`
- **Auth**: Bearer token in Authorization header
- **Auth Endpoints**:
  - `POST /auth/send-otp` - Send OTP to email
  - `POST /auth/email-login` - Login with OTP, get tokens
  - `POST /auth/refresh` - Refresh expired token
- **Data Endpoints**:
  - `GET /babies` - List babies
  - `GET /widget-today/{babyId}/{timestamp}` - Get today's data
  - `PUT /logs/{babyId}` - Create/update log
  - `DELETE /logs/{babyId}/{logId}` - Delete log

## Security Notes

- Tokens are stored in Home Assistant's encrypted storage
- No credentials are logged or transmitted insecurely
- The integration follows Home Assistant's security best practices
- OTP codes are never stored - only used for initial authentication

## License

MIT License

## Credits

- Napper API documentation from reverse engineering
- Home Assistant integration pattern based on official integrations
