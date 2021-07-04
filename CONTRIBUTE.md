# Contributing

## Setup

This project use `pipenv` for managing the virtualenv and package dependencies.

Install [pyenv](https://github.com/pyenv/pyenv) and [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv)
by following the instructions.

Clone this git:
```bash
git clone https://github.com/rudexi/python-relp
cd python-relp
```

Install `pipenv`:
```bash
pip install pipenv
```

Install the version of python, as well as the package dependencies:
```bash
pipenv install --dev
```

## Testing

So far there is no unit testing.
Be sure to test the examples in `./examples/` work, for the python client
and the librelp client (used by rsyslog).
