# MegaMek Data (C) 2026 by The MegaMek Team is licensed under CC BY-NC-SA 4.0.
# To view a copy of this license, visit https://creativecommons.org/licenses/by-nc-sa/4.0/
#
# NOTICE: The MegaMek organization is a non-profit group of volunteers
# creating free software for the BattleTech community.
#
# MechWarrior, BattleMech, `Mech and AeroTech are registered trademarks
# of The Topps Company, Inc. All Rights Reserved.
#
# Catalyst Game Labs and the Catalyst Game Labs logo are trademarks of
# InMediaRes Productions, LLC.
#
# MechWarrior Copyright Microsoft Corporation. MegaMek Data was created under
# Microsoft's "Game Content Usage Rules"
# <https://www.xbox.com/en-US/developers/rules> and it is not endorsed by or
# affiliated with Microsoft.

MMSVersion: 2
name: Princess Evaluation - Forced Withdrawal
description: >
  Headless bot-vs-bot benchmark scenario for AIMatchRunner. Two identical mixed lances with default
  Princess behavior and Forced Withdrawal enabled fight until one side is destroyed or withdraws.
  Intended to measure whether crippled units actually retreat to their withdrawal edge (and keep
  defending themselves) rather than loitering in the engagement zone. The first faction is the
  unit-less watcher slot claimed by the headless runner; the two bot factions mirror each other so
  before/after comparisons only measure code changes, not force imbalance.

map: Map Set 2/16x17 BattleTech.board

factions:
- name: Observer
  # Unit-less watcher slot; ScenarioGameRunner claims the first faction with a headless client.

- name: North Lance
  deploy: N
  bot:
    # DEFAULT preset values written out; scenarios cannot reference named presets
    selfpreservation: 5
    fallshame: 5
    hyperaggression: 5
    herdmentality: 5
    bravery: 5
    forcedwithdraw: true
    withdrawto: NORTH
    flee: false
  units:
  - fullname: Archer ARC-2R
    crew:
      name: Eval Pilot N1
      gunnery: 3
      piloting: 4
  - fullname: Marauder MAD-3R
    crew:
      name: Eval Pilot N2
      gunnery: 3
      piloting: 4
  - fullname: Wolverine WVR-6R
    crew:
      name: Eval Pilot N3
      gunnery: 3
      piloting: 4
  - fullname: Hunchback HBK-4G
    crew:
      name: Eval Pilot N4
      gunnery: 3
      piloting: 4

- name: South Lance
  deploy: S
  bot:
    selfpreservation: 5
    fallshame: 5
    hyperaggression: 5
    herdmentality: 5
    bravery: 5
    forcedwithdraw: true
    withdrawto: SOUTH
    flee: false
  units:
  - fullname: Archer ARC-2R
    crew:
      name: Eval Pilot S1
      gunnery: 3
      piloting: 4
  - fullname: Marauder MAD-3R
    crew:
      name: Eval Pilot S2
      gunnery: 3
      piloting: 4
  - fullname: Wolverine WVR-6R
    crew:
      name: Eval Pilot S3
      gunnery: 3
      piloting: 4
  - fullname: Hunchback HBK-4G
    crew:
      name: Eval Pilot S4
      gunnery: 3
      piloting: 4

end:
- trigger:
    type: battlefieldcontrol
- trigger:
    type: roundend
    round: 15
