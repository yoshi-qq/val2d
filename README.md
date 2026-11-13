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

Use the main menu to play Unrated, Swiftplay or Team Deathmatch against bots, or choose Custom to host or join a private party. The host can copy the IP address or join code from the lobby. Guests can paste it into the join field, which remembers the last successful connection. After the match, **Return to party lobby** brings everyone back on the same connection. The host can change the mode, map and rules before starting the next match. Run `python play.py --help` or `python server.py --help` for command-line options.

In Team Deathmatch, press **B** in your team's spawn to choose a loadout for each of the four timed stages. The first team to 100 kills wins. At the end of stage four, the higher score wins and a tie is a draw.

With **Allow cheats** enabled, the host can pause or resume the countdown and end preparation or the current stage from the pause menu. Gameplay continues while the countdown is paused. Ending the final stage resolves the match using its current score. During live play, each player can toggle **Ghost** from the pause menu to fly through walls. Hold jump to rise and crouch to descend.

At each stage change, press **B** outside spawn to equip your next loadout immediately. Val2D gives you five seconds before the automatic switch. If you carry a station weapon, you can keep it by letting the timer expire. Respawning equips the current stage's loadout immediately.

Press **F** near a weapon on the map to take it from its station. Station weapons have limited ammo. Press **G** while using one to switch back to your loadout. You can also carry it into the next stage and use up its remaining ammo.

Walk over a recovery orb when you are missing health or shield. It restores both over six seconds. Teammates who enter the zone share the remaining recovery time. Each orb returns after 30 seconds.

Walk over an ultimate orb to gain up to 10 ultimate points. Each teammate who enters its zone during the next six seconds also gains the points once, up to their ultimate cost. In Val2D, both orbs appear together 60 seconds into live play and refill together every 60 seconds.

After respawning, leave your team's spawn within 15 seconds. You are protected from damage and enemy abilities until you leave or the timer expires. In Val2D, staying past the timer costs 10 HP per second.

Aim at one of your recallable devices and press **F**. In Team Deathmatch, a successful recall returns its charge after five seconds.

