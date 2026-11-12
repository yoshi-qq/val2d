![Red VALORANT V on a dark background](assets/logo.png)

# Val2d

A non-commercial, top-down 2D recreation of VALORANT for solo practice against bots and private matches with friends.

The content and roadmap below track the development build. Gameplay changes may land on this branch separately.

[Maps](#maps) · [Agents](#agents) · [Weapons and armor](#weapons-and-armor) · [Roadmap](#roadmap)

## Play

```sh
python -m pip install -r requirements.txt
python play.py
python play.py --no-menu --map ascent --team-size 5
python server.py --online
python map_editor.py ascent
```

Use the main menu to play Unrated, Swiftplay or Team Deathmatch against bots, or choose Custom to host or join a private match. Join over LAN by address or discovery, or over the internet with a join code. Run `python play.py --help` or `python server.py --help` for command-line options.

| Controls | Action |
| --- | --- |
| WASD, Shift, Ctrl, Space | Run, walk, crouch, jump |
| Mouse, left click, right click | Turn and aim depth, fire, alternate fire or cancel an aimed ability |
| R, 1 / 2 / 3 | Reload, switch weapons |
| C / Q / E / X, hold F1 | Abilities, ability info |
| F, G | Interact, plant or defuse, swap weapons with F. Drop the bomb or weapon with G. |
| B, Tab, Esc | Buy menu, scoreboard, pause or close the current menu |
| Alt+F4 | Open quit confirmation. Press again to quit immediately. |

## Game content

<!-- BEGIN GAME CONTENT -->

### Maps

| Icon | Map | Availability |
| --- | --- | --- |
| ![Ascent map icon](assets/maps/ascent/icon.png) | Ascent | Default |
| ![Alley map icon](assets/maps/alley/icon.png) | Alley | Map editor |
| ![Harbour map icon](assets/maps/harbour/icon.png) | Harbour | Map editor |
| ![Range map icon](assets/maps/range/icon.png) | Range | Map editor |
| ![Workyard map icon](assets/maps/workyard/icon.png) | Workyard | Map editor |

### Agents

8 selectable in the current build.

| Portrait | In game | Agent | Role | C / Q / E / X |
| --- | --- | --- | --- | --- |
| ![Brimstone portrait](assets/agents/brimstone/brimstone_portrait.png) | ![Brimstone idle sprite](assets/agents/brimstone/brimstone_idle.png) | Brimstone | Controller | <img src="assets/ui/ability_brimstone_C.png" alt="Brimstone C" width="20"> <img src="assets/ui/ability_brimstone_Q.png" alt="Brimstone Q" width="20"> <img src="assets/ui/ability_brimstone_E.png" alt="Brimstone E" width="20"> <img src="assets/ui/ability_brimstone_X.png" alt="Brimstone X" width="20"> |
| ![Omen portrait](assets/agents/omen/omen_portrait.png) | ![Omen idle sprite](assets/agents/omen/omen_idle.png) | Omen | Controller | <img src="assets/ui/ability_omen_C.png" alt="Omen C" width="20"> <img src="assets/ui/ability_omen_Q.png" alt="Omen Q" width="20"> <img src="assets/ui/ability_omen_E.png" alt="Omen E" width="20"> <img src="assets/ui/ability_omen_X.png" alt="Omen X" width="20"> |
| ![Jett portrait](assets/agents/jett/jett_portrait.png) | ![Jett idle sprite](assets/agents/jett/jett_idle.png) | Jett | Duelist | <img src="assets/ui/ability_jett_C.png" alt="Jett C" width="20"> <img src="assets/ui/ability_jett_Q.png" alt="Jett Q" width="20"> <img src="assets/ui/ability_jett_E.png" alt="Jett E" width="20"> <img src="assets/ui/ability_jett_X.png" alt="Jett X" width="20"> |
| ![Sova portrait](assets/agents/sova/sova_portrait.png) | ![Sova idle sprite](assets/agents/sova/sova_idle.png) | Sova | Initiator | <img src="assets/ui/ability_sova_C.png" alt="Sova C" width="20"> <img src="assets/ui/ability_sova_Q.png" alt="Sova Q" width="20"> <img src="assets/ui/ability_sova_E.png" alt="Sova E" width="20"> <img src="assets/ui/ability_sova_X.png" alt="Sova X" width="20"> |
| ![Sage portrait](assets/agents/sage/sage_portrait.png) | ![Sage idle sprite](assets/agents/sage/sage_idle.png) | Sage | Sentinel | <img src="assets/ui/ability_sage_C.png" alt="Sage C" width="20"> <img src="assets/ui/ability_sage_Q.png" alt="Sage Q" width="20"> <img src="assets/ui/ability_sage_E.png" alt="Sage E" width="20"> <img src="assets/ui/ability_sage_X.png" alt="Sage X" width="20"> |
| ![Cypher portrait](assets/agents/cypher/cypher_portrait.png) | ![Cypher idle sprite](assets/agents/cypher/cypher_idle.png) | Cypher | Sentinel | <img src="assets/ui/ability_cypher_C.png" alt="Cypher C" width="20"> <img src="assets/ui/ability_cypher_Q.png" alt="Cypher Q" width="20"> <img src="assets/ui/ability_cypher_E.png" alt="Cypher E" width="20"> <img src="assets/ui/ability_cypher_X.png" alt="Cypher X" width="20"> |
| ![Phoenix portrait](assets/agents/phoenix/phoenix_portrait.png) | ![Phoenix idle sprite](assets/agents/phoenix/phoenix_idle.png) | Phoenix | Duelist | <img src="assets/ui/ability_phoenix_C.png" alt="Phoenix C" width="20"> <img src="assets/ui/ability_phoenix_Q.png" alt="Phoenix Q" width="20"> <img src="assets/ui/ability_phoenix_E.png" alt="Phoenix E" width="20"> <img src="assets/ui/ability_phoenix_X.png" alt="Phoenix X" width="20"> |
| ![Killjoy portrait](assets/agents/killjoy/killjoy_portrait.png) | ![Killjoy idle sprite](assets/agents/killjoy/killjoy_idle.png) | Killjoy | Sentinel | <img src="assets/ui/ability_killjoy_C.png" alt="Killjoy C" width="20"> <img src="assets/ui/ability_killjoy_Q.png" alt="Killjoy Q" width="20"> <img src="assets/ui/ability_killjoy_E.png" alt="Killjoy E" width="20"> <img src="assets/ui/ability_killjoy_X.png" alt="Killjoy X" width="20"> |

### Weapons and armor

21 configured weapons, including melee.

| Category | Item | Sprite | Cost |
| --- | --- | --- | --- |
| Melee | Tactical Knife | ![Tactical Knife sprite](assets/weapons/val2d/tactical_knife.png) | Starting loadout |
| Sidearm | Classic | ![Classic sprite](assets/weapons/val2d/classic.png) | Free |
| Sidearm | Shorty | ![Shorty sprite](assets/weapons/val2d/shorty.png) | 300 credits |
| Sidearm | Frenzy | ![Frenzy sprite](assets/weapons/val2d/frenzy.png) | 450 credits |
| Sidearm | Ghost | ![Ghost sprite](assets/weapons/val2d/ghost.png) | 500 credits |
| Sidearm | Bandit | ![Bandit sprite](assets/weapons/val2d/bandit.png) | 600 credits |
| Sidearm | Sheriff | ![Sheriff sprite](assets/weapons/val2d/sheriff.png) | 800 credits |
| SMG | Stinger | ![Stinger sprite](assets/weapons/val2d/stinger.png) | 1,100 credits |
| SMG | Spectre | ![Spectre sprite](assets/weapons/val2d/spectre.png) | 1,600 credits |
| Shotgun | Bucky | ![Bucky sprite](assets/weapons/val2d/bucky.png) | 850 credits |
| Shotgun | Judge | ![Judge sprite](assets/weapons/val2d/judge.png) | 1,850 credits |
| Rifle | Bulldog | ![Bulldog sprite](assets/weapons/val2d/bulldog.png) | 2,050 credits |
| Rifle | Guardian | ![Guardian sprite](assets/weapons/val2d/guardian.png) | 2,250 credits |
| Rifle | Phantom | ![Phantom sprite](assets/weapons/val2d/phantom.png) | 2,900 credits |
| Rifle | Vandal | ![Vandal sprite](assets/weapons/val2d/vandal.png) | 2,900 credits |
| Rifle | Warden | ![Warden sprite](assets/weapons/val2d/warden.png) | 2,900 credits |
| Sniper | Marshal | ![Marshal sprite](assets/weapons/val2d/marshal.png) | 950 credits |
| Sniper | Outlaw | ![Outlaw sprite](assets/weapons/val2d/outlaw.png) | 2,400 credits |
| Sniper | Operator | ![Operator sprite](assets/weapons/val2d/operator.png) | 4,700 credits |
| Heavy | Ares | ![Ares sprite](assets/weapons/val2d/ares.png) | 1,600 credits |
| Heavy | Odin | ![Odin sprite](assets/weapons/val2d/odin.png) | 3,200 credits |
| Armor | Light Armor | <img src="assets/ui/buy/vest_light.png" alt="Light Armor buy sprite" width="48"> | 400 credits |
| Armor | Heavy Armor | <img src="assets/ui/buy/vest_heavy.png" alt="Heavy Armor buy sprite" width="48"> | 1,000 credits |

<!-- END GAME CONTENT -->

## Roadmap

- [ ] Playtest Ascent with a full lobby and verify heights, windows, props and destructible cover. [Ascent design notes](docs/design/ASCENT.md)
- [ ] Verify ability animations and FX in a match for every active agent.
- [ ] Add rear and side character sprites for the active agents. [Figure views](docs/design/FIGURE_VIEWS.md)
- [ ] Check weapon sprites in hand, in the HUD and in the buy menu during a match.
- [ ] Tune gameplay and bot balance. Check the defender advantage on Harbour and the attacker advantage in Alley 1v1.
- [ ] Verify internet play across two separate networks.

See the [detailed roadmap](roadmap.md) and [sprite handover](docs/SPRITES.md).

## Development

- [Configuration](config/README.md) and [modding guide](docs/MODDING.md)
- In a checkout with the README generator, run `python -m tools.update_readme` after changing the roster, maps, weapons or sprites.
- Run the tests with `python -m pytest tests`.
- Build for Windows with `python build.py`. The game executable is `dist/Val2d/Val2d.exe`.

The VALORANT mark is by Riot Games. [VALORANT Asset Kit](https://playvalorant.com/en-gb/news/game-updates/valorant-asset-kit/)
