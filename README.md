# Mafia game
Для запуска сервера необходимо выполнить в директории команду

```docker-compose up --build```

После этого могут подключаться клиенты, делается через команду в терминале

```python3 client.py```

Далее игрок вводит своё имя и ему сразу же назначается роль. После того, как все игроки подключились и получили свою роль - начинается стадия дня, где игроки имеют следющие опции:
1. EndDay                                                                                                                                               
2. VotePlayer                                                                                                                                           
3. GetPlayers                                                                                                                                           
4. exit

После завершения дня(выбором EndDay или VotePlayer) наступает ночь, во время которой мирные жители просто ждут дня, шериф имеет право узнать роль одного из игроков, а мафия убить одного из жителей
Утро наступает после выборов шерифа и мафии, а также, если шериф еще жив, то после его выбора о том, чтобы рассказать данные проверки
