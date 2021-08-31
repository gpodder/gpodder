# Contributing to this repository <!-- omit in toc -->

## Getting started <!-- omit in toc -->

Before you begin:
- Ensure you are using Python 3.5+
- Check out the [existing issues](https://github.com/gpodder/gpodder/issues)

Contributions are made to this repo via Issues and Pull Requests (PRs). Make sure to search for existing Issues and PRs before creating your own.


## Getting the code and setting up the project
1. Fork this project
2. Clone the repository to your machine
3. Create a separate branch to get started, e.g. for feature `feat/branch-name-here` or fix `fix/fix-name-goes-here`
4. Make sure to create a new virtual environment and activate it:
```shell
$ python3 -m venv venv
$ source activate venv/bin/activate
```
5. Install dependencies: `python3 tools/localdepends.py`
6. Start the program with debug mode: `./bin/gpodder -v`
7. Make the changes, commit in a branch and push the branch to your fork and then submit a Pull Request.