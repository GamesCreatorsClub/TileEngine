<?xml version="1.0" encoding="UTF-8"?>
<tileset name="tileset-tiles" tilewidth="18" tileheight="18" tilecount="180" columns="20">
 <image source="tilemap_packed.png" width="360" height="162"/>
 <tile id="25">
  <objectgroup id="2" draworder="index">
   <object id="1" type="" x="0" y="0" width="18" height="18"/>
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
  <objectgroup id="2" draworder="index">
   <object id="1" type="" x="0" y="8" width="17" height="9">
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
  <objectgroup id="2" draworder="index">
   <object id="1" type="" x="2" y="6" width="12" height="9"/>
  </objectgroup>
 </tile>
 <tile id="143">
  <objectgroup id="2" draworder="index">
   <object id="1" type="" x="0" y="0" width="17" height="18"/>
  </objectgroup>
 </tile>
 <tile id="150">
  <objectgroup id="2" draworder="index">
   <object id="1" type="" x="0" y="0" width="17" height="18"/>
  </objectgroup>
 </tile>
 <tile id="151">
   <properties>
    <property name="animated_id" type="int" value="152"/>
    <property name="on_collision">remove_collided_object()
player[&quot;add_coin&quot;]()
</property>
   </properties>
  <objectgroup id="3" draworder="index">
   <object id="2" type="" x="2" y="2" width="12" height="12"/>
  </objectgroup>
 </tile>
 <tile id="152">
   <properties>
    <property name="animated_id" type="int" value="151"/>
    <property name="on_collision">remove_collided_object()
player[&quot;add_coin&quot;]()</property>
   </properties>
  <objectgroup id="2" draworder="index">
   <object id="1" type="" x="5" y="2" width="7" height="12"/>
  </objectgroup>
 </tile>
</tileset>
