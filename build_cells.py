
import sys, csv, pprint, json

(inf, outf) = sys.argv[1 : ]

IGNORE = set([
    'kingdom', 'kingdomKey', 'phylum', 'specificEpithet', 'taxonRank',
    'taxonKey', 'previousIdentifications', 'order', 'taxonomicStatus',
    'verbatimScientificName', 'acceptedNameUsageID', 'class', 'day',
    'month', 'family', 'familyKey', 'genericName', 'genus',
    'genusKey', 'license', 'lastParsed', 'lastInterpreted', 'lastCrawled',
    'institutionCode', 'vernacularName', 'stateProvince', 'species',
    'speciesKey', 'countryCode', 'publishingCountry', 'rightsHolder',
    'scientificName',
])

MIN_OBSERVATIONS = 0.35
UNCONFIRMED_WEIGHT = 0.9
MAX_NORTH = 72
MAX_SOUTH = 34
MAX_WEST  = -16
MAX_EAST  = 63
DELTA = 0.15
AVERAGING = False
SMOOTH = True
MIN_NEIGHBOURS = 5 # 4 just expands far too much

# ===== CONSTANTS AND STRUCTURES

DELTA_INVERSE = 1 / DELTA
NORTH_SOUTH = int((MAX_NORTH - MAX_SOUTH) / DELTA) + 1
EAST_WEST = int((MAX_EAST - MAX_WEST) / DELTA) + 1

cells = [
    [0] * EAST_WEST for ix in range(NORTH_SOUTH)
]
MAX_Y = len(cells)
MAX_X = len(cells[0])
DIRECTIONS_9 = [(-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1)]
DIRECTIONS_4 = [
    (1, 0),   # 0 = up
    (0, 1),   # 1 = right
    (-1, 0),  # 2 = down
    (0, -1)   # 3 = left
]

# ===== LOAD DATA INTO CELLS
r = csv.DictReader(open(inf), dialect = csv.excel_tab)
for row in r:
    row = {k : v for (k, v) in row.items() if v and (k not in IGNORE)}
    if (row['hasCoordinate'] == 'false' or
        row['occurrenceStatus'] == 'ABSENT' or
        ('decimalLatitude' not in row) or
        ('decimalLongitude' not in row)):
        continue

    # pprint.pprint(row)
    # break

    lat = float(row['decimalLatitude'])
    lng = float(row['decimalLongitude'])

    if (lat >= MAX_NORTH or lat <= MAX_SOUTH or
        lng >= MAX_EAST or lng <= MAX_WEST):
        continue

    y = int((lat - MAX_SOUTH) * DELTA_INVERSE)
    x = int((lng - MAX_WEST) * DELTA_INVERSE)

    verification = row.get('identificationVerificationStatus', '').lower()
    if any([verification.startswith(prefix) for prefix in
            ['accepted', 'approved', 'confirmed', 'validated']]):
        weight = 1.0
    else:
        weight = UNCONFIRMED_WEIGHT

    cells[y][x] = cells[y][x] + weight

# ===== AVERAGING

if AVERAGING:
    new_cells = [
        [0] * EAST_WEST for ix in range(NORTH_SOUTH)
    ]
    for y in range(MAX_Y):
        for x in range(MAX_X):
            total = 0
            for (dy, dx) in DIRECTIONS_9:
                if (y + dy < 0 or y + dy >= MAX_Y or
                    x + dx < 0 or x + dx >= MAX_X):
                    continue

                total += cells[y+dy][x+dx]

            new_cells[y][x] = total / 9.0
    cells = new_cells

# ===== FILTER
cells = [
    [(count >= MIN_OBSERVATIONS) for count in column] for column in cells
]

# ===== FILL IN & REGULARIZE

def regularize(directions, minimum):
    added = 1
    while added:
        added = 0
        for y in range(MAX_Y):
            for x in range(MAX_X):
                if cells[y][x]:
                    continue

                if count_neighbours(y, x, directions) >= minimum:
                    cells[y][x] = True
                    added += 1

        print 'Added %s new blocks' % added

def count_neighbours(y, x, directions):
    count = 0
    for (dy, dx) in directions:
        if (y + dy < 0 or y + dy >= MAX_Y or
            x + dx < 0 or x + dx >= MAX_X):
            continue

        count += 1 if cells[y+dy][x+dx] else 0
    return count

if SMOOTH:
    regularize(DIRECTIONS_9, MIN_NEIGHBOURS)

# ===== SAVE

with open(outf, 'w') as f:
    json.dump({
        'MAX_NORTH' : MAX_NORTH,
        'MAX_SOUTH' : MAX_SOUTH,
        'MAX_EAST' : MAX_EAST,
        'MAX_WEST' : MAX_WEST,
        'DELTA' : DELTA,
        'cells' : cells,
    }, f)
