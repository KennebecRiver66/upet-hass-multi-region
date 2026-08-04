# UPET / Airrobo Cat Litter Box (Multi-Region) for Home Assistant

## EN

This fork was created because the original integration currently appears to be unmaintained, and attempts to contact its author have not received a response.

It adds a country selection dialog during setup and routes requests to the appropriate regional UPET server. In particular, this resolves the misleading **“Authentication failed. Check account and password.”** error affecting accounts whose region is set to Russia.

A huge thank you to [@CrazzyBerg](https://github.com/CrazzyBerg), the author of the [original integration](https://github.com/CrazzyBerg/upet-hass). They did the hard work that made this project possible; this fork builds on that foundation rather than replacing it. ❤️

And, of course, thank you to ❤️**UPET / Airrobo**❤️ for creating the hardware and app that inspired this community integration. If your cat needs a smarter throne, please consider supporting the people who made it by choosing an official UPET / Airrobo litter box. 🐈💩

Custom Home Assistant integration for UPET / Airrobo smart cat litter boxes.

## RU

Этот форк был создан, поскольку оригинальная интеграция, судя по всему, больше не поддерживается, а попытки связаться с её автором остались без ответа.

В форк добавлен диалог выбора страны при настройке, а запросы направляются на соответствующий региональный сервер UPET. В частности, это исправляет ошибочное сообщение **«Authentication failed. Check account and password.»**, которое появлялось при использовании аккаунтов с регионом Россия.

Огромная благодарность [@CrazzyBerg](https://github.com/CrazzyBerg), автору [оригинальной интеграции](https://github.com/CrazzyBerg/upet-hass). Именно он проделал основную работу, благодаря которой этот проект стал возможен; данный форк развивает заложенную им основу, а не заменяет её. ❤️

И, конечно, спасибо ❤️**UPET / Airrobo**❤️ за устройства и приложение, вдохновившие сообщество на создание этой интеграции. Если вашему коту нужен более умный трон, поддержите его создателей, выбрав официальный кошачий лоток UPET / Airrobo. 🐈💩

Пользовательская интеграция Home Assistant для умных кошачьих лотков UPET / Airrobo.

This integration uses the vendor cloud API for account/device data and the vendor IM/MQTT channel for live work commands and work-state polling.

## Warning

This is an unofficial integration and is not affiliated with, endorsed by, or supported by UPET, Airrobo, or the vendor.

Use it at your own risk. The integration depends on private vendor APIs and may stop working or trigger vendor-side account restrictions at any time. I am not responsible for blocked accounts, lost access, device issues, or any other consequences of using this integration.

For safer use, create a separate UPET/Airrobo account and share litter box access to that account instead of using your primary account.

## Features

- Account login with UPET/Airrobo credentials.
- Device discovery from the vendor cloud account.
- Read-only box, waste-bin, deodorant, online, and firmware data.
- Cat profile sensors and cat picture URL attributes when returned by the API.
- Config controls for confirmed settings:
  - Auto clean delay.
  - Auto clean on/off.
  - Deodorant alert.
  - Empty waste-bin reminder switch, time, and weekdays.
  - Do not disturb schedule.
  - Light schedule.
- MQTT work commands:
  - Start clean.
  - Pause clean.
  - Resume clean.
  - Flatten.
  - Pause flatten.
  - Resume flatten.
  - Raise litter rake.
  - Lower litter rake.
  - Request MQTT state.
- Live MQTT work status:
  - Work mode.
  - Work state.
  - Work cause.
  - Last successful MQTT status update.
- Diagnostics download with sanitized raw API/coordinator data.
- Local brand icons for supported Home Assistant versions.

## Installation

Install through HACS as a custom repository:

1. Open HACS in Home Assistant.
2. Go to `Integrations`.
3. Open the three-dot menu and choose `Custom repositories`.
4. Add `https://github.com/PnnnG/upet-hass-multi-region`.
5. Select category `Integration`.
6. Install `UPET / Airrobo Cat Litter Box (Multi-Region)`.

Restart Home Assistant after installation.

Manual installation is also possible by copying this repository's
`custom_components/ubpet` directory into your Home Assistant config directory:

```bash
<config>/custom_components/ubpet
```

Add the integration from Home Assistant:

```text
Settings -> Devices & services -> Add integration -> UPET / Airrobo Cat Litter Box (Multi-Region)
```

## Configuration

Required fields:

- `Country`: select the same country that is configured in the official UPET app.
- `Account`: UPET/Airrobo login account.
- `Password`: plain account password. The integration hashes it internally before sending it to the API.

The integration selects the regional API endpoint from the chosen country. It also needs these vendor app/API fields:

- `APP_ID`
- `APP_KEY`
- `PRODUCT`

Bundled app defaults are included with the integration, so normal setup asks
only for country, account, and password. Sensitive app defaults are stored in
obfuscated form to keep raw values out of the repository.

If you maintain a private deployment and want to override the bundled defaults,
use `custom_components/ubpet/secrets.py.example` as a template for a private
`secrets.py`.

## Entities

Device sensors:

- Box status.
- Empty waste-bin reminder days.
- Box use times.
- Waste-bin level.
- Waste-bin last reset.
- Box full max.
- Box full alert.
- Deodorant remaining days.
- Auto clean delay.
- Firmware version.
- Wi-Fi name.
- MQTT work mode.
- MQTT work state.
- MQTT work cause.
- Last REST update.
- Last MQTT update.

Device binary sensors:

- Online.
- Deodorant expired.
- Sensor enabled.
- Camera enabled.
- Child lock.

Device controls:

- Auto clean delay number.
- Auto clean switch.
- Deodorant alert switch.
- Empty waste-bin reminder switch.
- Empty waste-bin reminder time.
- Empty waste-bin reminder weekday select.
- Do not disturb switch and start/end times.
- Light schedule switch and start/end times.

Device buttons:

- REST request.
- MQTT request state.
- Reset waste-bin counter.
- Start clean.
- Pause clean.
- Resume clean.
- Flatten.
- Pause flatten.
- Resume flatten.
- Raise litter rake.
- Lower litter rake.

Cat sensors:

- Weight.
- Visits.
- Usage duration.

Cat picture URLs are exposed as cat entity attributes when returned by the vendor API.

## MQTT Behavior

Work commands are sent through the vendor IM/MQTT path, not REST.

The integration obtains MQTT credentials and topics from the vendor API, publishes command payloads to the IM publish topic, and polls `request_state` for live work status.

Polling intervals:

- `RUNNING`: every 1 second.
- `PAUSED`: every 10 seconds.
- `PENDING`/standby/unknown: every 60 seconds.

MQTT polling starts after Home Assistant finishes setting up the integration, so startup is not blocked by MQTT traffic.

## Confirmed MQTT Commands

Current service ids and operation payload bodies:

| Service id | Meaning | Operation body |
| --- | --- | --- |
| `start_clean_up` | Start clean | `08011001` |
| `pause_clean_up` | Pause clean | `08011002` |
| `resume_clean_up` | Resume clean | `08011003` |
| `start_flatten` | Flatten / smoothing | `08031001` |
| `pause_flatten` | Pause flatten | `08031002` |
| `resume_flatten` | Resume flatten | `08031003` |
| `start_rise` | Raise litter rake | `08071001` |
| `start_drop` | Lower litter rake | `08081001` |

Confirmed operation ordinals:

- `CLEAN = 1`
- `SMOOTHING = 3`
- `RISE = 7`
- `DROP = 8`
- `START = 1`
- `PAUSE = 2`
- `RESUME = 3`

## Limitations

- The integration depends on the vendor cloud and vendor IM/MQTT service.
- Commands are confirmed by MQTT delivery/status responses, but full semantic validation of every receipt/error cause is not complete.
- Control board / child lock is currently exposed as read-only because the observed API flow returns a permission error for writes.
- Deodorize, direct light control, camera toggle, and full-alert threshold controls are not implemented yet.

## Development

Run dependency-free tests:

```bash
python3 -m unittest discover -s tests -v
```

Run quick checks:

```bash
python3 -m unittest tests.test_mqtt tests.test_api
python3 -m py_compile custom_components/ubpet/*.py
python3 -m json.tool custom_components/ubpet/strings.json >/tmp/ubpet_strings.json
python3 -m json.tool custom_components/ubpet/translations/en.json >/tmp/ubpet_en.json
python3 -m json.tool custom_components/ubpet/translations/uk.json >/tmp/ubpet_uk.json
```

The current tests cover:

- API signing and password hashing.
- Account type fallback.
- Authenticated request headers.
- Dashboard aggregation.
- Settings payload builders.
- IM credential/contact lookup.
- MQTT codec, packet helpers, RISP/protobuf payload generation, and service ordinals.
- Diagnostics redaction.

## Implementation Notes

Implemented REST endpoints:

- `PUT /user-service-rest/v2/user/login`
- `GET /user-service-rest/v2/robot/common/device/list`
- `GET /catbox-server/box/config/allConfig?serialNumber=...`
- `GET /catbox-server/box/config/box-use-times/?serialNumber=...`
- `PUT /catbox-server/box/config/box-use-times/reset`
- `GET /catbox-server/app/deodorant-block/status?serialNumber=...`
- `GET /v1/ubtechinc-im-manager/im/online/device/?sn=...`
- `POST /v1/ubtechinc-im-manager/im/login`
- `GET /v1/ubtechinc-im-manager/im/friends`
- `GET /catbox-server/web/cat/info`
- `POST /catbox-server/web/box/record/new`
- `PUT /catbox-server/box/config/switch/update`
- `PUT /catbox-server/box/config/timePeriod/update`
- `PUT /catbox-server/box/config/timePoint/update`
- `POST /catbox-server/app/deodorant-block/switch`

MQTT command format:

```text
Message -> MessageContent(custom) -> Any(BytesValue) -> CommandProto(protype=2) -> RISP frame -> AirPet protobuf body
```

MQTT state request uses RISP command `0x3fd`. Operation commands use RISP command `0x3fb`.

## Roadmap

Planned or open work:

- Decode more MQTT receipt/error causes and surface command failures more clearly.
- Implement deodorize command if available.
- Implement full-alert threshold setting.
- Implement writable control board / child lock if a permitted API flow is found.
- Add Home Assistant platform tests with `pytest-homeassistant-custom-component`.
