"""Potion definitions. Each has an `fx(combat, target)`; `targeted` potions are
handed the enemy the player picked.
"""

POTIONS = {
    "fire": dict(name="Fire Potion", desc="Deal 20 damage to an enemy.", targeted=True,
                 fx=lambda cb, t: cb.player_attack(t, 20, potion=True)),
    "block": dict(name="Block Potion", desc="Gain 12 Block.",
                  fx=lambda cb, t: cb.gain_block(cb.player, 12)),
    "strength": dict(name="Strength Potion", desc="Gain 2 Strength.",
                     fx=lambda cb, t: cb.apply(cb.player, "strength", 2)),
    "energy": dict(name="Energy Potion", desc="Gain 2 Energy.",
                   fx=lambda cb, t: cb.gain_energy(2)),
    "swift": dict(name="Swift Potion", desc="Draw 3 cards.", fx=lambda cb, t: cb.draw(3)),
    "explosive": dict(name="Explosive Potion", desc="Deal 10 damage to ALL enemies.",
                      fx=lambda cb, t: [cb.player_attack(e, 10, potion=True)
                                        for e in cb.living()]),
    "weak": dict(name="Weak Potion", desc="Apply 3 Weak to an enemy.", targeted=True,
                 fx=lambda cb, t: cb.apply(t, "weak", 3)),
    "fear": dict(name="Fear Potion", desc="Apply 3 Vulnerable to an enemy.", targeted=True,
                 fx=lambda cb, t: cb.apply(t, "vulnerable", 3)),
    "blood": dict(name="Blood Potion", desc="Heal 12 HP.", fx=lambda cb, t: cb.heal(cb.player, 12)),
}
