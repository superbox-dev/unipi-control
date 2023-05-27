# Contributing

Thank you for investing your time in contributing to **Unipi Control**.

## Setting up an environment

Clone the `unipi-control` repository. Copy the [config files](data/opkg/data/local/etc/unipi) to your `/etc/unipi` directory and configurate the `/etc/unipi/control.yaml`.

Inside the repository, create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Install the development dependencies:

```bash
pip install -e .[lint,format,audit,tests]
```

Now you can start unipi-control with `unipi-control`.

## Testing

To test the code we use [pytest](https://docs.pytest.org):

```bash
pytest -n auto
```

To get the full test coverage report of `unipi-control`, run the following command:

```bash
pytest --cov-report term-missing --cov=unipi_control
```

## Making a pull request

When you're finished with the changes, create a pull request, also known as a PR.
The branch to contribute is `main`. Please also update the [CHANGELOG.md](CHANGELOG.md) with your changes.
