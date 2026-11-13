from gameplay.kit.dsl import ability, agent, heal, heal_rate, on, push, sound, spawn, status, step, thing

PULSE_RADIUS = 5.5


def pulse_device(healing):
    mode = "heal" if healing else "concuss"
    pulse = [heal(20)] if healing else [step("miks_concuss")]
    pulse += [
        sound("ab_heal" if healing else "ab_sensor", radius=26),
        spawn(thing("zone", lasts=0.22, radius=PULSE_RADIUS, status_hint="heal" if healing else "concuss")),
    ]
    triggers = [on("tick", [heal_rate(20 / 3)], who="everyone", sight="walls")] if healing else []
    triggers.extend([
        on("every", pulse, who="everyone", sight="walls", offset=1, seconds=2, count=2),
        on("expire", pulse, who="everyone", sight="walls"),
    ])
    device = thing("sensor", lasts=5, radius=PULSE_RADIUS, hp=50, hit_radius=0.5,
                   friendly_fire=True, sprite=f"miks_pulse_{mode}", triggers=triggers)
    return thing("blast", lasts=0.55, thrown=True, sprite=f"miks_pulse_{mode}",
                 triggers=[on("expire", [spawn(device)])])


AGENT = agent(
    "Miks", role="Controller", order=3, sprites={"ability_poses": True},
    passives=[on("miks_harmonize_kill", [step("miks_refresh_harmonize")])],
    C=ability("M-pulse", target="throw", preview="zone", landing_preview=True, bot="offense",
              price=250, max=2, range=22, radius=PULSE_RADIUS, toggle_alt=True, sound="cast_throw_light",
              desc="Throw a destructible device with three pulses. Right click switches between concuss and heal. Both teams are affected.",
              mode_name="Concuss", place=pulse_device(False),
              alt={"name": "Heal", "place": pulse_device(True)}),
    Q=ability("Harmonize", target="aim_ally", range=20, require_sight=True, preview="heal", price=200, sound="cast_buff",
              desc="Give yourself and an ally combat stim and haste for 8 seconds. Either player's kills refresh both buffs while both survive.",
              do=[step("miks_harmonize")],
              alt={"name": "Buff yourself", "target": "self", "do": [step("miks_harmonize", self_cast=True)]}),
    E=ability("Waveform", target="aim_free", preview="smoke", bot="place", range=55.5, radius=4.72,
              price=100, max=2, start=1, recharge=40, tactical=True, multi=2, sound="ab_smoke",
              desc="Mark up to two locations on the tactical map and confirm to deploy smokes for 16.75 seconds.",
              place=thing("smoke", delay=1, lasts=16.75, radius=4.72, sprite="miks_waveform")),
    X=ability("Bassquake", target="self", preview="zone", cost=8, radius=40, aim_cone=60, sound="cast_charge_up",
              desc="Charge for 1.6 seconds, then knock back, deafen and slow everyone in the cone for 8 seconds.",
              do=[step("miks_bassquake")],
              place=thing("zone", delay=1.6, lasts=0.2, radius=40, cone=60,
                          triggers=[on("start", [push(5, along_aim=True), status("deaf", 8), status("slow", 8),
                                                 sound("ab_wave", radius=48)], who="others")])),
)
