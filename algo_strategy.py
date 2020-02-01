import gamelib
import random
import math
import warnings
from sys import maxsize
import json

class AlgoStrategy(gamelib.AlgoCore):
    def __init__(self):
        super().__init__()
        seed = random.randrange(maxsize)
        random.seed(seed)
        gamelib.debug_write('Random seed: {}'.format(seed))

    def on_game_start(self, config):
        """ 
        Read in config and perform any initial setup here 
        """
        gamelib.debug_write('Configuring your custom algo strategy...')
        self.config = config
        global FILTER, ENCRYPTOR, DESTRUCTOR, PING, EMP, SCRAMBLER, BITS, CORES
        FILTER = config["unitInformation"][0]["shorthand"]
        ENCRYPTOR = config["unitInformation"][1]["shorthand"]
        DESTRUCTOR = config["unitInformation"][2]["shorthand"]
        PING = config["unitInformation"][3]["shorthand"]
        EMP = config["unitInformation"][4]["shorthand"]
        SCRAMBLER = config["unitInformation"][5]["shorthand"]
        BITS = 1
        CORES = 0
        # This is a good place to do initial setup
        self.scored_on_locations = []
        self.ENEMY_HEALTH = 30;
        self.ENCRYPTOR_COUNT = 0;
        self.ENEMY_ENCRYPTOR_COUNT = 0;
        self.NEED_ENCRYPTORS = False;

    def on_turn(self, turn_state):
        """
        This function is called every turn with the game state wrapper as
        an argument. The wrapper stores the state of the arena and has methods
        for querying its state, allocating your current resources as planned
        unit deployments, and transmitting your intended deployments to the
        game engine.
        """
        game_state = gamelib.GameState(self.config, turn_state)
        gamelib.debug_write('Performing turn {} of your custom algo strategy'.format(game_state.turn_number))
        game_state.suppress_warnings(True)  # Comment or remove this line to enable warnings.

        self.starter_strategy(game_state)

        game_state.submit_turn()

    def starter_strategy(self, game_state):
        

        self.build_defences(game_state)

        #TODO better heuristic for seeing if firing is worthwhile... do real tracking ... can help us fire earlier too
        ping_count  = game_state.get_resource(BITS)//1;
        bit_increment = (game_state.turn_number // 10) + 5
        ping_spawn_location_options = [[11, 2], [16, 2]]

        if self.can_ping(game_state, ping_count, ping_spawn_location_options) and self.ENEMY_HEALTH-ping_count < 5 and self.ENEMY_HEALTH-ping_count > 0:
            gamelib.debug_write("Stalling")
        elif self.can_ping(game_state, ping_count, ping_spawn_location_options) and ping_count > 12:
            best_location = self.least_damage_spawn_location(game_state, ping_spawn_location_options)
            game_state.attempt_spawn(PING, best_location, 1000);
        elif not self.can_ping(game_state, ping_count, ping_spawn_location_options):
            if ping_count > 18:     
                best_location = self.least_damage_spawn_location(game_state, ping_spawn_location_options)
                game_state.attempt_spawn(EMP, best_location, 1000);

    def can_ping(self, game_state, ping_count, location_options):
        can_tank = 1+(15 + 3*self.ENCRYPTOR_COUNT)//16;
        total_hits = can_tank*ping_count;
        min_hits = self.determine_min_hitcount(game_state, location_options);
        netval = total_hits - min_hits;
        gamelib.debug_write("min hit "+ str(min_hits));
        gamelib.debug_write("total hit "+ str(total_hits));
        return netval>0 and not self.blocked_path(game_state,self.least_damage_spawn_location(game_state,location_options));

    def blocked_path(self, game_state, location):
        path = game_state.find_path_to_edge(location)
        target_edge = game_state.get_target_edge(location);
        edgelist = game_state.game_map.get_edge_locations(target_edge)
        endpoint = path[-1];
        return endpoint not in edgelist;

    def determine_min_hitcount(self, game_state, location_options):
        damages = []
        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0));
            damages.append(damage)

        return min(damages);

    def filter_blocked_locations(self, locations, game_state):
        filtered = []
        for location in locations:
            if not game_state.contains_stationary_unit(location):
                filtered.append(location)
        return filtered

    def nearby_destructor(self,game_state, l, destructor_locations):
        nearby_locs = [[l[0],l[1]-1], [l[0]-1,l[1]-1] , [l[0]+1,l[1]-1], [l[0]+1,l[1]], [l[0]-1,l[1]]];
        for i in nearby_locs:
            if game_state.contains_stationary_unit(i) and i in destructor_locations:
                return True;
        return False;
    def build_defences(self, game_state):
        # Useful tool for setting up your base locations: https://www.kevinbai.design/terminal-map-maker
        # More community tools available at: https://terminal.c1games.com/rules#Download
        encryptor_locations = [[7, 8], [20, 8], [8, 7], [19, 7], [9, 6], [18, 6], [10, 5], [17, 5], [11, 4], [16, 4], [12, 3], [15, 3], [13, 2], [14, 2]];
        encryptor_locations = sorted(encryptor_locations, key=lambda x: x[1]);
        
        if self.ENCRYPTOR_COUNT==0 and game_state.turn_number > 2:
            k = game_state.attempt_spawn(ENCRYPTOR, encryptor_locations[0]);

        basic_filter_locations = [[1, 13], [26, 13], [2, 12], [25, 12], [6, 11], [21, 11], [7, 9], [20, 9], [8, 8], [19, 8], [9, 7], [18, 7], [10, 6], [17, 6], [11, 5], [16, 5], [12, 4], [15, 4], [13, 3], [14, 3]];
        basic_destructor_locations = [[0, 13], [27, 13], [6, 10], [21, 10]];
        game_state.attempt_spawn(DESTRUCTOR, basic_destructor_locations)
        game_state.attempt_spawn(FILTER, basic_filter_locations)

        defending_filter_locations = [[1, 13], [26, 13], [2, 12], [25, 12], [6, 11], [21, 11], [3, 11], [5, 11], [7, 11], [8, 11], [19, 11], [20, 11], [22, 11], [24, 11]];
        defending_filter_locations = self.sort_positions_by_score(game_state, defending_filter_locations);

        destructor_locations = [[0, 13], [27, 13], [6, 10], [21, 10],[1, 12], [26, 12], [2, 11], [25, 11], [3, 10], [5, 10], [7, 10], [20, 10], [22, 10], [24, 10], [6, 9], [21, 9]];

        for i in defending_filter_locations:
            gamelib.debug_write(str(i));
            gamelib.debug_write(str(self.nearby_destructor(game_state, i, destructor_locations)));
            if game_state.get_resource(CORES) < 2:
                break;
            if self.nearby_destructor(game_state, i, destructor_locations):
                game_state.attempt_spawn(FILTER, i);
                game_state.attempt_upgrade(i);


       #extra filters [[3, 11], [5, 11], [7, 11], [8, 11], [19, 11], [20, 11], [22, 11], [24, 11]]

        # if not game_state.contains_stationary_unit([6,10]):
        #     game_state.attempt_spawn(DESTRUCTOR, [5,10]);
        # if not game_state.contains_stationary_unit([21,10]):
        #     game_state.attempt_spawn(DESTRUCTOR, [22,10]);
        
        



        

        destructor_locations = self.sort_positions_by_score(game_state, destructor_locations);
        game_state.attempt_spawn(DESTRUCTOR, destructor_locations[0:8])

        for i in defending_filter_locations:
            if game_state.get_resource(CORES) < 2:
                break;
            if self.nearby_destructor(game_state, i, destructor_locations):
                game_state.attempt_spawn(FILTER, i);
                game_state.attempt_upgrade(i);


        if game_state.get_resource(CORES) >= 8:         
            k=game_state.attempt_spawn(ENCRYPTOR, encryptor_locations[0:min(12,1+game_state.turn_number//2)])


        game_state.attempt_spawn(DESTRUCTOR, destructor_locations)

        for i in defending_filter_locations:
            if game_state.get_resource(CORES) < 2:
                break;
            if self.nearby_destructor(game_state, i, destructor_locations):
                game_state.attempt_spawn(FILTER, i);
                game_state.attempt_upgrade(i);
        
        #TODO decide on destructor vs encryptor upgrade order based on enemy encryptor count

        if game_state.get_resource(CORES) >= 8:
            game_state.attempt_upgrade(destructor_locations)
            game_state.attempt_upgrade(encryptor_locations)
    
    def least_damage_spawn_location(self, game_state, location_options):
        """
        This function will help us guess which location is the safest to spawn moving units from.
        It gets the path the unit will take then checks locations on that path to 
        estimate the path's damage risk.
        """
        damages = []

        for location in location_options:
            path = game_state.find_path_to_edge(location)
            damage = 0
            for path_location in path:
                # Get number of enemy destructors that can attack the final location and multiply by destructor damage
                damage += len(game_state.get_attackers(path_location, 0)) * gamelib.GameUnit(DESTRUCTOR,
                                                                                          game_state.config).damage_i
            damages.append(damage)

        return location_options[damages.index(min(damages))]
    

    def detect_enemy_unit(self, game_state, unit_type=None, valid_x=None, valid_y=None):
        total_units = 0
        for location in game_state.game_map:
            if game_state.contains_stationary_unit(location):
                for unit in game_state.game_map[location]:
                    if unit.player_index == 1 and (unit_type is None or unit.unit_type == unit_type) and (
                            valid_x is None or location[0] in valid_x) and (valid_y is None or location[1] in valid_y):
                        total_units += 1
        return total_units
    def position_score(self, game_state, location):
        score = 0;
        for loc in self.scored_on_locations:
           score += max(0, 3.5-game_state.game_map.distance_between_locations(loc,location));
        return score;

    def sort_positions_by_score(self, game_state, location_options):
        tuple_list = [];
        for loc in location_options:
            s = self.position_score(game_state,loc);
            tuple_list.append((loc,s));

        tuple_list = sorted(tuple_list, key=lambda x: x[1], reverse=True)
        
        sorted_locs = [i[0] for i in tuple_list];
        return sorted_locs;

    def on_action_frame(self, turn_string):
        """
        Full doc on format of a game frame at: https://docs.c1games.com/json-docs.html
        """
        # Let's record at what position we get scored on
        state = json.loads(turn_string)
        
        self.ENCRYPTOR_COUNT = len(state["p1Units"][1]);
        self.ENEMY_ENCRYPTOR_COUNT = len(state["p2Units"][1]);
        self.ENEMY_HEALTH = state["p2Stats"][0];
        
        events = state["events"]
        damages = events["damage"]
        breaches = events["breach"]

        for damage in damages:

            unit_owner_self = True if damage[4] == 1 else False

            # When parsing the frame data directly, 
            # 1 is integer for yourself, 2 is opponent (StarterKit code uses 0, 1 as player_index instead)
            if unit_owner_self:
                location = damage[0];
               # gamelib.debug_write("Got damaged at: {}".format(location))
                self.scored_on_locations.append(location)
                #gamelib.debug_write("All locations: {}".format(self.scored_on_locations))

        for breach in breaches:
            unit_owner_self = True if breach[4] == 1 else False
            if not unit_owner_self:
                location = breach[0];
                self.scored_on_locations.append(location)


if __name__ == "__main__":
    algo = AlgoStrategy()
    algo.start()
