# Movistar Car - Home Assistant Integration

Custom [Home Assistant](https://www.home-assistant.io/) integration for **Movistar Car / Movistar Mobility** connected car devices. Track your vehicle's location, fuel level, speed, battery voltage, and more directly from your HA dashboard.

## Features

- **GPS Device Tracker** — Live vehicle location on the HA map with heading and speed attributes
- **Vehicle Sensors** — Fuel level, speed, odometer, battery voltage, heading, and timestamps
- **Binary Sensors** — Device connectivity, OBD error detection, WiFi status, GPS validity
- **Multi-vehicle support** — Select which vehicle to track if your account has multiple devices
- **Token persistence** — Avoids unnecessary re-authentication between restarts
- **Configurable polling** — Adjust the update interval (default: 120s)

## Entities

### Sensors

| Entity | Device Class | Unit |
|---|---|---|
| Battery Voltage | `voltage` | V |
| Fuel Level | — | % |
| Speed | `speed` | km/h |
| Odometer | `distance` | km |
| Trip Odometer | `distance` | km |
| Heading | — | ° |
| Last Reception | `timestamp` | — |
| Location Time | `timestamp` | — |
| Data Synced | `timestamp` | — |
| WiFi SSID | — | — |
| WiFi Data Used | — | MB |

### Binary Sensors

| Entity | Device Class |
|---|---|
| Connected | `connectivity` |
| OBD Errors | `problem` |
| WiFi Enabled | `connectivity` |
| GPS Valid | — |

### Device Tracker

GPS location entity with `heading`, `speed`, and `gps_valid` as extra attributes. Shows your vehicle on the Home Assistant map.

## Installation

### HACS (Manual Repository)

1. Open HACS in Home Assistant
2. Go to **Integrations** > **Custom Repositories**
3. Add `https://github.com/lrodriguezesc/movistar-car-ha` as an **Integration**
4. Search for "Movistar Car" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/movistar_car` folder into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Movistar Car**
3. Enter your Movistar Mobility email and password
4. If your account has multiple vehicles, select which one to track
5. Done — entities will appear automatically

### Options

After setup, click **Configure** on the integration card to adjust:

- **Update interval** — How often to poll the API (30–3600 seconds, default: 120)

## API

This integration communicates with the Movistar Mobility / Net4Things API (`api-xmp-cli.net4things.com`). It uses the same endpoints as the official Movistar Mobility mobile app.

## License

MIT
