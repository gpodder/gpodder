# Contributing to this repository <!-- omit in toc -->

## Getting started <!-- omit in toc -->

Before you begin:
- Ensure you are using Python 3.7+
- Check out the [existing issues](https://github.com/gpodder/gpodder/issues)

Contributions are made to this repo via Issues and Pull Requests (PRs). Make sure to search for existing Issues and PRs before creating your own.


## Getting the code and setting up the project
1. Fork this project
2. Clone the repository to your machine
3. Create a separate branch to get started, e.g. for feature `feat/branch-name-here` or fix `fix/fix-name-goes-here`
4. Make sure to create a new virtual environment and activate it:
```shell
python3 -m venv venv
source activate venv/bin/activate
```
5. Install dependencies: [Run from Git](https://gpodder.github.io/docs/run-from-git.html)
6. Start the program with debug mode: `./bin/gpodder -v`
7. Make the changes, commit in a branch and push the branch to your fork and then submit a Pull Request.

## Linting
To ensure code quality, we recommend you to run the linter before pushing the changes to your repo. In order to do so ensure the necessary packages are installed by executing:
```shell
pip3 install pytest-cov minimock pycodestyle isort requests pytest pytest-httpserver
```
Execute the linter in the root directory (Linux only): `make lint unittest`. On Windows execute: `pycodestyle share src/gpodder tools bin/* *.py`
