# TileEngine

This is an engine/framework for making games using Pygame and Tiled map editor. See quick start and concepts below.

This project also provides cut down version of editor where Tiled is not available.

Tiled objects [reference docs](docs/reference.md#tiled-objects)

Game context [reference docs](docs/reference.md#game-context)

## Quick start

First create and activate a virtual environment with something like:

```bash
python -m venv venv
. venv/bin/python
```

Make sure you have installed Pygame:

```bash
pip install pygame
```

There are a couple of examples in `examples` folder. You can run them with:

```bash
python examples/side_scroller_main.py
```

or

```bash
python examples/top_down_main.py
```

## Documentation

For more documentation check following:
- [Concepts](docs/concepts.md)
- [Setting up project](docs/project-setup.md)
- [Available methods and variables in scriptles](docs/reference.md)
- [Recipes](docs/recipes.md)

## Editor

This editor is not meant to replace Tiled editor - it is built for envionments like
our Games Creators Club where school computers are locked down and we cannot get
Tiled to be installed there. It has enough functionality to create a game for the
TiledEngine.

To run editor just do:

```bash
python editor.py
```
