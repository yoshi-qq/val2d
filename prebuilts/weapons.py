from classes.types import GunKey, SidearmKey, MeleeKey, Gun, Melee, SpriteSetKey, EffectKey, GunCategory, PenetrationLevel, DamageValues, Scope, melees as melees_, sidearms as sidearms_, guns as guns_

m = MeleeKey
s = SidearmKey
g = GunKey
k = SpriteSetKey
c = GunCategory
p = PenetrationLevel

melees: dict[MeleeKey, Melee] = {m.DEFAULT: Melee(name="Default", sprites=k.WEAPON_MELEE)}
# TODO  x: finish
sidearms: dict[SidearmKey, Gun] = {
    s.CLASSIC: Gun(name="Classic", sprites=k.WEAPON_CLASSIC, category=c.SIDEARM, automatic=False, penetration=p.LOW, runSpeed=5.74, equipSpeed=0.75, reloadSpeed=1.75, magazine=12, reserveAmmo=36, fireRate=6.75, firstShotSpread=(0.4, 0.4), damage=DamageValues(values1=(78,26,22), range1=30, values2=(66,22,18), range2=50), scope=None, silenced=False, altFireEffect=None), 
    s.SHORTY: Gun(name="Shorty", sprites=k.WEAPON_SHORTY, category=c.SIDEARM, automatic=False, penetration=p.LOW, runSpeed=5.4, equipSpeed=0.75, reloadSpeed=1.75, magazine=2, reserveAmmo=6, fireRate=3.33, firstShotSpread=(4, 4), damage=DamageValues(values1=(22,12,6), range1=7, values2=(12,6,3), range2=15, values3=(6,3,2), range3=50), scope=None, silenced=False, altFireEffect=None),
    s.FRENZY: Gun(name="Frenzy", sprites=k.WEAPON_FRENZY, category=c.SIDEARM, automatic=True, penetration=p.LOW, runSpeed=5.74, equipSpeed=1, reloadSpeed=1.5, magazine=15, reserveAmmo=30, fireRate=10, firstShotSpread=(0.65, 0.65), damage=DamageValues(values1=(78,26,22), range1=20, values2=(63,21,17), range2=50), scope=None, silenced=False, altFireEffect=None),
    s.GHOST: Gun(name="Ghost", sprites=k.WEAPON_GHOST, category=c.SIDEARM, automatic=False, penetration=p.MEDIUM, runSpeed=5.74, equipSpeed=0.75, reloadSpeed=1.5, magazine=13, reserveAmmo=39, fireRate=6.75, firstShotSpread=(0.3, 0.3), damage=DamageValues(values1=(105,30,25), range1=30, values2=(87,25,21), range2=50), scope=None, silenced=True, altFireEffect=None),
    s.SHERIFF: Gun(name="Sheriff", sprites=k.WEAPON_SHERIFF, category=c.SIDEARM, automatic=False, penetration=p.HIGH, runSpeed=5.4, equipSpeed=1, reloadSpeed=2.25, magazine=6, reserveAmmo=24, fireRate=4, firstShotSpread=(0.25, 0.25), damage=DamageValues(values1=(159,55,46), range1=30, values2=(145,50,42), range2=50), scope=None, silenced=False, altFireEffect=None), 
    }
guns: dict[GunKey, Gun] = {
    # SMGs
    g.STINGER: Gun(name="Stinger", sprites=k.WEAPON_STINGER, category=c.SMG, automatic=True, penetration=p.LOW, runSpeed=5.74, equipSpeed=0.75, reloadSpeed=2.25, magazine=20, reserveAmmo=60, fireRate=16, firstShotSpread=(0.65,0.35), damage=DamageValues(values1=(67, 27, 22), range1=15, values2=(57,23,19), range2=50), scope=Scope(zoom=1.15, fireRateMultiplier=0.53, moveSpeedMultiplier=0.76, accuracy=1.2), silenced=False, altFireEffect=EffectKey.BURST_FIRE_4),
    g.SPECTRE: Gun(name="Spectre", sprites=k.WEAPON_SPECTRE, category=c.SMG, automatic=True, penetration=p.LOW, runSpeed=5.74, equipSpeed=0.75, reloadSpeed=2.25, magazine=30, reserveAmmo=90, fireRate=13.33, firstShotSpread=(0.4,0.25), damage=DamageValues(values1=(78, 26, 22), range1=15, values2=(66,22,18), range2=30, values3=(60,20,17), range3=50), scope=Scope(zoom=1.15, fireRateMultiplier=0.9, moveSpeedMultiplier=0.76, accuracy=1.2), silenced=True, altFireEffect=None),
    # Shotguns
    g.BUCKY: Gun(name="Bucky", sprites=k.WEAPON_BUCKY, category=c.SHOTGUN, automatic=False, penetration=p.LOW, runSpeed=5.06, equipSpeed=1, reloadSpeed=2.5, magazine=5, reserveAmmo=10, fireRate=1.1, firstShotSpread=(2.6,2.6), damage=DamageValues(values1=(40, 20, 17), range1=8, values2=(26,13,11), range2=12, values3=(18,9,7), range3=50), scope=None, silenced=False, altFireEffect=EffectKey.AIR_BURST_CANISTER_SHOT),
    g.JUDGE: Gun(name="Judge", sprites=k.WEAPON_JUDGE, category=c.SHOTGUN, automatic=False, penetration=p.LOW, runSpeed=5.06, equipSpeed=1, reloadSpeed=2.2, magazine=5, reserveAmmo=15, fireRate=3.5, firstShotSpread=(2.25,2.25), damage=DamageValues(values1=(34, 17, 14), range1=10, values2=(20,10,8), range2=15, values3=(14,7,5), range3=50), scope=None, silenced=False, altFireEffect=None),
    # Rifles
    #   Bulldog
    #   Guardian
    g.PHANTOM: Gun(name="Phantom", sprites=k.WEAPON_PHANTOM, category=c.RIFLE, automatic=True, penetration=p.MEDIUM, runSpeed=5.4, equipSpeed=1, reloadSpeed=2.5, magazine=30, reserveAmmo=60, fireRate=11, firstShotSpread=(0.2,0.11), damage=DamageValues(values1=(156, 39, 33), range1=30, values2=(140,35,29), range2=50), scope=Scope(zoom=1.25, fireRateMultiplier=0.9, moveSpeedMultiplier=0.76, accuracy=1.2), silenced=True, altFireEffect=None),
    g.VANDAL: Gun(name="Vandal", sprites=k.WEAPON_VANDAL, category=c.RIFLE, automatic=True, penetration=p.MEDIUM, runSpeed=5.4, equipSpeed=1, reloadSpeed=2.5, magazine=25, reserveAmmo=50, fireRate=9.75, firstShotSpread=(0.25,0.157), damage=DamageValues(values1=(160, 40, 32), range1=50), scope=Scope(zoom=1.25, fireRateMultiplier=0.9, moveSpeedMultiplier=0.76, accuracy=1.2), silenced=False, altFireEffect=None)
    # Sniper Rifles
    #   Marshal
    #   Outlaw
    #   Operator
    # Machine Guns
    #   Ares
    #   Odin
 }

def init() -> None:
    melees_.update(melees)
    sidearms_.update(sidearms)
    guns_.update(guns)