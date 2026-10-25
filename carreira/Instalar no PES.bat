@echo off
rem Instala no PES o modulo do Brasil Total (placar automatico). Rode como administrador.
net session >nul 2>&1
if errorlevel 1 (
  echo Clique com o botao direito neste arquivo e escolha "Executar como administrador".
  pause
  exit /b 1
)
set "JOGO=C:\Program Files (x86)\SP Football Life 2026\SiderAddons"
if not exist "%JOGO%\sider.ini" (
  echo Nao achei o Football Life 2026 em "%JOGO%".
  pause
  exit /b 1
)
copy /Y "%~dp0sider\brasiltotal.lua" "%JOGO%\modules\brasiltotal.lua" >nul
findstr /C:"brasiltotal.lua" "%JOGO%\sider.ini" >nul
if errorlevel 1 echo lua.module = "brasiltotal.lua">>"%JOGO%\sider.ini"
echo Pronto: o Brasil Total esta ligado ao PES.
pause
