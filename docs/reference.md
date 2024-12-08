# Reference

## <a name="tiled-objects"></a>Tiled Objects

### Map

Map object (defined in [`TiledMap` class](../engine/tmx.py)) has two scriplets properties:

- "on_create" - if present it will be executed only once. The moment it is executed new property
  will be added to the map properties called '_on_create_executed' with value 'True'.
  When executed following local values are passed in:
  - 'level' - instance of the [`Level` class](../engine/level.py)

- "on_show" - if present it will be executed each time map is set to be 'main' map. That
  happens typically a beginning of the each 'level'/'map' in the game.

### Tiled Layer

Tiled layer [`TiledTileLayer` class](../engine/tmx.py) currently doesn't have any
special properties catered for.

### Object Layer

Object layer [`TiledObjectGroup` class](../engine/tmx.py) currently doesn't have any
special properties catered for.

### Object

Objects in object layer [`TiledObject` class](../engine/tmx.py) instances have following
scriplet properties handled:

- "on_create" - if present it will be executed each time map is set as a main map.
  When executed following local values are passed in:
  - 'level' - instance of the [`Level` class](../engine/level.py)
  - 'obj' - reference back to the object ([`TiledObject` class](../engine/tmx.py) instance)
    that is being 'created'

- "on_enter" - if present it will be executed when player tries to 'enter' - collide with the
  object.
  When executed following local values are passed in:
  - 'this' - player (or another moving object) that performed move and collided with the
    object in the object layer.
  - 'obj' - object that has been hit/tried to be collided with.

  **Note**: Normaly player is 'this' and hit object 'obj'

- "on_leave" - if present it will be executed when player stops being over this object - stops
  colliding with the object.

  When executed following local values are passed in:
  - 'this' - player (or another moving object) that performed move and stopped colliding with the
    object in the object layer.
  - 'obj' - object that has been hit/tried to be collided with.

  **Note**: Normaly player is 'this' and hit object 'obj'

- "on_collision" - if present it will be executed as long as player moves over the object.

  When executed following local values are passed in:
  - 'this' - player (or another moving object) that performed move and collided with the
    object in the object layer.
  - 'obj' - object that has been hit/tried to be collided with.

  **Note**: Normaly player is 'this' and hit object 'obj'

- "on_animate" - if present it will be executed every frame.

  When executed following local values are passed in:
  - 'this' - player (or another moving object) that performed move and collided with the
    object in the object layer.
  - 'obj' - object that has been hit/tried to be collided with.
  - 'elapsed_ms' - number of milliseconds that elapsed since last call.

  **Note**: Normaly player is 'this' and hit object 'obj'

- "on_click" - if present it will be executed when user clicks left mouse button on an object.

  When executed following local values are passed in:
  - 'obj' - object that has been clicked on.
  - 'pos' - x, y coordinates (on the screen) where click happened.


### TileSet

TODO

### Tile in TileSet

TODO

## <a name="game-context"></a>Game Context


