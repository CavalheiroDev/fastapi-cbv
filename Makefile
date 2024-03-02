PIP := pip install

PROJECT_NAME := fastapi-cbv
PYTHON_VERSION := 3.9.18
VENV_NAME := $(PROJECT_NAME)-$(PYTHON_VERSION)

# Environment setup
.pip:
	pip install --upgrade pip
	pip install -U "setuptools>=69.1.1,<70.0"

setup: .pip
	$(PIP) -e .

setup-dev: .pip
	$(PIP) -e .[dev]

.clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

.clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean: .clean-build .clean-pyc

.create-venv:
	pyenv install -s $(PYTHON_VERSION)
	pyenv uninstall -f $(VENV_NAME)
	pyenv virtualenv $(PYTHON_VERSION) $(VENV_NAME)
	pyenv local $(VENV_NAME)

create-venv: .create-venv setup-dev

# Repository
git-up:
	git pull
	git fetch -p --all

code-convention:
	flake8
	pycodestyle
