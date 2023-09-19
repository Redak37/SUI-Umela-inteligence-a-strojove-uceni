import logging

from ..utils import possible_attacks
from dicewars.client.ai_driver import BattleCommand, EndTurnCommand
from . import helper, config

# [attacker's dices][deffender's dices]
att = ((0, 0, 0, 0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0, 0, 0),
        (1, 0.825396825396825, 0.446712018140589, 0.178571428571428, 0.061224489795918, 0, 0, 0, 0),
        (1, 0.958333333333333, 0.754251700680272, 0.459183673469387, 0.229733560090702, 0.102536848072562, 0, 0, 0),
        (1, 0.990740740740740, 0.907785336356765, 0.710034013605442, 0.466301335348954, 0.266849332325522, 0.139610389610389, 0, 0),
        (1, 0.998015873015873, 0.967876039304610, 0.863024376417233, 0.679453262786596, 0.471214411690602, 0.294939187796330, 0.171837421837421, 0.095719095719095),
        (1, 0.999639249639249, 0.988971346114203, 0.939355287569573, 0.825207860922146, 0.656849103277674, 0.474789640374055, 0.316957453321089, 0.199544563180926),
        (1, 0.999999999999999, 0.996272246272246, 0.973890692640692, 0.910012826679493, 0.793690877024210, 0.639427281472736, 0.477553310886644, 0.334678368769277),
        (1, 1,                 0.998741998741998, 0.988844488844488, 0.955014121680788, 0.881960631960632, 0.767273130909494, 0.625556261919898, 0.479746360865241))


def my_sort(move):
    """Sort

    Function tu sort moves by probability of win
    """

    return -att[move[0].get_dice()][move[1].get_dice()]


