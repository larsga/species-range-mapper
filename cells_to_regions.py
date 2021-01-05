'''
Process map grid cell JSON file into a GeoJSON file with polygons outlining
the areas where the species can be found.

Requires shapely iff SMOOTH == True.
'''

import sys, json

(inf, outf) = sys.argv[1 : ]

SMOOTH = True
MIN_SIZE = 5  # discard groups of contiguous cells smaller than this

data = json.load(open(inf))
MAX_NORTH = data['MAX_NORTH']
MAX_SOUTH = data['MAX_SOUTH']
MAX_WEST  = data['MAX_WEST']
MAX_EAST  = data['MAX_EAST']
DELTA = data['DELTA']
cells = data['cells']

MAX_Y = len(cells)
MAX_X = len(cells[0])

DIRECTIONS_9 = [(-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1)]

def debug(txt, param):
    pass #print txt, param

# ===== OUTPUT FEATURES

# offsets to corners when direction = 0. can be rotated with direction
CORNERS = [
    (0, 0), # lower left
    (1, 0), # upper left
    (1, 1), # upper right
    (0, 1), # lower right
]
def corner(point, corner_no):
    (y, x) = point
    y += CORNERS[corner_no][0]
    x += CORNERS[corner_no][1]
    return [MAX_WEST + x * DELTA, MAX_SOUTH + (y) * DELTA]

# FEATURE CLASS

class Feature:

    def __init__(self, y, x):
        self._start_y = y
        self._start_x = x
        # these are resolved corner points in WGS84 coords, not cell indexes
        self._outline = []

    def get_start_point(self):
        return (self._start_y, self._start_x)

    def get_polygon(self):
        return self._outline

    def wipe(self):
        queue = set([(self._start_y, self._start_x)])

        count = 0
        while queue:
            (y, x) = queue.pop()
            cells[y][x] = False
            count += 1
            for (dy, dx) in DIRECTIONS_4:
                if (y + dy < 0 or y + dy >= MAX_Y or
                    x + dx < 0 or x + dx >= MAX_X):
                    continue
                if cells[y + dy][x + dx]:
                    queue.add((y + dy, x + dx))

        return count

    def add_point(self, point):
        debug('point', point)
        self._outline.append(point)

    def close_polygon(self):
        self.add_point(self._outline[0])

# BOUNDARY WALKER

DIRECTIONS_4 = [
    (1, 0),   # 0 = up
    (0, 1),   # 1 = right
    (-1, 0),  # 2 = down
    (0, -1)   # 3 = left
]

class BoundaryWalker:

    def __init__(self, y, x):
        self._y = y
        self._x = x
        self._direction = 0

    def get_position(self):
        return (self._y, self._x)

    def can_go_left(self):
        return self._filled_cell_in_direction(self._turn(3))

    def can_go_ahead(self):
        return self._filled_cell_in_direction(self._direction)

    def can_go_right(self):
        return self._filled_cell_in_direction(self._turn(1))

    def _filled_cell_in_direction(self, direction):
        (y1, x1) = self._moved_in_dir(direction)
        if (y1 < 0 or y1 >= MAX_Y or
            x1 < 0 or x1 >= MAX_X):
            return False
        return cells[y1][x1]

    def turn_left(self):
        self._direction = self._turn(3)

    def turn_right(self):
        self._direction = self._turn(1)

    def turn_about(self):
        self._direction = self._turn(2)

    def _turn(self, amount):
        return (self._direction + amount) % 4

    def get_direction(self):
        return self._direction

    def _moved_in_dir(self, direction):
        return (self._y + DIRECTIONS_4[direction][0],
                self._x + DIRECTIONS_4[direction][1])

    def step(self):
        (self._y, self._x) = self._moved_in_dir(self._direction)
        debug('to', self.get_position())

    def get_lower_left(self):
        return corner(self.get_position(), (self._direction + 0) % 4)

    def get_upper_left(self):
        return corner(self.get_position(), (self._direction + 1) % 4)

    def get_upper_right(self):
        return corner(self.get_position(), (self._direction + 2) % 4)

    def get_lower_right(self):
        return corner(self.get_position(), (self._direction + 3) % 4)

def get_feature(y, x):
    while y < MAX_Y:
        while x < MAX_X and not(cells[y][x]):
            x += 1

        if x < MAX_X and cells[y][x]:
            break

        y += 1
        x = 0

    if y >= MAX_Y:
        return None

    feature = Feature(y, x)

    first_step = True
    walker = BoundaryWalker(y, x)
    while walker.get_position() != feature.get_start_point() or first_step:
        if walker.can_go_left():
            feature.add_point(walker.get_lower_left())
            walker.turn_left()
        elif walker.can_go_ahead():
            feature.add_point(walker.get_lower_left())
        elif walker.can_go_right():
            if first_step:
                feature.add_point(walker.get_lower_left())
            feature.add_point(walker.get_upper_left())
            walker.turn_right()
        elif not first_step: # if first step, there is nowhere to go back to
            feature.add_point(walker.get_lower_left())
            feature.add_point(walker.get_upper_left())
            feature.add_point(walker.get_upper_right())
            walker.turn_about() # got to go back where we came from
        else:
            # this feature is just a single square, so draw all corners
            feature.add_point(walker.get_lower_left())
            feature.add_point(walker.get_upper_left())
            feature.add_point(walker.get_upper_right())
            feature.add_point(walker.get_lower_right())
            break

        walker.step()
        first_step = False

    if walker.get_direction() == 2: # down
        feature.add_point(walker.get_upper_left())

    feature.close_polygon()
    return feature

polygons = []
x,y = 0,0
while True:
    feature = get_feature(y, x)
    if not feature:
        break

    size = feature.wipe()
    if size >= MIN_SIZE:
        polygons.append(feature.get_polygon())
    y,x = feature.get_start_point()

# ===== SMOOTH POLYGONS

def smooth(p):
    r = 64
    return list(Polygon(p)
                .buffer(0.5, resolution = r)
                .buffer(-0.5, resolution = r)
                .buffer(0.5, resolution = r)
                .buffer(-0.5, resolution = r)
                .buffer(0.5, resolution = r)
                .buffer(-0.4, resolution = r) # extend perimeter by 0.1 degrees
                .exterior.coords)

if SMOOTH:
    from shapely.geometry import Polygon
    polygons = [
        smooth(p) for p in polygons
    ]

# ===== GEOJSON OUTPUT

with open(outf, 'w') as f:
    json.dump({
        "type": "FeatureCollection",
        "name": "species-range-distribution",
        "features": [{
            'type' : 'Feature',
            'geometry' : {
                'type' : 'Polygon',
                'coordinates' : [coordinates]
            }
        } for coordinates in polygons]
    }, f)
