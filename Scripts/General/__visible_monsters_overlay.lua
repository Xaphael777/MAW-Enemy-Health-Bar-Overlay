local json = require("json")

-- 1. Get the current script's file path
local script_path = debug.getinfo(1, "S").source:sub(2)

-- 2. Extract the script's directory (".../Scripts/General/")
local script_dir = script_path:match("^(.*[/\\])")

-- 3. Build the relative path to visible_monsters.json and overlay_settings.json
local file_path = script_dir .. ".." .. "\\" .. ".." .. "\\" .. "_Python Overlay" .. "\\" .. "visible_monsters.json"
local settings_path = script_dir .. ".." .. "\\" .. ".." .. "\\" .. "_Python Overlay" .. "\\" .. "overlay_settings.json"

-- 4. Grab screen res from settings app (reloaded periodically)
local function loadScreenResolution(path)
    local file = io.open(path, "r")
    if not file then
        return 1920.0, 1080.0
    end

    local content = file:read("*a")
    file:close()

    local ok, data = pcall(json.decode, content)
    if ok and data and data.screen_resolution then
        local w, h = data.screen_resolution:match("(%d+)x(%d+)")
        if w and h then
            return tonumber(w), tonumber(h)
        end
    end

    return 1920.0, 1080.0
end

local screenWidth, screenHeight = loadScreenResolution(settings_path)
local screenCenterX = screenWidth / 2.0
local screenCenterY = screenHeight / 2.0
local lastSettingsCheck = 0
local lastEncodedOutput = ""
local lastWriteTime = 0

local function refreshResolutionIfNeeded(now)
    if now - lastSettingsCheck >= 2.0 then
        lastSettingsCheck = now
        local w, h = loadScreenResolution(settings_path)
        if w ~= screenWidth or h ~= screenHeight then
            screenWidth, screenHeight = w, h
            screenCenterX = screenWidth / 2.0
            screenCenterY = screenHeight / 2.0
        end
    end
end

-- Distance utility
local function getDistance(p, m)
    return math.sqrt((p.X - m.X)^2 + (p.Y - m.Y)^2 + (p.Z - m.Z)^2)
end

-- Real monster HP helper using MawCore.MonsterHP ledger when available
local function getRealHP(mon)
    if MawCore and MawCore.MonsterHP then
        local hp = math.floor(MawCore.MonsterHP.current(mon) + 0.5)
        local fullHP = math.floor(MawCore.MonsterHP.max(mon) + 0.5)
        return math.max(0, hp), math.max(1, fullHP)
    end
    local res0 = mon.Resistances and mon.Resistances[0] or 0
    local exponent = (res0 >= 0 and res0 < 60000) and math.floor(res0 / 1000) or 0
    local mult = 2 ^ exponent
    return math.max(0, mon.HP * mult), math.max(1, mon.FullHP * mult)
end

-- Visual sprite height & radius helper (accounts for sprite-to-collision height ratio, boss scale & Shrinking Ray)
-- Note: MonListBin[id].Height (typically 160) is the physics collision cylinder height (~chest level),
-- while the rendered billboard sprite extends ~1.75x higher to the top of the monster's head.
local SPRITE_HEIGHT_FACTOR = 1.75

local function getMonsterVisualDimensions(mon)
    local bin = Game.MonListBin[mon.Id]
    local height = ((bin and bin.Height) or mon.BodyHeight or 100) * SPRITE_HEIGHT_FACTOR
    local radius = (bin and bin.Radius) or mon.BodyRadius or 40
    local scale = 1.0
    if mon.NameId >= 220 and mon.NameId < 300 then
        scale = (Map.IndoorOrOutdoor == 1) and 1.4 or 2.0
        local nameStr = Game.PlaceMonTxt[mon.NameId] or ""
        local monsterSkill = string.match(nameStr, "([^%s]+)")
        if monsterSkill == "Omnipotent" then
            scale = (scale - 1) * 1.5 + scale
        end
    end
    if const and const.MonsterBuff and const.MonsterBuff.ShrinkingRay then
        local shrinkBuff = mon.SpellBuffs[const.MonsterBuff.ShrinkingRay]
        if shrinkBuff and shrinkBuff.ExpireTime > Game.Time and shrinkBuff.Power > 0 then
            scale = scale / shrinkBuff.Power
        end
    end
    return height * scale, radius * scale
end

-- Active debuffs helper (tracks duration ratios and stack counts)
local DEBUFF_BUFF_DEFS = nil
local debuff_duration_tracker = {}
local nextHitSeq = 0
local lastMonstersOutput = {}

