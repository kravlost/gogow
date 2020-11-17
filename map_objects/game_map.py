import tcod as libtcod
from random import randint, random

from components.ai import BasicMonster
from components.equipment import EquipmentSlots
from components.equippable import Equippable
from components.fighter import Fighter
from components.item import Item
from components.item_functions import cast_confuse, cast_fireball, cast_lightning, heal
from components.stairs import Stairs

from game_messages import Message

from entity import Entity
from map_objects.rectangle import Rect
from map_objects.tile import Tile
from render_functions import RenderOrder
from random_utils import from_dungeon_level, random_choice_from_dict

class GameMap:
    def __init__(self, width, height, dungeon_level=1):
        self.width = width
        self.height = height
        self.tiles = self.initialize_tiles()

        self.dungeon_level = dungeon_level

    def initialize_tiles(self):
        tiles = [[Tile(True) for y in range(self.height)] for x in range(self.width)]

        return tiles

    def make_map(self, max_rooms, room_min_size, room_max_size, 
        map_width, map_height, 
        player, entities):

        rooms = []
        num_rooms = 0

        center_of_last_room_x = None
        center_of_last_room_y = None

        for _ in range(max_rooms):
            # random width and height
            w = randint(room_min_size, room_max_size)
            h = randint(room_min_size, room_max_size)
            # random position without going out of the boundaries of the map
            x = randint(0, map_width - w - 1)
            y = randint(0, map_height - h - 1)
                        
            # "Rect" class makes rectangles easier to work with
            new_room = Rect(x, y, w, h)

            # run through the other rooms and see if they intersect with this one
            for other_room in rooms:
                if new_room.intersect(other_room):
                    break
            else:
                # this means there are no intersections, so this room is valid

                # "paint" it to the map's tiles
                self.create_room(new_room)

                # center coordinates of new room, will be useful later
                (new_x, new_y) = new_room.center()

                center_of_last_room_x = new_x
                center_of_last_room_y = new_y

                if num_rooms == 0:
                    # this is the first room, where the player starts at
                    player.x = new_x
                    player.y = new_y
                else:
                    # all rooms after the first:
                    # connect it to the previous room with a tunnel

                    # center coordinates of previous room
                    (prev_x, prev_y) = rooms[num_rooms - 1].center()

                    # flip a coin (random number that is either 0 or 1)
                    if randint(0, 1) == 1:
                        # first move horizontally, then vertically
                        self.create_h_tunnel(prev_x, new_x, prev_y)
                        self.create_v_tunnel(prev_y, new_y, new_x)
                    else:
                        # first move vertically, then horizontally
                        self.create_v_tunnel(prev_y, new_y, prev_x)
                        self.create_h_tunnel(prev_x, new_x, new_y)

                self.place_entities(new_room, entities)

                # finally, append the new room to the list
                rooms.append(new_room)
                num_rooms += 1

        stairs_component = Stairs(self.dungeon_level + 1)
        down_stairs = Entity(center_of_last_room_x, center_of_last_room_y, '>', libtcod.white, 'Stairs',
                             render_order=RenderOrder.STAIRS, stairs=stairs_component)
        
        entities.append(down_stairs)

    def create_room(self, room):
        # go through the tiles in the rectangle and make them passable
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                self.tiles[x][y].blocked = False
                self.tiles[x][y].block_sight = False

    def create_h_tunnel(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.tiles[x][y].blocked = False
            self.tiles[x][y].block_sight = False

    def create_v_tunnel(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.tiles[x][y].blocked = False
            self.tiles[x][y].block_sight = False

    def place_entities(self, room, entities):
        max_monsters_per_room = from_dungeon_level([[2, 1], [3, 4], [5, 6]], self.dungeon_level)
        max_items_per_room = from_dungeon_level([[1, 1], [2, 4]], self.dungeon_level)

        number_of_monsters = randint(0, max_monsters_per_room)
        number_of_items = randint(0, max_items_per_room)

        monster_chances = {
            'orc': 80,
            'troll': from_dungeon_level([[15, 3], [30, 5], [60, 7]], self.dungeon_level)
        }

        item_chances = {
            'healing_potion': 35,
            'sword': from_dungeon_level([[5, 4]], self.dungeon_level),
            'shield': from_dungeon_level([[15, 8]], self.dungeon_level),
            'lightning_scroll': from_dungeon_level([[25, 4]], self.dungeon_level),
            'fireball_scroll': from_dungeon_level([[25, 6]], self.dungeon_level),
            'confusion_scroll': from_dungeon_level([[10, 2]], self.dungeon_level)
        }

        for _ in range(number_of_monsters):
            # Choose a random location in the room
            x = randint(room.x1 + 1, room.x2 - 1)
            y = randint(room.y1 + 1, room.y2 - 1)

            if not any([entity for entity in entities if entity.x == x and entity.y == y]):
                monster_choice = random_choice_from_dict(monster_chances)

                if monster_choice == 'orc':
                    fighter_component = Fighter(hp=20, defense=0, power=4, xp=35)
                    ai_component = BasicMonster()

                    monster = Entity(x, y, 'o', libtcod.desaturated_green, 'Ork', blocks=True,
                        render_order=RenderOrder.ACTOR, fighter=fighter_component, ai=ai_component)
                else:
                    fighter_component = Fighter(hp=30, defense=2, power=8, xp=100)
                    ai_component = BasicMonster()

                    monster = Entity(x, y, 'T', libtcod.darker_green, 'Troll', blocks=True,
                        render_order=RenderOrder.ACTOR, fighter=fighter_component, ai=ai_component)

                entities.append(monster)

        for _ in range(number_of_items):
            x = randint(room.x1 + 1, room.x2 - 1)
            y = randint(room.y1 + 1, room.y2 - 1)

            if not any([entity for entity in entities if entity.x == x and entity.y == y]):
                item_choice = random_choice_from_dict(item_chances)

                if item_choice == 'healing_potion':
                    item_component = Item(use_function=heal, amount=40)
                    item = Entity(x, y, '!', libtcod.violet, 'Ismek Yaghes', render_order=RenderOrder.ITEM,
                                  item=item_component)
                elif item_choice == 'sword':
                    equippable_component = Equippable(EquipmentSlots.MAIN_HAND, power_bonus=3)
                    item = Entity(x, y, '/', libtcod.sky, 'Kledha', equippable=equippable_component)
                elif item_choice == 'shield':
                    equippable_component = Equippable(EquipmentSlots.OFF_HAND, defense_bonus=1)
                    item = Entity(x, y, '[', libtcod.darker_orange, 'Skoos', equippable=equippable_component)
                elif item_choice == 'fireball_scroll':
                    item_component = Item(use_function=cast_fireball, targeting=True, targeting_message=Message(
                        'Kledh-klyckya leghen rag an pel tan, po deghow-klyckya dhe nagha.', libtcod.light_cyan),
                                          damage=25, radius=3)
                    item = Entity(x, y, '#', libtcod.red, 'Hus Pel Tan', render_order=RenderOrder.ITEM,
                                  item=item_component)
                elif item_choice == 'confusion_scroll':
                    item_component = Item(use_function=cast_confuse, targeting=True, targeting_message=Message(
                        'Kledh-klyckya eskar dh\'y sowdheni, po deghow-klyckya dhe nagha.', libtcod.light_cyan))
                    
                    item = Entity(x, y, '#', libtcod.light_pink, 'Hus Sowdhan', render_order=RenderOrder.ITEM,
                                  item=item_component)
                else:
                    item_component = Item(use_function=cast_lightning, damage=40, maximum_range=5)
                    
                    item = Entity(x, y, '#', libtcod.yellow, 'Hus Lughes', render_order=RenderOrder.ITEM,
                                  item=item_component)
                
                entities.append(item)

    def is_blocked(self, x, y):
        if self.tiles[x][y].blocked:
            return True

        return False

    def next_floor(self, player, message_log, constants):
        self.dungeon_level += 1
        entities = [player]

        self.tiles = self.initialize_tiles()
        self.make_map(constants['max_rooms'], constants['room_min_size'], constants['room_max_size'],
                      constants['map_width'], constants['map_height'], player, entities)

        player.fighter.heal(player.fighter.max_hp // 2)

        message_log.add_message(Message('Ty a bowes pols, ha daskavos dha nerth.', libtcod.light_violet))

        return entities

#     def make_bsp(self, constants, player, entities):
#         global map, objects, stairs, bsp_rooms
    
#         objects = [player]
    
#         map = [[Tile(True) for y in range(constants['map_height'])] for x in range(constants['map_width'])]
    
#         #Empty global list for storing room coordinates
#         bsp_rooms = []
    
#         #New root node
#         bsp = libtcod.bsp_new_with_size(0, 0, constants['map_width'], constants['map_height'])
    
#         #Split into nodes
#         libtcod.bsp_split_recursive(bsp, 0, constants['bsp_depth'], 
#             constants['bsp_min_size'] + 1, constants['bsp_min_size'] + 1, 1.5, 1.5)
    
#         #Traverse the nodes and create rooms                            
#         libtcod.bsp_traverse_inverted_level_order(bsp, traverse_node)
    
#         #Random room for the stairs
#         stairs_location = random.choice(bsp_rooms)
#         bsp_rooms.remove(stairs_location)
#         stairs = Object(stairs_location[0], stairs_location[1], '<', 'stairs', libtcod.white, always_visible=True)
#         objects.append(stairs)
#         stairs.send_to_back()
    
#         #Random room for player start
#         player_room = random.choice(bsp_rooms)
#         bsp_rooms.remove(player_room)
#         player.x = player_room[0]
#         player.y = player_room[1]
    
#         #Add monsters and items
#         for room in bsp_rooms:
#             new_room = Rect(room[0], room[1], 2, 2)
#             place_objects(new_room)
    
#         initialize_fov()


# def traverse_node(node, dat):
#     global map, bsp_rooms
 
#     #Create rooms
#     if libtcod.bsp_is_leaf(node):
#         minx = node.x + 1
#         maxx = node.x + node.w - 1
#         miny = node.y + 1
#         maxy = node.y + node.h - 1
 
#         if maxx == MAP_WIDTH - 1:
#             maxx -= 1
#         if maxy == MAP_HEIGHT - 1:
#             maxy -= 1
 
#         #If it's False the rooms sizes are random, else the rooms are filled to the node's size
#         if FULL_ROOMS == False:
#             minx = libtcod.random_get_int(None, minx, maxx - MIN_SIZE + 1)
#             miny = libtcod.random_get_int(None, miny, maxy - MIN_SIZE + 1)
#             maxx = libtcod.random_get_int(None, minx + MIN_SIZE - 2, maxx)
#             maxy = libtcod.random_get_int(None, miny + MIN_SIZE - 2, maxy)
 
#         node.x = minx
#         node.y = miny
#         node.w = maxx-minx + 1
#         node.h = maxy-miny + 1
 
#         #Dig room
#         for x in range(minx, maxx + 1):
#             for y in range(miny, maxy + 1):
#                 map[x][y].blocked = False
#                 map[x][y].block_sight = False
 
#         #Add center coordinates to the list of rooms
#         bsp_rooms.append(((minx + maxx) / 2, (miny + maxy) / 2))
 
#     #Create corridors    
#     else:
#         left = libtcod.bsp_left(node)
#         right = libtcod.bsp_right(node)
#         node.x = min(left.x, right.x)
#         node.y = min(left.y, right.y)
#         node.w = max(left.x + left.w, right.x + right.w) - node.x
#         node.h = max(left.y + left.h, right.y + right.h) - node.y
#         if node.horizontal:
#             if left.x + left.w - 1 < right.x or right.x + right.w - 1 < left.x:
#                 x1 = libtcod.random_get_int(None, left.x, left.x + left.w - 1)
#                 x2 = libtcod.random_get_int(None, right.x, right.x + right.w - 1)
#                 y = libtcod.random_get_int(None, left.y + left.h, right.y)
#                 vline_up(map, x1, y - 1)
#                 hline(map, x1, y, x2)
#                 vline_down(map, x2, y + 1)
 
#             else:
#                 minx = max(left.x, right.x)
#                 maxx = min(left.x + left.w - 1, right.x + right.w - 1)
#                 x = libtcod.random_get_int(None, minx, maxx)
 
#                 # catch out-of-bounds attempts
#                 while x > MAP_WIDTH - 1:
#                         x -= 1
 
#                 vline_down(map, x, right.y)
#                 vline_up(map, x, right.y - 1)
 
#         else:
#             if left.y + left.h - 1 < right.y or right.y + right.h - 1 < left.y:
#                 y1 = libtcod.random_get_int(None, left.y, left.y + left.h - 1)
#                 y2 = libtcod.random_get_int(None, right.y, right.y + right.h - 1)
#                 x = libtcod.random_get_int(None, left.x + left.w, right.x)
#                 hline_left(map, x - 1, y1)
#                 vline(map, x, y1, y2)
#                 hline_right(map, x + 1, y2)
#             else:
#                 miny = max(left.y, right.y)
#                 maxy = min(left.y + left.h - 1, right.y + right.h - 1)
#                 y = libtcod.random_get_int(None, miny, maxy)
 
#                 # catch out-of-bounds attempts
#                 while y > MAP_HEIGHT - 1:
#                          y -= 1
 
#                 hline_left(map, right.x - 1, y)
#                 hline_right(map, right.x, y)
 
#     return True

# def vline(map, x, y1, y2):
#     if y1 > y2:
#         y1,y2 = y2,y1
 
#     for y in range(y1,y2+1):
#         map[x][y].blocked = False
#         map[x][y].block_sight = False
 
# def vline_up(map, x, y):
#     while y >= 0 and map[x][y].blocked == True:
#         map[x][y].blocked = False
#         map[x][y].block_sight = False
#         y -= 1
 
# def vline_down(map, x, y):
#     while y < MAP_HEIGHT and map[x][y].blocked == True:
#         map[x][y].blocked = False
#         map[x][y].block_sight = False
#         y += 1
 
# def hline(map, x1, y, x2):
#     if x1 > x2:
#         x1,x2 = x2,x1
#     for x in range(x1,x2+1):
#         map[x][y].blocked = False
#         map[x][y].block_sight = False
 
# def hline_left(map, x, y):
#     while x >= 0 and map[x][y].blocked == True:
#         map[x][y].blocked = False
#         map[x][y].block_sight = False
#         x -= 1
 
# def hline_right(map, x, y):
#     while x < MAP_WIDTH and map[x][y].blocked == True:
#         map[x][y].blocked = False
#         map[x][y].block_sight = False
#         x += 1