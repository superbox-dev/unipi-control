# MQTT topics

Available MQTT topics:

## Features

### Unipi Neuron

| Topic                                         | Response/Request | Description                                                                                          |
|-----------------------------------------------|------------------|------------------------------------------------------------------------------------------------------|
| `[device_name]/relay/ro_[1-9]_[0-9][0-9]/get` | `ON` or `OFF`    | Get a string with the value `ON` or `OFF` from this topic.                                           |
| `[device_name]/relay/do_[1-9]_[0-9][0-9]/get` | `ON` or `OFF`    | Get a string with the value `ON` or `OFF` from this topic.                                           |
| `[device_name]/input/di_[1-9]_[0-9][0-9]/get` | `ON` or `OFF`    | Get a string with the value `ON` or `OFF` from this topic.                                           |
| `[device_name]/relay/ro_[1-9]_[0-9][0-9]/set` | `ON` or `OFF`    | Send a string with the value `ON` or `OFF` to this topic. This enable or disable the selected relay. |
| `[device_name]/relay/do_[1-9]_[0-9][0-9]/set` | `ON` or `OFF`    | Send a string with the value `ON` or `OFF` to this topic. This enable or disable the selected relay. |

### Eastron SDM120M

| Topic                                                              | Unit  |
|--------------------------------------------------------------------|-------|
| `[device_name]/meter/voltage_[unit]/get`                           | V     |
| `[device_name]/meter/current[unit]/get`                            | A     |
| `[device_name]/meter/current_demand[unit]/get`                     | A     |
| `[device_name]/meter/maximum_current_demand[unit]/get`             | A     |
| `[device_name]/meter/active_power[unit]/get`                       | W     |
| `[device_name]/meter/total_system_power_demand[unit]/get`          | W     |
| `[device_name]/meter/maximum_total_system_power_demand[unit]/get`  | W     |
| `[device_name]/meter/import_system_power_demand[unit]/get`         | W     |
| `[device_name]/meter/maximum_import_system_power_demand[unit]/get` | W     |
| `[device_name]/meter/export_system_power_demand[unit]/get`         | W     |
| `[device_name]/meter/maximum_export_system_power_demand[unit]/get` | W     |
| `[device_name]/meter/apparent_power[unit]/get`                     | VA    |
| `[device_name]/meter/reactive_power[unit]/get`                     | var   |
| `[device_name]/meter/frequency[unit]/get`                          | Hz    |
| `[device_name]/meter/import_active_energy[unit]/get`               | kWh   |
| `[device_name]/meter/export_active_energy[unit]/get`               | kWh   |
| `[device_name]/meter/total_active_energy[unit]/get`                | kWh   |
| `[device_name]/meter/import_reactive_energy[unit]/get`             | kvarh |
| `[device_name]/meter/export_reactive_energy[unit]/get`             | kvarh |
| `[device_name]/meter/total_reactive_energy[unit]/get`              | kvarh |
| `[device_name]/meter/power_factor[unit]/get`                       |       |
| `[device_name]/meter/phase_angle[unit]/get`                        |       |

## Covers

| Topic                                                  | Response/Request                                    | Description                                                          |
|--------------------------------------------------------|-----------------------------------------------------|----------------------------------------------------------------------|
| `[device_name]/[object_id]/cover/[device_class]/state` | `open`, `opening`, `closing`, `closed` or `stopped` | Get the cover state.                                                 |
| `[device_name]/[object_id]/cover/[device_class]/set`          | `OPEN`, `CLOSE` or `STOP`                    | Send a string to control the cover.                                  |
| `[device_name]/[object_id]/cover/[device_class]/position`     | `0` to `100`                                 | Get the cover position. `100` is fully open and `0` is fully closed. |
| `[device_name]/[object_id]/cover/[device_class]/position/set` | `0` to `100`                                 | Send an integer to set the cover position.                           |
| `[device_name]/[object_id]/cover/[device_class]/tilt`         | `0` to `100`                                 | Get the tilt position. `100` is fully open and `0` is fully closed.  |
| `[device_name]/[object_id]/cover/[device_class]/tilt/set`     | `0` to `100`                                 | Send an integer to set the cover position.                           |
