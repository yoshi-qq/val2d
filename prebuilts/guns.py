from classes.types import GunKey, SidearmKey, MeleeKey, Gun, Melee, SpriteSetKey, GunCategory, PenetrationLevel, DamageValues, Scope

m = MeleeKey
s = SidearmKey
g = GunKey
k = SpriteSetKey
c = GunCategory
p = PenetrationLevel

melees: dict[MeleeKey, Melee] = {m.DEFAULT: Melee(name="Default", sprites=k.WEAPON_MELEE)}
# TODO  x4: finish
sidearms: dict[SidearmKey, Gun] = {
    s.CLASSIC: Gun(name="Classic", sprites=k.WEAPON_CLASSIC, category=c.SIDEARM, automatic=False, penetration=p.LOW, runSpeed=5.74, equipSpeed=0.75, reloadSpeed=1.75, magazine=12, fireRate=6.75, firstShotSpread=(0.4, 0.4), damage=DamageValues(values1=(78,26,22), range1=30, values2=(66,22,18), range2=50), scope=None, altFireEffect=None) 
    }
guns: dict[GunKey, Gun] = {
    g.VANDAL: Gun(name="Vandal", sprites=k.WEAPON_VANDAL, category=c.RIFLE, automatic=True, penetration=p.MEDIUM, runSpeed=5.4, equipSpeed=1, reloadSpeed=2.5, magazine=25, fireRate=9.75, firstShotSpread=(0.25,0.157), damage=DamageValues(values1=(160, 40, 32), range1=50), scope=Scope(zoom=1.25, fireRateMultiplier=0.9, moveSpeedMultiplier=0.76, accuracy=1.2), altFireEffect=None)
 }
