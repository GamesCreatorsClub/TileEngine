<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.9" tiledversion="1.9.2" name="tileset-tiles" tilewidth="18" tileheight="18" tilecount="180" columns="20">
 <image source="tilemap_packed.png" width="360" height="162"/>
 <tile id="25">
  <objectgroup draworder="index" id="2">
   <object id="1" x="0.0728745" y="0.0728745" width="18" height="18"/>
  </objectgroup>
 </tile>
 <tile id="34">
  <properties>
   <property name="animated_id" type="int" value="35"/>
   <property name="on_collision">if obj == player:
    player.vy = 2
    next_rect.y += player.vy
    next_rect.x += (tile_rect.midtop[0] - next_rect.midtop[0])
</property>
  </properties>
 </tile>
 <tile id="35">
  <properties>
   <property name="animated_id" type="int" value="34"/>
   <property name="on_collision">if obj == player:
    player.vy = 2
    next_rect.y += player.vy
    next_rect.x += (tile_rect.midtop[0] - next_rect.midtop[0])
</property>
  </properties>
 </tile>
 <tile id="54">
  <properties>
   <property name="animated_id" type="int" value="55"/>
   <property name="on_collision">if obj == player:
    player.vy = 2
    next_rect.y += player.vy
    next_rect.x += (tile_rect.midtop[0] - next_rect.midtop[0])
</property>
  </properties>
 </tile>
 <tile id="55">
  <properties>
   <property name="animated_id" type="int" value="54"/>
   <property name="on_collision">if obj == player:
    player.vy = 2
    next_rect.y += player.vy
    next_rect.x += (tile_rect.midtop[0] - next_rect.midtop[0])
</property>
  </properties>
 </tile>
 <tile id="68">
  <properties>
   <property name="on_collision">hurt_player(1)
next_rect.x = player.rect.x + 3 * (player.rect.x - next_rect.x)
next_rect.y = player.rect.y + 3 * (player.rect.y - next_rect.y)</property>
  </properties>
  <objectgroup draworder="index" id="2">
   <object id="1" x="0" y="8.96356" width="17.7814" height="9.10931">
    <properties>
     <property name="on_collision" value="player.hurt(1)"/>
    </properties>
   </object>
  </objectgroup>
 </tile>
 <tile id="74">
  <properties>
   <property name="animated_id" type="int" value="75"/>
  </properties>
 </tile>
 <tile id="75">
  <properties>
   <property name="animated_id" type="int" value="74"/>
  </properties>
 </tile>
 <tile id="111">
  <properties>
   <property name="animated_id" type="int" value="112"/>
   <property name="level_end" type="bool" value="true"/>
  </properties>
 </tile>
 <tile id="112">
  <properties>
   <property name="animated_id" type="int" value="111"/>
  </properties>
 </tile>
 <tile id="128">
  <objectgroup draworder="index" id="2">
   <object id="1" x="2.98785" y="6.04858" width="12.0972" height="9.54656"/>
  </objectgroup>
 </tile>
 <tile id="143">
  <objectgroup draworder="index" id="2">
   <object id="1" x="0.145749" y="0.0728745" width="17.8543" height="18"/>
  </objectgroup>
 </tile>
 <tile id="150">
  <objectgroup draworder="index" id="2">
   <object id="1" x="0.0728745" y="0.0728745" width="17.9271" height="18"/>
  </objectgroup>
 </tile>
 <tile id="151">
  <properties>
   <property name="animated_id" type="int" value="152"/>
   <property name="on_collision">remove_collided_object()
add_coins(1)</property>
  </properties>
  <objectgroup draworder="index" id="3">
   <object id="2" x="2.84211" y="2.91498" width="12.0972" height="12.17"/>
  </objectgroup>
 </tile>
 <tile id="152">
  <properties>
   <property name="animated_id" type="int" value="151"/>
   <property name="on_collision">remove_collided_object()
add_coins(1)</property>
  </properties>
  <objectgroup draworder="index" id="2">
   <object id="1" x="5.10121" y="2.84211" width="7.87045" height="12.0972"/>
  </objectgroup>
 </tile>
</tileset>