local function getDebuffDefs()
    if DEBUFF_BUFF_DEFS then
        return DEBUFF_BUFF_DEFS
    end
    if not (const and const.MonsterBuff) then
        return {}
    end
    local mb = const.MonsterBuff
    DEBUFF_BUFF_DEFS = {
        { id = mb.Paralyze,     name = "Paralyze" },
        { id = mb.Stoned,       name = "Stoned" },
        { id = mb.Slow,         name = "Slow" },
        { id = mb.ArmorHalved,  name = "ArmorHalved" },
        { id = mb.DamageHalved, name = "DamageHalved" },
        { id = mb.MeleeOnly,    name = "MeleeOnly" },
        { id = mb.ShrinkingRay, name = "ShrinkingRay" },
        { id = mb.Fear,         name = "Fear" },
        { id = mb.Charm,        name = "Charm" },
        { id = mb.Berserk,      name = "Berserk" },
        { id = mb.Enslave,      name = "Enslave" },
        { id = mb.Wander,       name = "Wander" },
    }
    return DEBUFF_BUFF_DEFS
end

local function getActiveDebuffs(mon, monIndex)
    local active = {}
    local gameTime = Game.Time
    local minuteTicks = (const and const.Minute) or 256
    local monTracker = debuff_duration_tracker[monIndex]

    for _, def in ipairs(getDebuffDefs()) do
        if def.id then
            local buff = mon.SpellBuffs[def.id]
            if buff and buff.ExpireTime > gameTime then
                local remTicks = buff.ExpireTime - gameTime
                if not monTracker then
                    monTracker = {}
                    debuff_duration_tracker[monIndex] = monTracker
                end
                local bState = monTracker[def.name]
                if not bState or remTicks > bState.prevTicks or bState.maxTicks <= 0 then
                    bState = { maxTicks = remTicks, prevTicks = remTicks }
                    monTracker[def.name] = bState
                else
                    bState.prevTicks = remTicks
                end
                local ratio = math.max(0.0, math.min(1.0, remTicks / math.max(1, bState.maxTicks)))
                local remSec = math.floor(((remTicks / minuteTicks) * 2.0) * 10 + 0.5) / 10.0
                table.insert(active, {
                    Name = def.name,
                    Ratio = math.floor(ratio * 1000 + 0.5) / 1000,
                    Remaining = remSec
                })
            elseif monTracker then
                monTracker[def.name] = nil
            end
        end
    end
    if mapvars then
        local spearStack = mapvars.spearDamageIncrease and mapvars.spearDamageIncrease[monIndex] or 0
        if spearStack > 0 then
            table.insert(active, {
                Name = "Spear",
                Stacks = math.max(1, math.floor(spearStack + 0.5))
            })
        end
        local legStack = mapvars.legendaryDamageTaken and mapvars.legendaryDamageTaken[monIndex] or 0
        if legStack > 0 then
            table.insert(active, {
                Name = "Legendary",
                Stacks = math.max(1, math.floor(legStack + 0.5))
            })
        end
    end
    return active
end

local function ProjectToScreen(x, y, z, height, radius)
    local dx, dy, dz = x - Party.X, y - Party.Y, z - Party.Z

    local angle = math.rad(Party.Direction * 360.0 / 2048.0)
    local look = math.rad(Party.LookAngle * 180.0 / 1024.0)
    local s = math.sin(angle)
    local c = math.cos(angle)

    local depth = dx * c + dy * s

    -- If depth is zero or behind camera, do not render
    if depth <= 0.1 then 
        return nil, nil
    end

    local horizontal_offset = -dx * s + dy * c
    local base_vertical_offset = dz - depth * math.tan(look)
    local head_vertical_offset = base_vertical_offset + height

    -- Linear perspective scale based strictly on forward depth
    local scale = screenCenterX / depth

    local screenX = screenCenterX - (horizontal_offset * scale)
    local headY = screenCenterY - (head_vertical_offset * scale)
    local footY = screenCenterY - (base_vertical_offset * scale)
    local halfWidth = (radius or 0) * scale

    -- Check whether the monster's body (feet-to-head and width) intersects the screen bounds
    if (screenX + halfWidth) < -100 or (screenX - halfWidth) > (screenWidth + 100) then
        return nil, nil
    end
    if footY < -100 or headY > (screenHeight + 100) then
        return nil, nil
    end

    -- If a tall monster/boss has its body on-screen but its head extends above the top edge, clamp Y on-screen
    local screenY = headY
    if screenY < 35 and footY > 70 then
        screenY = math.min(math.max(35, headY), footY - 35)
    end

    return screenX, screenY
