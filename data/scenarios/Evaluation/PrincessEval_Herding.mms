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
name: Princess Evaluation - Herding
description: >
  Headless bot-vs-bot benchmark scenario for AIMatchRunner. Two identical slow, heavy companies with
  default Princess behavior advance toward each other across an open grasslands map. This is the
  configuration where herding-driven piecemeal attacks show up: watch for units trickling into contact
  one at a time instead of committing as a body. The long east-west approach gives the closing dynamic
  several rounds to express itself. The first faction is the unit-less watcher slot claimed by the
  headless runner; the two bot factions mirror each other so before/after comparisons only measure
  code changes.

map: Grasslands BattleMats/32x17 Grasslands A BattleMat.board

factions:
- name: Observer
  # Unit-less watcher slot; ScenarioGameRunner claims the first faction with a headless client.

- name: West Company
  deploy: W
  bot:
    # DEFAULT preset values written out; scenarios cannot reference named presets
    selfpreservation: 5
    fallshame: 5
    hyperaggression: 5
    herdmentality: 5
    bravery: 5
    forcedwithdraw: true
    withdrawto: WEST
    flee: false
  units:
  - fullname: Atlas AS7-D
    crew:
      name: Eval Pilot W1
      gunnery: 4
      piloting: 5
  - fullname: Banshee BNC-3E
    crew:
      name: Eval Pilot W2
      gunnery: 4
      piloting: 5
  - fullname: Stalker STK-3F
    crew:
      name: Eval Pilot W3
      gunnery: 4
      piloting: 5
  - fullname: Awesome AWS-8Q
    crew:
      name: Eval Pilot W4
      gunnery: 4
      piloting: 5
  - fullname: BattleMaster BLR-1G
    crew:
      name: Eval Pilot W5
      gunnery: 4
      piloting: 5
  - fullname: Zeus ZEU-6S
    crew:
      name: Eval Pilot W6
      gunnery: 4
      piloting: 5
  - fullname: Warhammer WHM-6R
    crew:
      name: Eval Pilot W7
      gunnery: 4
      piloting: 5
  - fullname: Marauder MAD-3R
    crew:
      name: Eval Pilot W8
      gunnery: 4
      piloting: 5

- name: East Company
  deploy: "E"
  bot:
    selfpreservation: 5
    fallshame: 5
    hyperaggression: 5
    herdmentality: 5
    bravery: 5
    forcedwithdraw: true
    withdrawto: EAST
    flee: false
  units:
  - fullname: Atlas AS7-D
    crew:
      name: Eval Pilot E1
      gunnery: 4
      piloting: 5
  - fullname: Banshee BNC-3E
    crew:
      name: Eval Pilot E2
      gunnery: 4
      piloting: 5
  - fullname: Stalker STK-3F
    crew:
      name: Eval Pilot E3
      gunnery: 4
      piloting: 5
  - fullname: Awesome AWS-8Q
    crew:
      name: Eval Pilot E4
      gunnery: 4
      piloting: 5
  - fullname: BattleMaster BLR-1G
    crew:
      name: Eval Pilot E5
      gunnery: 4
      piloting: 5
  - fullname: Zeus ZEU-6S
    crew:
      name: Eval Pilot E6
      gunnery: 4
      piloting: 5
  - fullname: Warhammer WHM-6R
    crew:
      name: Eval Pilot E7
      gunnery: 4
      piloting: 5
  - fullname: Marauder MAD-3R
    crew:
      name: Eval Pilot E8
      gunnery: 4
      piloting: 5

end:
- trigger:
    type: battlefieldcontrol
- trigger:
    type: roundend
    round: 20