class AI:
    """Naive player agent

    This agent performs all moves, that are close to any move, that was already good
    """

    def __init__(self, player_name, board, players_order):
        """
        Parameters
        ----------
        game : Game

        Attributes
        ----------
        players_order : list of int
            Names of players in the order they are playing, with the agent being first
        """
        self.only_read = True
        self.player_name = player_name
        self.logger = logging.getLogger('AI')
        self.helper = helper.Helper(self.only_read)
        self.nb_players = board.nb_players_alive()
        self.board = board
        self.state = self.evaluate_board_state()
        self.skipped = 0
        self.random = 0
        self.turns = 0
        self.players_order = players_order
        self.last = 0
        if self.is_last():
            self.last = 1


    def ai_turn(self, board, nb_moves_this_turn, nb_turns_this_game, time_left):
        """AI agent's turn

        This agent estimates probability to win the game from the statistics file
        """
        self.board = board

        if time_left <= 0:
            return EndTurnCommand()

        self.helper.close_file()
        self.helper.open_file_rw()

        if not self.only_read:
            for move in self.helper.jsondata['last moves']:
                try:
                    target = self.board.get_area(move['target name'])
                except KeyError:
                    continue

                if move['survived'] == 0 and target.get_owner_name() == self.player_name:
                    move['successful'] = 1
                    self.helper.rewrite_file()

                if self.is_winner():
                    move['winner'] = 1
                    self.helper.rewrite_file()

            if nb_turns_this_game == 0 and nb_moves_this_turn == 0:
                self.helper.jsondata['number of games'] += 1
                if self.nb_players != board.nb_players_alive():
                    self.last = 0

            if nb_turns_this_game > self.turns:
                self.evaluate_last_moves()
                self.turns = nb_turns_this_game

        if self.is_winner() or self.is_looser():
            self.helper.close_file()
            return EndTurnCommand()

        attacks = list(possible_attacks(board, self.player_name))
        valued_attacks = self.get_attack_value(attacks)

        for valued_attack in valued_attacks:
            source = valued_attack[0]
            target = valued_attack[1]
            move = valued_attack[2]

            if not self.only_read:
                self.helper.jsondata['last moves'].append(move)
                self.helper.rewrite_file()
            return BattleCommand(source.get_name(), target.get_name())

        self.skipped += 1
        if self.skipped >= 4 and attacks:
            source, target = sorted(attacks, key=my_sort)[0]
            self.skipped = 0
            self.helper.close_file()
            return BattleCommand(source.get_name(), target.get_name())

        self.helper.close_file()
        return EndTurnCommand()

    def is_looser(self):
        """Has this player lost?

        Returns
        -------
        bool
            looser
        """
        if self.board.nb_players_alive() == 1:
            for area in self.board.areas.values():
                return area.get_owner_name != self.player_name
        return False

    def is_winner(self):
        """Has this player won?

        Returns
        -------
        bool
            winner
        """
        if self.board.nb_players_alive() == 1:
            for area in self.board.areas.values():
                return area.get_owner_name == self.player_name
        return False

    def evaluate_board_state(self):
        '''Evaluate actual state
        '''
        info = Info(self.board, self.player_name, self.nb_players)
        return info.evaluate()

    @staticmethod
    def update_moves(moves, new_move, only_get=False):
        '''Updates moves in statistic
        '''
        dev = 1
        similar_move = None
        similar_move_score = 0
        if only_get:
            for move in moves:
                score = 0
                if att[new_move['source power']][new_move['target power']] < att[int(move['source power'])][int(move['target power'])]:
                    continue
                if new_move['source power'] < move['source power']:
                    continue

                for key in config.MOVES_KEYS:
                    if key != 'source power' and key != 'target power':
                        if move[key] - dev <= new_move[key] <= move[key] + dev:
                            score += 1

                if score >= len(config.MOVES_KEYS) - 5:
                    return True
            return False
        
        for move in moves:
            score = 0
            if new_move['source power'] != move['source power'] or new_move['target power'] != move['target power']:
                continue

            for key in config.MOVES_KEYS:
                if move[key] - dev <= new_move[key] <= move[key] + dev:
                    score += 1

            if score >= len(config.MOVES_KEYS) - 3 and score > similar_move_score:
                similar_move = move
                similar_move_score = score

        if similar_move:
            for key in config.MOVES_KEYS:
                similar_move[key] = (similar_move[key] + new_move[key]) * 0.5
        else:
            new_good_move = dict()
            for key in config.MOVES_KEYS:
                if key not in new_good_move or key not in new_move:
                    new_good_move[key] = 0
                new_good_move[key] = new_move[key]
            moves.append(new_good_move)

    def is_last(self):
        """Is this last player?

        Returns
        -------
        bool
            is this player last?
        """
        return self.players_order.index(self.player_name) == self.nb_players - 1

    def evaluate_last_moves(self):
        """Evaluate last move
        """
        prev_eval = self.state
        new_eval = self.evaluate_board_state()

        last_moves = list()
        for move in self.helper.jsondata['last moves']:
            try:
                source = self.board.get_area(move['source name'])
                target = self.board.get_area(move['target name'])
            except KeyError:
                continue

            if move['successful'] == 1:
                if self.is_winner():
                    move['winner'] = 1
                    last_moves.append(move)
                    continue

                if not self.last:
                    continue

                if self.is_looser():
                    continue

                if source.get_owner_name() == self.player_name:
                    move['protection'] += 1

                if target.get_owner_name() == self.player_name:
                    move['survived'] += 1
                    last_moves.append(move)
                else:
                    if prev_eval + move['winner'] * 5 + (move['protection'] + move['survived']) * 3 > new_eval:
                        self.update_moves(self.helper.jsondata["overall"][str(move['number of players'])], move)

        self.helper.jsondata['last moves'] = last_moves
        self.helper.rewrite_file()
        self.state = new_eval

    def get_attack_value(self, attacks):
        """Get list of possible turns that are near to any known good move.
        Improved by probability of successfullness restriction.
        """
        alive = self.board.nb_players_alive()
        valued_attacks = list()

        if len(self.helper.jsondata['overall'][str(alive)]) < config.MINIMUM_STATISTIC_MOVES:
            for source, target in attacks:
                move = self.get_attack_info(source, target)
                if att[source.get_dice()][target.get_dice()] > 0.4:
                    valued_attacks.append([source, target, move])
        else:
            for source, target in attacks:
                if att[source.get_dice()][target.get_dice()] > 0.4:
                    move = self.get_attack_info(source, target)
                    if self.update_moves(self.helper.jsondata['overall'][str(alive)], move, only_get=True):
                        valued_attacks.append([source, target, move])

        return sorted(valued_attacks, key=my_sort)

    def get_attack_info(self, source, target):
        '''Get info about attacks from statistics
        '''
        move = dict()

        move['winner'] = 0
        move['survived'] = 0
        move['protection'] = 0
        move['number of players'] = self.board.nb_players_alive()
        move['successful'] = 0
        move['source name'] = source.get_name()
        move['target name'] = target.get_name()

        move['source power'] = source.get_dice()
        move['source region size'] = len(self.board.get_areas_region(
            source.get_name(),
            self.board.get_player_areas(source.get_owner_name)
        ))

        neighbours = source.get_adjacent_areas()
        max = 1
        mymax = 1
        oneneigh = 0
        eightneigh = 0
        myoneneigh = 0
        myeightneigh = 0

        for neighbour in neighbours:
            neigh = self.board.get_area(neighbour)
            if neigh.get_owner_name() != self.player_name:
                if neigh.get_dice() == 8:
                    eightneigh += 1
                if not neigh.can_attack():
                    oneneigh += 1
                if neigh.get_dice() > max:
                    max = neigh.get_dice()
            else:
                if neigh.get_dice() == 8:
                    myeightneigh += 1
                if not neigh.can_attack():
                    myoneneigh += 1
                if neigh.get_dice() > mymax:
                    mymax = neigh.get_dice()

        move['source neighbours'] = len(neighbours)
        move['source neighbours highest dice'] = max
        move['source 1 neighbours'] = oneneigh
        move['source 8 neighbours'] = eightneigh
        move['source my neighbours highest dice'] = mymax
        move['source number of 1'] = myoneneigh
        move['source number of 8'] = myeightneigh

        move['target power'] = target.get_dice()
        move['target region size'] = len(self.board.get_areas_region(
            target.get_name(),
            self.board.get_player_areas(target.get_owner_name)
        ))

        neighbours = target.get_adjacent_areas()
        max = 1
        mymax = 1
        oneneigh = 0
        eightneigh = 0
        myoneneigh = 0
        myeightneigh = 0

        for neighbour in neighbours:
            neigh = self.board.get_area(neighbour)
            if neigh.get_owner_name() != self.player_name and neigh.get_owner_name() != target.get_owner_name():
                if neigh.get_dice() == 8:
                    eightneigh += 1
                if not neigh.can_attack():
                    oneneigh += 1
                if neigh.get_dice() > max:
                    max = neigh.get_dice()
            elif neigh.get_owner_name() != self.player_name:
                if neigh.get_dice() == 8:
                    myeightneigh += 1
                if not neigh.can_attack():
                    myoneneigh += 1
                if neigh.get_dice() > mymax:
                    mymax = neigh.get_dice()

        move['target neighbours'] = len(neighbours)
        move['target neighbours highest dice'] = max
        move['target 1 neighbours'] = oneneigh
        move['target 8 neighbours'] = eightneigh
        move['target my neighbours highest dice'] = mymax
        move['target number of 1'] = myoneneigh
        move['target number of 8'] = myeightneigh

        return move


class Info:
    '''Class for summary of info
    '''
    def __init__(self, board, player_name, nb_players):
        self.board = board
        self.player_name = player_name
        self.largest_region = self.get_largest_region()
        self.overall_strength = board.get_player_dice(player_name)
        self.nb_players_alive = board.nb_players_alive()
        self.original_nb_players = nb_players

    def get_largest_region(self):
        """Get size of the largest region, including the areas within

        Attributes
        ----------
        largest_region : list of int
            Names of areas in the largest region

        Returns
        -------
        int
            Number of areas in the largest region
        """
        self.largest_region = []

        players_regions = self.board.get_players_regions(self.player_name)
        max_region_size = max(len(region) for region in players_regions)
        max_sized_regions = [region for region in players_regions if len(region) == max_region_size]

        for region in max_sized_regions:
            for area in region:
                self.largest_region.append(area)
        return max_region_size

    def evaluate(self):
        """Evaluate move based on biggest area and overall strength
        
        Returns
        -------
        int
            Evaluation
        """
        return 2 * self.largest_region + self.overall_strength