end

local barSize = {100, 150, 200, 250, 300, 400}
function CheckBarSize(mon)
    local monType = (mon.Id - 1) % 3 + 1
    if mon.NameId >= 220 and mon.NameId < 300 then
        local nameStr = Game.PlaceMonTxt[mon.NameId] or ""
        local monsterSkill = string.match(nameStr, "([^%s]+)")
        if monsterSkill == "Omnipotent" then
            monType = 6
        elseif monsterSkill == "Broodlord" then
            monType = 5
        else
            monType = 4
        end
    end
    return barSize[monType]
end

local DAMAGE_TYPE_NAMES = {
    [0] = "Fire",
    [1] = "Air",
    [2] = "Water",
    [3] = "Earth",
    [4] = "Phys",
    [5] = "Magic",
    [6] = "Spirit",
    [7] = "Mind",
    [8] = "Body",
    [9] = "Light",
    [10] = "Dark",
    [12] = "Energy",
    [50] = "Dragon"
}

local function getMonsterAttackAndSpells(mon)
    local attackTypes = {}
    local atk1 = mon.Attack1 and mon.Attack1.Type
    local atk1Name = (atk1 and DAMAGE_TYPE_NAMES[atk1]) or (atk1 and const and const.Damage and table.find(const.Damage, atk1)) or "Phys"
    table.insert(attackTypes, atk1Name)

    if (mon.Attack2Chance or 0) > 0 and mon.Attack2 then
        local atk2 = mon.Attack2.Type
        local atk2Name = (atk2 and DAMAGE_TYPE_NAMES[atk2]) or (atk2 and const and const.Damage and table.find(const.Damage, atk2))
        if atk2Name and atk2Name ~= atk1Name then
            table.insert(attackTypes, atk2Name)
        end
    end

    local spells = {}
    if (mon.SpellChance or 0) > 0 and (mon.Spell or 0) > 0 and Game.SpellsTxt and Game.SpellsTxt[mon.Spell] then
        local s1Name = Game.SpellsTxt[mon.Spell].Name
        if s1Name and s1Name ~= "" then
            table.insert(spells, s1Name)
        end
    end
    if (mon.Spell2Chance or 0) > 0 and (mon.Spell2 or 0) > 0 and mon.Spell2 ~= mon.Spell and Game.SpellsTxt and Game.SpellsTxt[mon.Spell2] then
        local s2Name = Game.SpellsTxt[mon.Spell2].Name
        if s2Name and s2Name ~= "" then
            table.insert(spells, s2Name)
        end
    end

    return attackTypes, spells
end

local function getPartyIdMonsterMastery()
    if not (Party and const and const.Skills and const.Skills.IdentifyMonster) then
        return 0
    end
    local maxM = 0
    for i = 0, Party.High do
        local pl = Party[i]
        if pl then
            local s, m = SplitSkill(pl:GetSkill(const.Skills.IdentifyMonster))
            local s1, m1 = SplitSkill(pl.Skills[const.Skills.IdentifyMonster])
            if (s1 and s1 > 0) or (s and s > 0) then
                local effM = math.max(m or 0, m1 or 0)
                if effM == 0 then
                    effM = 1
                end
                if effM > maxM then
                    maxM = effM
                end
            end
        end
    end
    return maxM
end

