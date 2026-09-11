# MM Data

This is the MegaMek Data Repository. It holds all data used by the suite of MegaMek programs. Unit files, maps, images,
etc. are all here and normalized.

## Contact Information

This will officially release with the 0.50.07 Version of the MegaMek Suite. Upon release, if you have concerns about
your assets within this package, please email <megamekteam@gmail.com>

## Formatting

Text files must end with a newline and carry no trailing whitespace, which is what `.editorconfig` already asks your
editor for. The build checks this on every pull request and lists every violation in one go. Before you push:

```
./gradlew spotlessApply
```

That fixes every data file you changed. `./gradlew spotlessCheck` reports the same violations without changing
anything.

## File Headers

When adding files to this repository, ensure the following header is at the top with respect to the file format.
Encapsulate appropriately within XML and other such markup files.

```yaml
# MegaMek Data (C) 2025 by The MegaMek Team is licensed under CC BY-NC-SA 4.0.
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
```

## Utilities

This folder holds various utilities that are/have been used to handle various tasks through out the process of the data repo.
They are stored in the `/utilities` folder for backups and for use as needed.

## License

<p><a property="dct:title" rel="cc:attributionURL" href="https://github.com/MegaMek/mm-data">MegaMek Data</a> by <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://github.com/MegaMek">MegaMek Development Team</a> is licensed under <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">CC BY-NC-SA 4.0<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/nc.svg?ref=chooser-v1" alt=""><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/sa.svg?ref=chooser-v1" alt=""></a></p>
