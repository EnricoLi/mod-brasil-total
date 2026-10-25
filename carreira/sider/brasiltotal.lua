-- Brasil Total: liga o PES à carreira do Brasil Total.
--
-- O programa grava o seu próximo jogo em %APPDATA%\BrasilTotal\partida.txt. Este módulo mostra
-- esse jogo no overlay do Sider, liga os pênaltis no Amistoso quando o jogo precisa de um
-- vencedor e, durante a partida, grava o placar em %APPDATA%\BrasilTotal\placar.txt, que o
-- programa lê sozinho. Só grava quando os dois times em campo são os do jogo marcado.

local m = {}
m.version = "0.1"

local pasta
local partida
local ultimo = ""
local frames = 0
local chaves_logadas = false
local periodo_antes

local function ler_partida()
    partida = nil
    local f = io.open(pasta .. "partida.txt", "r")
    if not f then
        return
    end
    local t = {}
    for l in f:lines() do
        local k, v = l:match("^([%w_]+)=(.*)$")
        if k then
            t[k] = v
        end
    end
    f:close()
    t.casa, t.fora = tonumber(t.casa), tonumber(t.fora)
    if t.casa and t.fora then
        partida = t
    end
end

local function em_campo(ctx)
    if not partida then
        return false
    end
    local h, a = ctx.home_team, ctx.away_team
    return (h == partida.casa and a == partida.fora) or (h == partida.fora and a == partida.casa)
end

local function gravar(ctx, s)
    local fim = (s.fim and "1") or "0"
    local linha = string.format("id=%s\ncasa=%d\nfora=%d\ngc=%d\ngf=%d\nminuto=%s\nperiodo=%s\nfim=%s\n",
        partida.id or "", ctx.home_team, ctx.away_team, s.home_score or 0, s.away_score or 0,
        tostring(s.clock_minutes or ""), tostring(s.period or ""), fim)
    if linha == ultimo then
        return
    end
    local f = io.open(pasta .. "placar.txt", "w")
    if f then
        f:write(linha)
        f:close()
        ultimo = linha
    end
end

local function stats()
    local fn = match and (match.stats or match.get_stats)
    if not fn then
        return nil
    end
    local ok, s = pcall(fn)
    if ok and type(s) == "table" then
        return s
    end
    return nil
end

function m.set_teams(ctx, home, away)
    ler_partida()
    ultimo = ""
    periodo_antes = nil
    log(string.format("set_teams: %s x %s; jogo marcado: %s x %s", tostring(home), tostring(away),
        partida and tostring(partida.casa) or "-", partida and tostring(partida.fora) or "-"))
end

function m.set_match_settings(ctx, options)
    ler_partida()
    if partida and partida.decide == "1" and ctx.tournament_id == 65535 and em_campo(ctx) then
        options.extra_time = 0
        options.penalties = 1
        log("jogo que precisa de vencedor: pênaltis ligados")
        return options
    end
end

function m.display_frame(ctx)
    frames = frames + 1
    if frames % 30 ~= 0 or not em_campo(ctx) then
        return
    end
    local s = stats()
    if not s then
        return
    end
    if not chaves_logadas then
        local ks = {}
        for k, v in pairs(s) do
            ks[#ks + 1] = k .. "=" .. tostring(v)
        end
        table.sort(ks)
        log("match stats: " .. table.concat(ks, ", "))
        chaves_logadas = true
    end
    if s.period ~= periodo_antes then
        log(string.format("periodo %s -> %s (%s min, %s x %s)", tostring(periodo_antes), tostring(s.period),
            tostring(s.clock_minutes), tostring(s.home_score), tostring(s.away_score)))
        periodo_antes = s.period
    end
    gravar(ctx, s)
end

function m.overlay_on(ctx)
    ler_partida()
    if not partida then
        return "Brasil Total: nenhum jogo marcado. Avance a carreira no programa."
    end
    local t = string.format("Brasil Total: %s\nAmistoso: %s (casa) x %s (fora)", partida.texto or "",
        partida.nome_casa or partida.casa, partida.nome_fora or partida.fora)
    if em_campo(ctx) then
        t = t .. "\nTimes certos: o placar vai para a carreira sozinho."
    end
    return t
end

function m.init(ctx)
    local base = os.getenv("APPDATA") or ctx.sider_dir
    pasta = base:gsub("[/\\]+$", "") .. "\\BrasilTotal\\"
    ler_partida()
    ctx.register("set_teams", m.set_teams)
    ctx.register("set_match_settings", m.set_match_settings)
    ctx.register("display_frame", m.display_frame)
    ctx.register("overlay_on", m.overlay_on)
    log("Brasil Total " .. m.version .. ": pasta " .. pasta)
end

return m