local function buildMonsterEntry(key, mon, value_table, dist, now)
    local hp, fullHP = getRealHP(mon)
    local hp_before_hit = (value_table and value_table.hp_before_hit) or hp
    local is_crit = (value_table and value_table.is_crit) or false

    local name = Game.MonstersTxt[mon.Id].Name
    if mon.NameId > 0 and Game.PlaceMonTxt[mon.NameId] then
        name = Game.PlaceMonTxt[mon.NameId]
    end

    local level = (getMonsterLevel and getMonsterLevel(mon)) or mon.Level
    local bSize = CheckBarSize(mon)
    local height, radius = getMonsterVisualDimensions(mon)
    local screenX, screenY = ProjectToScreen(mon.X, mon.Y, mon.Z, height, radius)
    if not (screenX and screenY) then
        return nil
    end

    local actual_damage = 0
    local recent_hits = {}
    if value_table then
        if value_table.last_hit_damage and value_table.last_hit_damage > 0 then
            actual_damage = math.min(fullHP, value_table.last_hit_damage)
        else
            actual_damage = math.max(0, math.min(hp_before_hit, hp_before_hit - hp))
        end

        if value_table.recent_hits then
            local kept = {}
            for _, h in ipairs(value_table.recent_hits) do
                if (now - (h.Time or 0)) <= 1.2 then
                    table.insert(kept, h)
                    table.insert(recent_hits, {
                        Seq = h.Seq,
                        Damage = h.Damage,
                        Crit = h.Crit
                    })
                end
            end
            value_table.recent_hits = kept
        end
    end

    local debuffs = getActiveDebuffs(mon, key)
    local attackTypes, spells = getMonsterAttackAndSpells(mon)

    return {
        Index = key,
        Name = name,
        Level = level,
        HP = hp,
        FullHP = fullHP,
        Distance = dist,
        ScreenX = screenX,
        ScreenY = screenY,
        BarSize = bSize,
        LastHitDamage = actual_damage,
        IsCrit = is_crit,
        Debuffs = debuffs,
        AttackTypes = attackTypes,
        Spells = spells,
        RecentHits = recent_hits
    }
end

local function recordHitEvent(entry, damage, is_crit, now)
    local dmg = math.max(0, math.floor((damage or 0) + 0.5))
    if dmg <= 0 then
        return
    end
    nextHitSeq = nextHitSeq + 1
    entry.recent_hits = entry.recent_hits or {}
    table.insert(entry.recent_hits, {
        Seq = nextHitSeq,
        Damage = dmg,
        Crit = not not is_crit,
        Time = now
    })
    while #entry.recent_hits > 8 do
        table.remove(entry.recent_hits, 1)
    end
end

function events.LoadMap()
    mapvars.damaged_monsters = mapvars.damaged_monsters or {}
    debuff_duration_tracker = {}
    lastMonstersOutput = {}
end

-- Hook that triggers when damage is calculated (runs before MawCore.Damage pipeline)
function events.CalcDamageToMonster(t)
    if not t or type(t.MonsterIndex) ~= "number" or t.MonsterIndex < 0 or t.MonsterIndex > Map.Monsters.High then
        return
    end
    local mon = Map.Monsters[t.MonsterIndex]
    if mon then
        local curHP, _ = getRealHP(mon)
        mapvars.damaged_monsters = mapvars.damaged_monsters or {}
        local entry = mapvars.damaged_monsters[t.MonsterIndex] or {}
        entry.timestamp = os.clock()
        entry.hp_before_hit = curHP
        entry.last_hit_damage = nil
        entry.is_crit = false
        entry.hit_recorded_this_calc = false
        mapvars.damaged_monsters[t.MonsterIndex] = entry
    end
end

-- Hook called by MawCore/Damage.lua stage_trackAndClamp:
-- ShowDamage(data.Player, damage, DamageState.isCrit(), data.Object, t.Monster)
function ShowDamage(pl, damage, crit, obj, mon)
    if mon then
        local ok, idx = pcall(function() return mon:GetIndex() end)
        if ok and idx and idx >= 0 and idx <= Map.Monsters.High then
            local now = os.clock()
            mapvars.damaged_monsters = mapvars.damaged_monsters or {}
            local entry = mapvars.damaged_monsters[idx] or {}
            entry.is_crit = not not crit
            entry.last_hit_damage = math.max(0, math.floor((damage or 0) + 0.5))
            entry.timestamp = now
            entry.hit_recorded_this_calc = true
            recordHitEvent(entry, entry.last_hit_damage, entry.is_crit, now)
            mapvars.damaged_monsters[idx] = entry
        end
    end
end

-- Hook published at the end of MawCore.Damage pipeline
function events.MawMonsterDamage(t)
    if t and type(t.MonsterIndex) == "number" and (t.Result or 0) > 0 then
        local now = os.clock()
        mapvars.damaged_monsters = mapvars.damaged_monsters or {}
        local entry = mapvars.damaged_monsters[t.MonsterIndex]
        if entry then
            entry.timestamp = now
            if MawCore and MawCore.DamageState and MawCore.DamageState.isCrit() then
                entry.is_crit = true
            end
            if not entry.hit_recorded_this_calc then
                entry.last_hit_damage = math.max(0, math.floor((t.Result or 0) + 0.5))
                entry.hit_recorded_this_calc = true
                recordHitEvent(entry, entry.last_hit_damage, entry.is_crit, now)
            end
        end
    end
end

