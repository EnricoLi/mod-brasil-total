# Mod Studio do Brasil Total

Cópia do [FL26 Mod Studio](https://github.com/Matozanato/FootballLife-new-leagues) (licença MIT, ver `mod-studio/LICENSE`), versão 0.2.3+ (commit 138017e), com uma mudança nossa:

- **`custom_cups`** (em `tools/leaguebuilder.py`): uma copa montada à mão, com pré-fases de ida e volta alimentando um mata-mata de 16. É o que monta a Copa do Brasil do mod. Teste em `tools/test_custom_cups.py`.

## Como rodar no Windows

1. Instale o Python 3.11 ou mais novo (python.org), marcando "Add python.exe to PATH".
2. No Prompt de Comando: `pip install PySide6 Pillow capstone py7zr`
3. Entre na pasta `mod-studio\tools` e rode: `python modstudio_main.py`
   - Para o build gravar no jogo, abra o Prompt de Comando como administrador.
