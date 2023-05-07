# Commands

## unipi-control

**Usage:**

````bash
unipi-control [--log {systemd,stdout,file}] [--config CONFIG]
````

| Argument   | Description                                                                |
|------------|----------------------------------------------------------------------------|
| `--config` | path to the configuration (default: `/etc/unipi`)                            |
| `--log`    | set log handler to file or systemd (choices: `systemd`, `stdout` or `file` |
| `-v`       | verbose mode: multiple -v options increase the verbosity (maximum: 4)      |

## unipi-config-backup

Backup Unipi Control configuration

**Usage:**

```bash
unipi-config-backup [--log {systemd,stdout,file}] [--config CONFIG] output
```

| Argument   | Description                                                                |          |
|------------|----------------------------------------------------------------------------|----------|
| `output`   | path to save the backup file                                               | required |
| `--config` | path to the configuration (default: `/etc/unipi`)                          |          |
| `--log`    | set log handler to file or systemd (choices: `systemd`, `stdout` or `file` |          |
| `-v`       | verbose mode: multiple -v options increase the verbosity (maximum: 4)      |          |


## unipi-config-converter

Convert Evok to Unipi Control YAML file format.

**Usage:**

````bash
unipi-config-converter [--log {systemd,stdout,file}] [-v] [--force] input output
````

| Argument   | Description                                                                |          |
|------------|----------------------------------------------------------------------------|----------|
| `input`    | path to the evok YAML file                                                 | required |
| `output`   | path to save the converted YAML file                                       | required |
| `--force`  | overwrite output YAML file if already exists                               |          |
| `--log`    | set log handler to file or systemd (choices: `systemd`, `stdout` or `file` |          |
| `-v`       | verbose mode: multiple -v options increase the verbosity (maximum: 4)      |          |