Open Bind or Haven with `python map_editor.py bind` or `python map_editor.py haven`. Both have buy barriers, elevated A Towers and walkable routes from each spawn to every plant site. Bind has two one-way player teleporters. Haven has a lower floor under A Tower and destructible metal plates on the Garage doors. Elevations and cover in the other areas still need a detailed pass. [Map references](https://playvalorant.com/en-us/maps/)

Recorded footsteps, rifle fire, magazine handling, Spike pulses and menu clicks use the [CC0 sound sources](assets/sounds/cc0/SOURCES.md).

Open **Inventory**, choose a weapon and preview a skin, then select **Equip** to save it. Every weapon has a Standard look and at least one variant inspired by Prime, Reaver, Oni, RGX 11z Pro or Kuronami.

| Controls | Action |
| --- | --- |
| WASD, Shift, Ctrl, Space | Run, walk, crouch, jump |
| Mouse, left click, right click | Turn and aim depth, fire, alternate fire or cancel an aimed ability |
| R, 1 / 2 / 3 | Reload, switch weapons |
| C / Q / E / X, hold F1 | Abilities, ability info |
| 4, hold 4 | Equip the Spike, plant or defuse |
| F, G | Interact or swap weapons with F. Drop the held Spike or weapon with G. |
| B, Tab, Esc | Buy menu, scoreboard, pause or close the current menu |
| Alt+F4 | Open quit confirmation. Press again to quit immediately. |

## Game content

<!-- BEGIN GAME CONTENT -->

### Maps

| Icon | Map | Availability |
| --- | --- | --- |
| ![Ascent map icon](assets/maps/ascent/icon.png) | Ascent | Default |
| Missing | Bind | Playable |
| Missing | Haven | Playable |

### Agents

30 selectable in the current build.

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
| ![Breach portrait](assets/agents/breach/breach_portrait.png) | ![Breach idle sprite](assets/agents/breach/breach_idle.png) | Breach | Initiator | <img src="assets/ui/ability_breach_C.png" alt="Breach C" width="20"> <img src="assets/ui/ability_breach_Q.png" alt="Breach Q" width="20"> <img src="assets/ui/ability_breach_E.png" alt="Breach E" width="20"> <img src="assets/ui/ability_breach_X.png" alt="Breach X" width="20"> |
| ![Reyna portrait](assets/agents/reyna/reyna_portrait.png) | ![Reyna idle sprite](assets/agents/reyna/reyna_idle.png) | Reyna | Duelist | <img src="assets/ui/ability_reyna_C.png" alt="Reyna C" width="20"> <img src="assets/ui/ability_reyna_Q.png" alt="Reyna Q" width="20"> <img src="assets/ui/ability_reyna_E.png" alt="Reyna E" width="20"> <img src="assets/ui/ability_reyna_X.png" alt="Reyna X" width="20"> |
| ![Miks portrait](assets/agents/miks/miks_portrait.png) | ![Miks idle sprite](assets/agents/miks/miks_idle.png) | Miks | Controller | <img src="assets/ui/ability_miks_C.png" alt="Miks C" width="20"> <img src="assets/ui/ability_miks_Q.png" alt="Miks Q" width="20"> <img src="assets/ui/ability_miks_E.png" alt="Miks E" width="20"> <img src="assets/ui/ability_miks_X.png" alt="Miks X" width="20"> |
| ![Waylay portrait](assets/agents/waylay/waylay_portrait.png) | ![Waylay idle sprite](assets/agents/waylay/waylay_idle.png) | Waylay | Duelist | <img src="assets/ui/ability_waylay_C.png" alt="Waylay C" width="20"> <img src="assets/ui/ability_waylay_Q.png" alt="Waylay Q" width="20"> <img src="assets/ui/ability_waylay_E.png" alt="Waylay E" width="20"> <img src="assets/ui/ability_waylay_X.png" alt="Waylay X" width="20"> |
| ![Gekko portrait](assets/agents/gekko/gekko_portrait.png) | ![Gekko idle sprite](assets/agents/gekko/gekko_idle.png) | Gekko | Initiator | <img src="assets/ui/ability_gekko_C.png" alt="Gekko C" width="20"> <img src="assets/ui/ability_gekko_Q.png" alt="Gekko Q" width="20"> <img src="assets/ui/ability_gekko_E.png" alt="Gekko E" width="20"> <img src="assets/ui/ability_gekko_X.png" alt="Gekko X" width="20"> |
| ![Chamber portrait](assets/agents/chamber/chamber_portrait.png) | ![Chamber idle sprite](assets/agents/chamber/chamber_idle.png) | Chamber | Sentinel | <img src="assets/ui/ability_chamber_C.png" alt="Chamber C" width="20"> <img src="assets/ui/ability_chamber_Q.png" alt="Chamber Q" width="20"> <img src="assets/ui/ability_chamber_E.png" alt="Chamber E" width="20"> <img src="assets/ui/ability_chamber_X.png" alt="Chamber X" width="20"> |
| ![Raze portrait](assets/agents/raze/raze_portrait.png) | ![Raze idle sprite](assets/agents/raze/raze_idle.png) | Raze | Duelist | <img src="assets/ui/ability_raze_C.png" alt="Raze C" width="20"> <img src="assets/ui/ability_raze_Q.png" alt="Raze Q" width="20"> <img src="assets/ui/ability_raze_E.png" alt="Raze E" width="20"> <img src="assets/ui/ability_raze_X.png" alt="Raze X" width="20"> |
| ![Skye portrait](assets/agents/skye/skye_portrait.png) | ![Skye idle sprite](assets/agents/skye/skye_idle.png) | Skye | Initiator | <img src="assets/ui/ability_skye_C.png" alt="Skye C" width="20"> <img src="assets/ui/ability_skye_Q.png" alt="Skye Q" width="20"> <img src="assets/ui/ability_skye_E.png" alt="Skye E" width="20"> <img src="assets/ui/ability_skye_X.png" alt="Skye X" width="20"> |
| ![KAY/O portrait](assets/agents/kayo/kayo_portrait.png) | ![KAY/O idle sprite](assets/agents/kayo/kayo_idle.png) | KAY/O | Initiator | <img src="assets/ui/ability_kayo_C.png" alt="KAY/O C" width="20"> <img src="assets/ui/ability_kayo_Q.png" alt="KAY/O Q" width="20"> <img src="assets/ui/ability_kayo_E.png" alt="KAY/O E" width="20"> <img src="assets/ui/ability_kayo_X.png" alt="KAY/O X" width="20"> |
| ![Viper portrait](assets/agents/viper/viper_portrait.png) | ![Viper idle sprite](assets/agents/viper/viper_idle.png) | Viper | Controller | <img src="assets/ui/ability_viper_C.png" alt="Viper C" width="20"> <img src="assets/ui/ability_viper_Q.png" alt="Viper Q" width="20"> <img src="assets/ui/ability_viper_E.png" alt="Viper E" width="20"> <img src="assets/ui/ability_viper_X.png" alt="Viper X" width="20"> |
| ![Neon portrait](assets/agents/neon/neon_portrait.png) | ![Neon idle sprite](assets/agents/neon/neon_idle.png) | Neon | Duelist | <img src="assets/ui/ability_neon_C.png" alt="Neon C" width="20"> <img src="assets/ui/ability_neon_Q.png" alt="Neon Q" width="20"> <img src="assets/ui/ability_neon_E.png" alt="Neon E" width="20"> <img src="assets/ui/ability_neon_X.png" alt="Neon X" width="20"> |
| ![Yoru portrait](assets/agents/yoru/yoru_portrait.png) | ![Yoru idle sprite](assets/agents/yoru/yoru_idle.png) | Yoru | Duelist | <img src="assets/ui/ability_yoru_C.png" alt="Yoru C" width="20"> <img src="assets/ui/ability_yoru_Q.png" alt="Yoru Q" width="20"> <img src="assets/ui/ability_yoru_E.png" alt="Yoru E" width="20"> <img src="assets/ui/ability_yoru_X.png" alt="Yoru X" width="20"> |
| ![Fade portrait](assets/agents/fade/fade_portrait.png) | ![Fade idle sprite](assets/agents/fade/fade_idle.png) | Fade | Initiator | <img src="assets/ui/ability_fade_C.png" alt="Fade C" width="20"> <img src="assets/ui/ability_fade_Q.png" alt="Fade Q" width="20"> <img src="assets/ui/ability_fade_E.png" alt="Fade E" width="20"> <img src="assets/ui/ability_fade_X.png" alt="Fade X" width="20"> |
| ![Harbor portrait](assets/agents/harbor/harbor_portrait.png) | ![Harbor idle sprite](assets/agents/harbor/harbor_idle.png) | Harbor | Controller | <img src="assets/ui/ability_harbor_C.png" alt="Harbor C" width="20"> <img src="assets/ui/ability_harbor_Q.png" alt="Harbor Q" width="20"> <img src="assets/ui/ability_harbor_E.png" alt="Harbor E" width="20"> <img src="assets/ui/ability_harbor_X.png" alt="Harbor X" width="20"> |
| ![Deadlock portrait](assets/agents/deadlock/deadlock_portrait.png) | ![Deadlock idle sprite](assets/agents/deadlock/deadlock_idle.png) | Deadlock | Sentinel | <img src="assets/ui/ability_deadlock_C.png" alt="Deadlock C" width="20"> <img src="assets/ui/ability_deadlock_Q.png" alt="Deadlock Q" width="20"> <img src="assets/ui/ability_deadlock_E.png" alt="Deadlock E" width="20"> <img src="assets/ui/ability_deadlock_X.png" alt="Deadlock X" width="20"> |
| ![Vyse portrait](assets/agents/vyse/vyse_portrait.png) | ![Vyse idle sprite](assets/agents/vyse/vyse_idle.png) | Vyse | Sentinel | <img src="assets/ui/ability_vyse_C.png" alt="Vyse C" width="20"> <img src="assets/ui/ability_vyse_Q.png" alt="Vyse Q" width="20"> <img src="assets/ui/ability_vyse_E.png" alt="Vyse E" width="20"> <img src="assets/ui/ability_vyse_X.png" alt="Vyse X" width="20"> |
| ![Iso portrait](assets/agents/iso/iso_portrait.png) | ![Iso idle sprite](assets/agents/iso/iso_idle.png) | Iso | Duelist | <img src="assets/ui/ability_iso_C.png" alt="Iso C" width="20"> <img src="assets/ui/ability_iso_Q.png" alt="Iso Q" width="20"> <img src="assets/ui/ability_iso_E.png" alt="Iso E" width="20"> <img src="assets/ui/ability_iso_X.png" alt="Iso X" width="20"> |
| ![Clove portrait](assets/agents/clove/clove_portrait.png) | ![Clove idle sprite](assets/agents/clove/clove_idle.png) | Clove | Controller | <img src="assets/ui/ability_clove_C.png" alt="Clove C" width="20"> <img src="assets/ui/ability_clove_Q.png" alt="Clove Q" width="20"> <img src="assets/ui/ability_clove_E.png" alt="Clove E" width="20"> <img src="assets/ui/ability_clove_X.png" alt="Clove X" width="20"> |
| ![Tejo portrait](assets/agents/tejo/tejo_portrait.png) | ![Tejo idle sprite](assets/agents/tejo/tejo_idle.png) | Tejo | Initiator | <img src="assets/ui/ability_tejo_C.png" alt="Tejo C" width="20"> <img src="assets/ui/ability_tejo_Q.png" alt="Tejo Q" width="20"> <img src="assets/ui/ability_tejo_E.png" alt="Tejo E" width="20"> <img src="assets/ui/ability_tejo_X.png" alt="Tejo X" width="20"> |
| ![Veto portrait](assets/agents/veto/veto_portrait.png) | ![Veto idle sprite](assets/agents/veto/veto_idle.png) | Veto | Sentinel | <img src="assets/ui/ability_veto_C.png" alt="Veto C" width="20"> <img src="assets/ui/ability_veto_Q.png" alt="Veto Q" width="20"> <img src="assets/ui/ability_veto_E.png" alt="Veto E" width="20"> <img src="assets/ui/ability_veto_X.png" alt="Veto X" width="20"> |
| ![Astra portrait](assets/agents/astra/astra_portrait.png) | ![Astra idle sprite](assets/agents/astra/astra_idle.png) | Astra | Controller | <img src="assets/ui/ability_astra_C.png" alt="Astra C" width="20"> <img src="assets/ui/ability_astra_Q.png" alt="Astra Q" width="20"> <img src="assets/ui/ability_astra_E.png" alt="Astra E" width="20"> <img src="assets/ui/ability_astra_X.png" alt="Astra X" width="20"> |
| ![Hush portrait](assets/agents/hush/hush_portrait.png) | ![Hush idle sprite](assets/agents/hush/hush_idle.png) | Hush | Duelist | <img src="assets/ui/ability_hush_C.png" alt="Hush C" width="20"> <img src="assets/ui/ability_hush_Q.png" alt="Hush Q" width="20"> <img src="assets/ui/ability_hush_E.png" alt="Hush E" width="20"> <img src="assets/ui/ability_hush_X.png" alt="Hush X" width="20"> |

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
| Armor | Regen Shield | <img src="assets/ui/buy/regen_shield.png" alt="Regen Shield buy sprite" width="48"> | 650 credits |
| Armor | Heavy Armor | <img src="assets/ui/buy/vest_heavy.png" alt="Heavy Armor buy sprite" width="48"> | 1,000 credits |

<!-- END GAME CONTENT -->

## Roadmap

- [ ] Playtest Ascent with a full lobby and verify heights, windows, props and destructible cover. [Ascent design notes](docs/design/ASCENT.md)
- [ ] Verify ability animations and FX in a match for every active agent.
- [ ] Add rear and side character sprites for the active agents. [Figure views](docs/design/FIGURE_VIEWS.md)
- [ ] Check weapon sprites in hand, in the HUD and in the buy menu during a match.
- [ ] Tune gameplay and bot balance on the playable maps.
- [ ] Verify internet play across two separate networks.

See the [detailed roadmap](roadmap.md) and [sprite handover](docs/SPRITES.md).

## Development

- [Configuration](config/README.md) and [modding guide](docs/MODDING.md)
- In a checkout with the README generator, run `python -m tools.update_readme` after changing the roster, maps, weapons or sprites.
- Run the tests with `python -m pytest tests`.
- Build for Windows with `python build.py`. The game executable is `dist/Val2d/Val2d.exe`.

The VALORANT mark is by Riot Games. [VALORANT Asset Kit](https://playvalorant.com/en-gb/news/game-updates/valorant-asset-kit/)