-- On every tick, decide which monsters to show and write to JSON
function events.Tick()
    local now = os.clock()
    refreshResolutionIfNeeded(now)

    local inMenu = (Game.CurrentScreen ~= 0)
    local idMonsterMastery = getPartyIdMonsterMastery()

    if inMenu then
        local final_output = {
            MapName = (Map and Map.Name) or "",
            InMenu = true,
            IdMonsterMastery = idMonsterMastery,
            Monsters = lastMonstersOutput,
            TargetedMonsterIndex = nil
        }
        local ok, encoded = pcall(json.encode, final_output)
        if ok and encoded and (encoded ~= lastEncodedOutput or (now - lastWriteTime >= 0.5)) then
            local f = io.open(file_path, "w")
            if f then
                f:write(encoded)
                f:close()
                lastEncodedOutput = encoded
                lastWriteTime = now
            end
        end
        return
    end

    local output = {}
    local monsters_to_remove = {}
    local targeted_monster_index = nil

    local tar = Mouse:GetTarget()
    if tar and tar.Kind == 3 and tar.Index >= 0 and tar.Index <= Map.Monsters.High then
        targeted_monster_index = tar.Index
    end

    mapvars.damaged_monsters = mapvars.damaged_monsters or {}

    -- Also auto-track any nearby hostile monster that currently has an active CC/debuff
    local gameTime = Game.Time
    local defs = getDebuffDefs()
    if #defs > 0 then
        for i = 0, Map.Monsters.High do
            if not mapvars.damaged_monsters[i] then
                local m = Map.Monsters[i]
                if m and m.HP > 0 and m.ShowOnMap and m.ShowAsHostile then
                    for _, def in ipairs(defs) do
                        local b = def.id and m.SpellBuffs[def.id]
                        if b and b.ExpireTime > gameTime then
                            local curHP, _ = getRealHP(m)
                            mapvars.damaged_monsters[i] = {
                                timestamp = now,
                                hp_before_hit = curHP,
                                is_crit = false
                            }
                            break
                        end
                    end
                end
            end
        end
    end

    local included_targeted = false

    for key, value_table in pairs(mapvars.damaged_monsters) do
        if type(key) ~= "number" or key < 0 or key > Map.Monsters.High then
            table.insert(monsters_to_remove, key)
            goto continue_loop
        end

        local mon = Map.Monsters[key]
        if not mon or not mon.ShowOnMap or not mon.ShowAsHostile then
            table.insert(monsters_to_remove, key)
            goto continue_loop
        end

        local hp, _ = getRealHP(mon)
        local last_hit_timestamp = value_table.timestamp or now

        local effective_display_time = 30000.0
        if hp == 0 then
            effective_display_time = 30.5
        end

        if (now - last_hit_timestamp <= effective_display_time) then
            local dist = getDistance(Party, mon)
            if dist <= 5120 then
                local entry = buildMonsterEntry(key, mon, value_table, dist, now)
                if entry then
                    table.insert(output, entry)
                    if key == targeted_monster_index then
                        included_targeted = true
                    end
                end
            end
        else
            table.insert(monsters_to_remove, key)
        end
        ::continue_loop::
    end

    for _, key in ipairs(monsters_to_remove) do
        mapvars.damaged_monsters[key] = nil
        debuff_duration_tracker[key] = nil
    end

    -- Include mouseover target even if it has not been damaged yet
    if targeted_monster_index and not included_targeted then
        local mon = Map.Monsters[targeted_monster_index]
        if mon and mon.HP > 0 and mon.ShowOnMap and mon.ShowAsHostile then
            local dist = getDistance(Party, mon)
            if dist <= 5120 then
                local entry = buildMonsterEntry(targeted_monster_index, mon, nil, dist, now)
                if entry then
                    table.insert(output, entry)
                end
            end
        end
    end

    lastMonstersOutput = output

    local final_output = {
        MapName = Map.Name or "",
        InMenu = false,
        IdMonsterMastery = idMonsterMastery,
        Monsters = output,
        TargetedMonsterIndex = targeted_monster_index
    }

    local ok, encoded = pcall(json.encode, final_output)
    if ok and encoded then
        -- Only write when data changed (or every 0.5s as heartbeat) to prevent read/write flicker
        if encoded ~= lastEncodedOutput or (now - lastWriteTime >= 0.5) then
            local f = io.open(file_path, "w")
            if f then
                f:write(encoded)
                f:close()
                lastEncodedOutput = encoded
                lastWriteTime = now
            end
        end
    end
end