"""Roles and passive descriptions shared by the agent browser and lobby."""

import pygame

from client.ui import Ui

AGENT_ROLES = ("All roles", "Duelist", "Initiator", "Controller", "Sentinel")


def draw_role_picker(ui: Ui, selected: int) -> None:
    ui.shade()
    box = pygame.Rect(0, 0, 320, 282)
    box.center = ui.screen.get_rect().center
    ui.panel(box, "bg", edge="top")
    ui.text("Filter by role", (box.x + 18, box.y + 14), "m", bold=True)
    ui.button(pygame.Rect(box.right - 102, box.y + 10, 84, 28), "Back [Esc]", "role_back", size="xs")
    for i, role in enumerate(AGENT_ROLES):
        rect = pygame.Rect(box.x + 18, box.y + 52 + i * 42, box.w - 36, 34)
        ui.button(rect, f"{i + 1}  {role}", f"role_pick:{i}", selected=i == selected, size="s")

AGENT_PASSIVES = {
    "jett": ("Drift", "Hold {jump} while falling to glide. Suppression disables Drift."),
    "neon": ("Battery", "High Gear drains Battery. It recharges while High Gear is inactive. Kills refill it during Overdrive."),
}
