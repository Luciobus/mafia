import grpc
import logging
from simple_term_menu import TerminalMenu
from time import sleep

import server_pb2
import server_pb2_grpc

SHERIFF_NIGHT_OPTIONS = ['InvestigatePlayer']
MAFIA_OPTIONS = ['ExecutePlayer']
CITIZEN_OPTIONS = ['EndDay', 'VotePlayer']
GHOST_OPTIONS = ['GetPlayers', 'exit']


# Класс, представляющий клиент игры
class MafiaGameClient:
    def __init__(self):
        self.username = ""
        self.role = ""
        self.is_day = True
        self.server_address = ""
        self.channel = None
        self.stub = None

    def Connect(self, server_address):
        self.server_address = server_address
        self.channel = grpc.insecure_channel(self.server_address)
        self.stub = server_pb2_grpc.MafiaGameStub(self.channel)
        request = server_pb2.ConnectRequest(server_address=self.server_address)
        response = self.stub.Connect(request)
        return response.success

    def SetUsername(self, username):
        self.username = username
        request = server_pb2.SetUsernameRequest(username=username)
        response = self.stub.SetUsername(request)
        return response.success
    
    def AssignRole(self):
        request = server_pb2.AssignRoleRequest(username=self.username)
        response = self.stub.AssignRole(request)
        self.role = response.role
        self.is_alive = True
        return response.role

    def GetPlayers(self):
        request = server_pb2.GetPlayersRequest()
        response = self.stub.GetPlayers(request)
        return response.players.players
    
    def IsGameFinished(self):
        request = server_pb2.IsGameFinishedRequest()
        response = self.stub.IsGameFinished(request)
        return response.finished, response.msg

    def EndDay(self):
        request = server_pb2.EndDayRequest(username=self.username)
        response = self.stub.EndDay(request)
        self.WaitNight()
        if role == 'Citizen':
            self.WaitDay()
    
    def ExecutePlayer(self, player_name):
        request = server_pb2.ExecutePlayerRequest(player_name=player_name)
        response = self.stub.ExecutePlayer(request)
        self.WaitDay()
        return response.success
    
    def VotePlayer(self, player_name):
        request = server_pb2.VotePlayerRequest(username=self.username, player_name=player_name)
        response = self.stub.VotePlayer(request)
        self.WaitNight()
        if role == 'Citizen':
            self.WaitDay()
    
    def WaitNight(self):
        print('Waiting for night...')
        is_day = True
        day_result = ''
        while is_day:
            request = server_pb2.CheckDayRequest()
            response = self.stub.CheckDay(request)
            is_day = response.success
            day_result = response.msg
            sleep(2)
        self.is_day = False
        self.role = next((p for p in self.GetPlayers() if p.name == self.username)).role
        print('Day finished.\n{}'.format(day_result))
    
    def WaitDay(self):
        print('Waiting for day...')
        is_day = False
        while not is_day:
            request = server_pb2.CheckDayRequest(role=self.role)
            response = self.stub.CheckDay(request)
            is_day = response.success
            night_result = response.msg
            finished, _ = self.IsGameFinished()
            if finished:
                return
            sleep(2)
        self.is_day = True
        self.role = next((p for p in self.GetPlayers() if p.name == self.username)).role
        print('Night finished.\n{}'.format(night_result))
        if self.role == 'Sheriff':
            print('Do you want to publish data?')
            publish_variants = ['Yes', 'No']
            publish = publish_variants[TerminalMenu(publish_variants).show()] == 'Yes'
            request = server_pb2.PublishDataRequest(publish=publish)
            response = self.stub.PublishData(request)

    def InvestigatePlayer(self, player_name):
        request = server_pb2.InvestigatePlayerRequest(player_name=player_name)
        response = self.stub.InvestigatePlayer(request)
        print('Player {} is {}.'.format(player_name, response.role))
        self.WaitDay()
        return response.success

    def PublishData(self):
        request = server_pb2.PublishDataRequest()
        response = self.stub.PublishData(request)
        return response.success


if __name__ == '__main__':
    game_client = MafiaGameClient()
    game_client.Connect('localhost:50053')
    is_username_set = False
    name = input('Enter username:')
    is_username_set = game_client.SetUsername(name)
    while not is_username_set:
        print('Sorry, username with this name is already playing')
        name = input('Enter username:')
        is_username_set = game_client.SetUsername(name)
    role = game_client.AssignRole()

    while True:
        finished, res = game_client.IsGameFinished()
        if finished:
            print(res)
            break
        options = GHOST_OPTIONS
        role = game_client.role
        if game_client.is_day:
            if role != 'Ghost':
                options = CITIZEN_OPTIONS + options
        else:
            if role == 'Mafia':
                options = MAFIA_OPTIONS + options
            elif role == 'Sheriff':
                options = SHERIFF_NIGHT_OPTIONS + options
        print('Role: {}. Choose command:'.format(game_client.role))
        command_id = TerminalMenu(options).show()
        command = options[command_id]

        if command == 'GetPlayers':
            players = game_client.GetPlayers()
            print('Connected Players:')
            for player in players:
                print('-', player.name + '{}'.format('You' if player.name == game_client.username else player.role if player.role == 'Ghost' else '?'))
        
        elif command == 'EndDay':
            logging.info("Sending EndDay request from client")
            game_client.EndDay()
        
        elif command == 'ExecutePlayer':
            print('Choose player to execute')
            players = [player.name for player in game_client.GetPlayers()]
            player_name = players[TerminalMenu(players).show()]
            logging.info("Sending ExecutePlayer request from client for player: %s", player_name)
            game_client.ExecutePlayer(player_name)
        
        elif command == 'VotePlayer':
            print('Choose player to vote')
            players = [player.name for player in game_client.GetPlayers() if player.role != 'Ghost']
            player_name = players[TerminalMenu(players).show()]
            logging.info("Sending VotePlayer request from client for player: %s", player_name)
            game_client.VotePlayer(player_name)
        
        elif command == 'InvestigatePlayer':
            print('Choose player to investigate')
            players = [player.name for player in game_client.GetPlayers()]
            player_name = players[TerminalMenu(players).show()]
            logging.info("Sending InvestigatePlayer request from client")
            game_client.InvestigatePlayer(player_name)
        
        elif command == 'PublishData':
            logging.info("Sending PublishData request from client")
            game_client.PublishData()
        
        elif command == 'exit':
            break
        
        else:
            print("Invalid command '{}'. Please try again.".format(command))
        print()
