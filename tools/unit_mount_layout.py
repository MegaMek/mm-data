"""Keeps the equipment drawn in one location from overlapping.

Every location has a mounting area: a rectangle on the face its weapons look out of. A weapon first takes
the place its hard point gives it. Only when that would overlap something already placed is it moved, to
the nearest free spot inside the area, and only when the area is genuinely full is it drawn smaller.
A recipe states an area with mountAreas; otherwise a default is centered on the location's hard point.
"""
# Clear space kept between two neighbors, and the grid searched for a free spot, in model units.
GAP = .4
STEP = .5
# A full area shrinks a weapon through these sizes before giving up and leaving it where it was.
FITS = (1, .85, .72, .61, .52)
# Width and height of a location's mounting area when the recipe does not give one.
DEFAULT_AREAS = {'CT': (12, 14), 'LT': (12, 14), 'RT': (12, 14), 'HD': (6, 6)}
LIMB_AREA = (10, 10)


class MountArea:
    def __init__(self, center, width, height):
        self.center, self.width, self.height = center, width, height
        self.placed = []

    @classmethod
    def for_location(cls, recipe, location, hard_point):
        """The recipe's area for this location, or a default one around its hard point (x, z)."""
        stated = recipe.get('mountAreas', {}).get(location)
        if stated:
            center = stated.get('center')
            return cls((center[0]-42, center[2]) if center else hard_point, stated['width'], stated['height'])
        return cls(hard_point, *DEFAULT_AREAS.get(location, LIMB_AREA))

    def _is_free(self, x, z, width, height):
        return all(abs(x-other_x)*2 >= width+other_width+2*GAP or abs(z-other_z)*2 >= height+other_height+2*GAP
                   for other_x, other_z, other_width, other_height in self.placed)

    def block(self, x, z, width, height):
        """Reserves the space of something that is never moved, such as a launcher in its bay."""
        self.placed.append((x, z, width, height))

    def place(self, x, z, width, height):
        """Returns where the item goes as (x, z, fit, crowded), reserving that space."""
        if self._is_free(x, z, width, height):
            self.placed.append((x, z, width, height))
            return x, z, 1, False
        for fit in FITS:
            fitted_width, fitted_height = width*fit, height*fit
            spots = []
            reach_x, reach_z = (self.width-fitted_width)/2, (self.height-fitted_height)/2
            steps_x, steps_z = int(max(0, reach_x)/STEP), int(max(0, reach_z)/STEP)
            for step_x in range(-steps_x, steps_x+1):
                for step_z in range(-steps_z, steps_z+1):
                    spot_x, spot_z = self.center[0]+step_x*STEP, self.center[1]+step_z*STEP
                    spots.append(((spot_x-x)**2+(spot_z-z)**2, spot_x, spot_z))
            for _, spot_x, spot_z in sorted(spots):
                if self._is_free(spot_x, spot_z, fitted_width, fitted_height):
                    self.placed.append((spot_x, spot_z, fitted_width, fitted_height))
                    return spot_x, spot_z, fit, False
        # Nowhere to go even at the smallest size: leave it at its hard point and say so in the manifest.
        self.placed.append((x, z, width, height))
        return x, z, 1, True
