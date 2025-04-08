from classes.types import GunKey, SidearmKey, MeleeKey, Gun, Melee, SpriteSetKey, GunCategory, PenetrationLevel, DamageValues, Scope, melees as melees_, sidearms as sidearms_, guns as guns_

m = MeleeKey
s = SidearmKey
g = GunKey
k = SpriteSetKey
c = GunCategory
p = PenetrationLevel

melees: dict[MeleeKey, Melee] = {m.DEFAULT: Melee(name="Default", sprites=k.WEAPON_MELEE)}
# TODO  x4: finish
sidearms: dict[SidearmKey, Gun] = {
    s.CLASSIC: Gun(name="Classic", sprites=k.WEAPON_CLASSIC, category=c.SIDEARM, automatic=False, penetration=p.LOW, runSpeed=5.74, equipSpeed=0.75, reloadSpeed=1.75, magazine=12, fireRate=6.75, firstShotSpread=(0.4, 0.4), damage=DamageValues(values1=(78,26,22), range1=30, values2=(66,22,18), range2=50), scope=None, silenced=False, altFireEffect=None), 
    s.SHORTY: Gun(name="Shorty", sprites=k.WEAPON_SHORTYY, category=c.SIDEARM, automatic=False, penetration=p.LOW, runSpeed=5.4, equipSpeed=0.75, reloadSpeed=1.75, magazine=2, fireRate=3.33, firstShotSpread=(4, 4), damage=DamageValues(values1=(22,12,6), range1=7, values2=(12,6,3), range2=15, values3=(6,3,2), range3=50), scope=None, silenced=False, altFireEffect=None),
    # Frenzy
    # Ghost
    s.SHERIFF: Gun(name="Sheriff", sprites=k.WEAPON_SHERIFF, category=c.SIDEARM, automatic=False, penetration=p.HIGH, runSpeed=5.4, equipSpeed=1, reloadSpeed=2.25, magazine=6, fireRate=4, firstShotSpread=(0.25, 0.25), damage=DamageValues(values1=(159,55,46), range1=30, values2=(145,50,42), range2=50), scope=None, silenced=False, altFireEffect=None), 
    }
guns: dict[GunKey, Gun] = {
    g.PHANTOM: Gun(name="Phantom", sprites=k.WEAPON_PHANTOM, category=c.RIFLE, automatic=True, penetration=p.MEDIUM, runSpeed=5.4, equipSpeed=1, reloadSpeed=2.5, magazine=30, fireRate=11, firstShotSpread=(0.2,0.11), damage=DamageValues(values1=(156, 39, 33), range1=30, values2=(140,35,29), range2=50), scope=Scope(zoom=1.25, fireRateMultiplier=0.9, moveSpeedMultiplier=0.76, accuracy=1.2), silenced=True, altFireEffect=None),
    g.VANDAL: Gun(name="Vandal", sprites=k.WEAPON_VANDAL, category=c.RIFLE, automatic=True, penetration=p.MEDIUM, runSpeed=5.4, equipSpeed=1, reloadSpeed=2.5, magazine=25, fireRate=9.75, firstShotSpread=(0.25,0.157), damage=DamageValues(values1=(160, 40, 32), range1=50), scope=Scope(zoom=1.25, fireRateMultiplier=0.9, moveSpeedMultiplier=0.76, accuracy=1.2), silenced=False, altFireEffect=None)
 }

def init() -> None:
    melees_.update(melees)
    sidearms_.update(sidearms)
    guns_.update(guns)