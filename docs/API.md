# Movistar Mobility API notes

Notes about the cloud API used by this integration. The API is **not public or documented**. These notes come from the traffic of the official app and from live responses (checked 2026-11-10). They can become wrong at any time.

> ⚠️ Never put real values (passwords, tokens, SIM numbers, VIN, plate, SSID, WiFi password) in issues, commits or logs. The `/session` response contains all of them.

## Base

- Base URL: `https://api-xmp-cli.net4things.com/API/v3`
- Platform: Net4Things (`xmp` = Movistar Mobility)
- Headers on every call:
  - `User-Agent`: the app user agent (see `const.py`)
  - `Content-Type: application/json; charset=utf-8`
  - `Accept: plain/text,application/json`
  - `Token: <session token>` (all calls except login)
- Times are **milliseconds since the Unix epoch (UTC)**.

## Authentication

| Call | Description |
|---|---|
| `PUT /session` | Login. Body: `{"Username", "Password", "EnterpriseKey"}`. The response has a top-level `Token` and the session data. |
| `GET /session` | With a valid `Token` header, it returns the session data again. Status `200` means the token is valid. Other statuses mean login again. |

- The `EnterpriseKey` identifies the **app**, not the user. It is the same for all users of the Movistar Mobility app.
- The enterprise config shows `ExpirationSessionTime = 129600` and `UpdatingSessionFrequency = 1439`. The units are not documented. If 129600 is in seconds, a session lasts 36 hours. The integration stores the token and logs in again only when the token is rejected.
- Login limits: `MaxLoginAttempts = 3`, `LoginAttemptsWaitTime = 60` s. Do not retry a failed login in a tight loop. The coordinator waits 10 minutes between retries for this reason.

## Endpoints

### `GET /session`

The main call. It is large because it includes the full configuration, so do not call it more often than needed.

Top-level keys:

| Key | Content |
|---|---|
| `Enterprise` | App configuration (languages, feature flags, about 300 config items). Not useful for entities. |
| `User` | Account data (name, email, phone). **Personal.** |
| `Services[]` | One per contracted service. Links a `DeviceId` and a `VehicleId`. |
| `Vehicles[]` | Car data (make, model, year, consumption, ITV). |
| `Devices[]` | The OBD device (voltage, km, WiFi, connection). |
| `Invitations[]` | Sharing invitations. |
| `Timestamp` | Server time. |

How the lists connect: `Services[].DeviceId → Devices[].Id` and `Services[].VehicleId → Vehicles[].Id`. The integration matches the service by `service_id` and then finds its vehicle.

#### `Devices[]` (the OBD box)

| Field | Type | Used | Notes |
|---|---|---|---|
| `Id`, `Serial` | int, str | ✅ | |
| `Voltage` | float | ✅ | 12 V battery |
| `Kilometers` | float | ✅ | Odometer |
| `Connected` | bool | ✅ | `false` when parked and asleep |
| `LastReception` | ms | ✅ | |
| `BatteryLevel` | float or null | ✅ | Usually `null` |
| `DeviceStatus`, `State` | int | ✅ / — | Codes, meaning not known |
| `ActivationDate`, `AssociationDate`, `DisconnectionDate` | ms | ✅ | |
| `Incompatible` | bool | ✅ | |
| `SIMSerial`, `SIMNumber` | str | ✅ | Personal |
| `WiFiStatus` | object | partly | **See the pitfall below** |
| `Capabilities` | object | — | Bit masks of device features |
| `AssociationAllowed`, `AssociationState` | | — | |
| `AnomalousVINDate` | | — | Hidden by the integration |

#### `Services[]`

| Field | Type | Used | Notes |
|---|---|---|---|
| `Id`, `DeviceId`, `VehicleId` | int | ✅ | |
| `Kilometers` | float | — | Same as the device odometer |
| `ExtraData[]` | `{Name, DataType, Value}` | ✅ | Name/value pairs. Contains `SCORING_DAILY` and `SCORING_MONTHLY`. |
| `WiFiStatus` | object | ✅ | **Real data pack values.** |
| `TheftAlarmStatus` | object | ✅ | `Armed`, `State`, `AlarmDate`, `AlarmEventLatitude/Longitude`, `ArmDate`, `DisarmDate` |
| `TheftAlarmPreferences` | object | — | `ArmMode`, schedule |
| `Product.Packages[]` | | — | Contracted packages and their `Status` |
| `Product.Properties[]` | | — | About 120 feature flags (see below) |
| `ActivationDate`, `State`, `IsOwner`, `IsShared`, `SilentMode` | | — | |
| `FirstYearWithStatistics` | int | — | First year with statistics (2022 here). Hints at a statistics endpoint. |

`ExtraData` values:

- `SCORING_DAILY`: a string with a number, for example `"89"`.
- `SCORING_MONTHLY`: a **JSON string**: `{"2026": [82, 94, 99, -1, ...]}`. One list of 12 values per year, January first. **`-1` means no data.**

`WiFiStatus` on a service:

| Field | Notes |
|---|---|
| `Enabled`, `SSID`, `Password`, `IPAddress` | |
| `UsedData` | **Bytes** used in the cycle |
| `DataPackSize` | **Bytes** |
| `DataUsageCycleLastDay` | Day of month when the cycle ends |
| `DataPacks[]` | `{Name, Type, Used, Size, ExpirationDate, PurchaseDate}`. Sizes are in bytes. |

#### `Vehicles[]`

