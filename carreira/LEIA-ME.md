# Brasil Total — Carreira

A carreira roda neste programa, e o PES 2021 fica só para jogar as partidas do seu clube.

## Como abrir

Dê dois cliques em **Abrir Brasil Total.bat**. Ou, no Prompt de Comando, nesta pasta: `python BrasilTotal.py`.
Precisa do Python com o PySide6, os mesmos do Mod Studio. Não precisa ser administrador.

## Como jogar

1. Na primeira vez, escolha a série e o clube.
2. **Avançar até o próximo jogo** simula todos os outros jogos até o dia do seu.
3. No PES 2021, jogue um **Amistoso (Exhibition)** com o mandante e o visitante que o programa mostra.
4. Digite o placar final e clique em **Confirmar placar do PES**. Num mata-mata empatado, escolha quem venceu nos pênaltis.
   Para pular um jogo, use **Simular este jogo**.

A carreira se salva sozinha em `%APPDATA%\BrasilTotal\carreira.json`.

## O que tem nesta versão

- Séries A, B, C e D com 4 que sobem e 4 que descem entre todas. A Série C tem primeira fase, grupos e final, e a Série D tem grupos e mata-mata.
- Copa do Brasil com os 84 clubes: 1ª e 2ª fase em jogo único com vantagem do empate, 3ª e 4ª fase em jogo único, oitavas a semifinal em ida e volta e final em jogo único.
- Temporadas seguidas, com acesso e rebaixamento.

Os clubes e os elencos vêm do seu mundo do FL26 (`dados/mundo.json`).
