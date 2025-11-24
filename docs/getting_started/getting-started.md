# Getting Started

This is set of simple recipes how to start making a game with TileEngine - Tiled compatible 
editor and Tile Engine.

First open TileEngine editor and add tilesets.

For example here I've used https://kenney.nl free assets - more precisely
[Pixel Platformer](https://kenney.nl/assets/pixel-platformer). All kudos to Kenney
for sharing them and please at least attribute all free resources downloded form the internet.

![Add Tilesets](getting-started-1.gif "Add Tilesets")

Note: Make sure you know your tileset's tile size (width and height).

When you have imported tilesets, you can shape your level:

![Shape your level](getting-started-2.gif "Shape your level")

Next you can select a tileset to 'draw' with and start making your level. For instance:

![Draw](getting-started-3.gif "Draw")

Next step is to define 'player' and animation of player. To achieve that we'll add
a property called 'plaery' on player's tiles with value 'left,1' and 'left,2' a current tileset has only
images of player looking at left. If you defined only 'left' or only 'right' images, the engine
will create symmetrical opposite. That doesn't work with 'up' and 'down' values which still
can be added. If value has ',' after 'left', 'right', 'up' or 'down' it will be treated as
a frame in the animation.

![Player Tile](getting-started-4.gif "Player Tile")

Note: This property name 'player' is going to be matched to object's 'type' property. TileEngine
is really flexible and if 'type' property is not set on an object, it will use 'name' property instead.

Let's add player to the map:

![Player Object](getting-started-5.gif "Player Object")

Now we can ask TileEngine editor to create a boilerplate python game and run it for us:

![Create and Start Game](getting-started-6.gif "Create and Start Game")

This will add property called 'python_file' to the map itself:

![python_file](python_file_property.png "python_file")
