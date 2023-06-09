import logging
from concurrent import futures
import grpc
import random
import copy

import server_pb2
import server_pb2_grpc

MAX_COUNT = 4
CITIZEN_COUNT = 2
MAFIA_COUNT = 1
SHERIFF_COUNT = 1
ROLES = CITIZEN_COUNT * ['Citizen'] + MAFIA_COUNT * ['Mafia'] + SHERIFF_COUNT * ['Sheriff']
DEFAULT_DAY_RESULT = 'Voting stage result: nobody is killed'
DEFAULT_NIGHT_RESULT = 'Night stage result: nobody is killed'

# Класс, представляющий сервер игры
class MafiaGameServer(server_pb2_grpc.MafiaGameServicer):
    def __init__(self):
        self.players = []

        self.votes = {}
        self.end_day_players = set()
        self.is_day = True
        self.published = True

        self.executed = ''
        self.investigated = ''

        self.day_result = DEFAULT_DAY_RESULT
        self.night_result = DEFAULT_NIGHT_RESULT

        self.available_roles = ROLES.copy()
        random.shuffle(self.available_roles)
        logging.info(self.available_roles)

    def SetUsername(self, request, context):
        username = request.username
        logging.info("SetUsername request from client: {}".format(username))
        player = next((p for p in self.players if p.name == username), None)
        if player is None and len(self.players) < len(ROLES):
            self.players.append(server_pb2.Player(name=request.username))
            return server_pb2.SetUsernameResponse(success=True)
        else:
            return server_pb2.SetUsernameResponse(success=False)

    def Connect(self, request, context):
        server_address = request.server_address
        logging.info("Connect request from client: {}".format(server_address))
        return server_pb2.ConnectResponse(success=True)

    def GetPlayers(self, request, context):
        logging.info("GetPlayers request from client")
        return server_pb2.GetPlayersResponse(players=server_pb2.PlayerList(players=self.players))
    
    def AssignRole(self, request, context):
        username = request.username
        logging.info("AssignRole request from client: {}".format(username))
        player = next((p for p in self.players if p.name == username))
        role = self.available_roles.pop()
        player.role = role
        return server_pb2.AssignRoleResponse(role=player.role)

    def CheckDay(self, request, context):
        logging.info("CheckDay request from client")
        role = request.role
        sheriff_alive = sum(1 for player in self.players if player.role == 'Sheriff')
        is_day = self.is_day and (self.published or not sheriff_alive)
        if role == 'Sheriff':
            is_day = self.is_day
        res = self.night_result if is_day else self.day_result
        return server_pb2.CheckDayResponse(success=is_day, msg=res)
    
    def IsGameFinished(self, request, context):
        if len(self.available_roles) > 0:
            return server_pb2.IsGameFinishedResponse(finished=False, msg='Game not started')
        mafia_count = sum(1 for player in self.players if player.role == 'Mafia')
        alive_count = sum(1 for player in self.players if player.role != 'Ghost')
        finished = False
        res = ''
        if mafia_count == 0:
            res = 'Game finished. Citizens won.'
            finished = True
        elif 2 * mafia_count >= alive_count:
            res = 'Game finished. Mafia won.'
            finished = True
        return server_pb2.IsGameFinishedResponse(finished=finished, msg=res)
    
    def EndDay(self, request, context):
        username = request.username
        logging.info("EndDay request from client {}".format(username))
        self.end_day_players.add(username)
        if len(self.end_day_players) == MAX_COUNT:
            if len(self.votes) > 0:
                player_name = max(self.votes, key=self.votes.get)
                player = next((p for p in self.players if p.name == player_name))
                player.role = 'Ghost'
                self.day_result = 'Player {} was voted and killed.'.format(player_name)
            self.is_day = False
            self.night_result = DEFAULT_NIGHT_RESULT
            self.votes.clear()
            self.end_day_players.clear()
        return server_pb2.EndDayResponse()

    def ExecutePlayer(self, request, context):
        player_name = request.player_name
        logging.info("ExecutePlayer request from client for player: {}".format(player_name))
        player = next((p for p in self.players if p.name == player_name))
        player.role = 'Ghost'
        self.executed = player_name
        self.night_result = 'Player {} was killed by mafia.'.format(player_name)
        if self.investigated or sum(1 for player in self.players if player.role == 'Sheriff') == 0:
            self.day_result = DEFAULT_DAY_RESULT
            self.is_day = True
        return server_pb2.ExecutePlayerResponse()
    
    def VotePlayer(self, request, context):
        username = request.username
        player_name = request.player_name
        logging.info("VotePlayer request from client {} for player: {}".format(username, player_name))
        if username not in self.end_day_players:
            self.votes[player_name] = self.votes.get(player_name, 0)
            self.end_day_players.add(username)
        return self.EndDay(request=request, context=context)

    def InvestigatePlayer(self, request, context):
        player_name = request.player_name
        logging.info("InvestigatePlayer request from client for player: {}".format(player_name))
        player = next((p for p in self.players if p.name == player_name))
        self.investigated = copy.deepcopy(player)
        self.published = False
        if self.executed or sum(1 for player in self.players if player.role == 'Mafia') == 0:
            self.day_result = DEFAULT_DAY_RESULT
            self.is_day = True
        return server_pb2.InvestigatePlayerResponse(role=player.role)

    def PublishData(self, request, context):
        logging.info("PublishData request from client")
        self.published = True
        self.night_result += ' Player {} was investigated, role: {}.'.format(self.investigated.name, self.investigated.role)
        return server_pb2.PublishDataResponse()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    server_pb2_grpc.add_MafiaGameServicer_to_server(MafiaGameServer(), server)
    server.add_insecure_port('[::]:50053')
    server.start()
    logging.info("Server started on port 50053")
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()