| Field | Used | Notes |
|---|---|---|
| `Make`, `Model`, `ManufacturingYear` | ✅ | Device model name |
| `ConsumptionAverage` | ✅ | **Certified** value, L/100 km |
| `CO2Certified` | ✅ (in data) | g/km |
| `NextVTIDate` | ✅ | ITV date, in ms. The owner must keep it up to date in the app, so it can be old. |
| `FuelType` | — | `1` = gasoline in this account |
| `Insurance` | — | Mostly empty |
| `Plate`, `VIN`, `AllowedVIN` | ❌ | Personal. Do not log. |
| `EnvironmentalClassification`, `ModelId`, `MakeId`, `YearId` | — | |

### `GET /session/location-status/{vehicle_index}`

`{vehicle_index}` is the **position in the `Devices` list** (0 for the first), not an id.

```json
{
  "Timestamp": 0,
  "Status": [{
    "ServiceId": 0,
    "DeviceStatus": 1,
    "LastReception": 0,
    "TotalKilometers": 0.0,
    "OnStreetParkingStatus": 0,
    "LatestEvent": {
      "EventType": 5002, "Type": 2,
      "Latitude": 0.0, "Longitude": 0.0, "ValidPosition": true,
      "Speed": 0.0, "Fuel": 0.0, "Heading": 0, "Date": 0
    }
  }]
}
```

- `Fuel` is a **percentage**. The tank size is not in the API.
- `TotalKilometers` is the service counter. It differs from the device `Kilometers` by a fixed offset.
- `LatestEvent.Date` is the time of the GPS fix. It can be older than `LastReception`.

### `POST /obd-diagnostic-codes/{service_id}/query`

Returns a list of codes. Each code has `Solved` (bool). `404` means no codes. The integration counts the codes where `Solved` is false.

### `GET /geometries`

Returns `[]` for this account (geofences). Probably the geofence list.

## Pitfalls

1. **WiFi data is in two places with different meanings.** `Devices[].WiFiStatus` has `DataPackSize: 0` and a small `UsedData`. `Services[].WiFiStatus` has the real pack, in **bytes**. Use the service. Versions before 1.1.0 read the device and showed wrong values.
2. **Monthly score uses `-1`** for months without data. Treat it as "no value", not as a score.
3. **The `Fuel` value is a percentage.** Litres need the tank size from the user.
4. **`ConsumptionAverage` is certified.** Real consumption is higher (about 8 L/100 km measured against 5.1 certified, for one city-driven car). That is why the integration measures it from the fuel % and the odometer.
5. **The device sleeps.** `Connected = false` and an old `LastReception` are normal when the car is parked.
6. **Keep logins rare.** Several clients can read the API at the same time (the HA integration and a separate script both work with the same account). We did not test whether a new `PUT /session` invalidates older tokens. Login only when the token is rejected.
7. **Large payload.** `GET /session` carries the whole enterprise config (about 300 items) and about 120 product properties. It is called on every poll to validate the token and to read device data. Keep the update interval reasonable.

## Features seen but not implemented

The account has these packages, so the app has matching screens, but their endpoints are **not known yet**:

`PKG_TRIP_TAGGING`, `PKG_DRIVING_SCORING`, `PKG_VEHICLE_MAINTENANCE`, `PKG_VEHICLE_INSURANCE`, `PKG_OBD_DIAGNOSTIC_CODES` (with history), `PKG_DOCUMENTS`, `PKG_APPOINTMENTS`, `PKG_EUROTALLER`, `PKG_ASSISTANCE`, `PKG_WIFI`, `PKG_ANTI_THEFT_ALARM`.

The enterprise config also lists categories `Trips`, `Alerts`, `Geometries` (min size 100, max size 200000) and `Notifications`.

### Endpoints that returned 404 (guessed paths, 2026-11-10)

`/trips`, `/service/{id}/trips`, `/services/{id}/trips`, `/trip`, `/obd-diagnostic-codes/{id}` (GET), `/obd-diagnostic-codes/{id}/history`, `/services/{id}/statistics`, `/statistics`, `/alerts`, `/services/{id}/geometries`, `/session/service/{id}`, `/maintenance`, `/vehicle-maintenance`, `/driving-scoring`, `/scoring`, `/services/{id}/scoring`, `/documents`, `/services/{id}/events`, `/events`.

### How to find the real paths

Guessing does not work. Capture the traffic of the app:

1. Install [mitmproxy](https://mitmproxy.org) and run `mitmweb`.
2. Set your phone proxy to the computer and install the mitmproxy certificate.
3. Open the Trips, Statistics and Maintenance screens in the Movistar Mobility app.
4. Read the `api-xmp-cli.net4things.com/API/v3/...` requests in mitmweb.

If the app uses certificate pinning, use a rooted device or a tool such as Frida to bypass it. Only do this with your own account and your own device.

## Derived values (computed by the integration)

| Value | Formula |
|---|---|
| Fuel (litres) | `Fuel % ÷ 100 × tank capacity` |
| Measured consumption (L/100 km) | Sum of `% of tank used ÷ 100 × tank capacity` over the last ~500 km, divided by the km driven. Refuel intervals are skipped. Needs 50 km. |
| Estimated range (km) | `litres ÷ measured consumption × 100`. Before 50 km of data: `litres ÷ ConsumptionAverage × 100`. |
| Moving | `Speed > 0` |
| ITV days left | `NextVTIDate − today` (negative if overdue) |
| OBD error count | number of codes where `Solved` is `false` |
