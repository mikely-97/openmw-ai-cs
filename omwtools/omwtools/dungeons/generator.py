import random
from collections import deque
from .dungeon_spec import DungeonSpec, DungeonLayout, Room


def generate(spec: DungeonSpec, seed: int) -> DungeonLayout:
    rng = random.Random(seed)
    rooms = _place_rooms(spec, rng)

    # Collect all room floor tiles
    room_tiles: set[tuple[int, int]] = set()
    for room in rooms:
        room_tiles.update(room.room_tiles())

    # Carve corridors — returns only the NEW tiles added (not already room tiles)
    corridor_tiles: set[tuple[int, int]] = set()
    _carve_corridors(rooms, room_tiles, corridor_tiles)

    floor_tiles = room_tiles | corridor_tiles
    boundary_tiles = _compute_boundary(floor_tiles, corridor_tiles)

    anchor_tiles = [r.centre_tile for r in rooms]
    return DungeonLayout(
        spec=spec,
        seed=seed,
        rooms=rooms,
        floor_tiles=floor_tiles,
        corridor_tiles=corridor_tiles,
        boundary_tiles=boundary_tiles,
        anchor_tiles=anchor_tiles,
        entrance_tile=rooms[0].centre_tile,
        exit_tile=rooms[-1].centre_tile,
    )


def _place_rooms(spec: DungeonSpec, rng: random.Random) -> list[Room]:
    count = rng.randint(*spec.room_count)
    rooms: list[Room] = []
    grid_size = max(spec.room_count[1] * spec.room_size[1] * 2, 30)
    max_attempts = 300
    while len(rooms) < count and max_attempts > 0:
        max_attempts -= 1
        w = rng.randint(*spec.room_size)
        h = rng.randint(*spec.room_size)
        x = rng.randint(1, grid_size - w - 1)
        y = rng.randint(1, grid_size - h - 1)
        candidate = Room(x=x, y=y, w=w, h=h)
        if not any(candidate.overlaps(r, margin=3) for r in rooms):
            rooms.append(candidate)
    if len(rooms) == 0:
        raise RuntimeError(
            f"Failed to place any rooms for spec '{spec.name}' with room_size={spec.room_size}. "
            "Try increasing grid_size or reducing room_size."
        )
    rooms.sort(key=lambda r: r.centre_tile[0])
    return rooms


def _carve_corridors(
    rooms: list[Room],
    room_tiles: set[tuple[int, int]],
    corridor_tiles: set[tuple[int, int]],
) -> None:
    """Connect rooms via a minimum spanning tree (by Manhattan distance).

    Routing uses BFS that avoids:
      - Room interiors (room_tiles)
      - Tiles adjacent to any room wall at a non-doorway position (forbidden)

    This guarantees every corridor tile adjacent to a room wall is at the
    wall's centre doorway position.  BFS produces L-shaped paths on open
    grids and routes cleanly around obstacles when rooms are nearby.
    """
    # Tiles adjacent to a room wall at a non-centre (non-doorway) position.
    forbidden: set[tuple[int, int]] = set()
    for r in rooms:
        rx, ry = r.centre_tile
        for tx in range(r.x, r.x + r.w):
            if tx != rx:
                forbidden.add((tx, r.y + r.h))   # north face, wrong col
                forbidden.add((tx, r.y - 1))      # south face, wrong col
        for ty in range(r.y, r.y + r.h):
            if ty != ry:
                forbidden.add((r.x + r.w, ty))    # east face, wrong row
                forbidden.add((r.x - 1, ty))      # west face, wrong row

    blocked = room_tiles | forbidden

    # MST via Kruskal's (Manhattan distance between room centres)
    n = len(rooms)
    edges = sorted(
        (abs(rooms[i].centre_tile[0] - rooms[j].centre_tile[0]) +
         abs(rooms[i].centre_tile[1] - rooms[j].centre_tile[1]), i, j)
        for i in range(n) for j in range(i + 1, n)
    )
    parent = list(range(n))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    # BFS bounding box: rooms extent + small pad
    pad = 4
    bx_min = min(r.x for r in rooms) - pad
    bx_max = max(r.x + r.w for r in rooms) + pad
    by_min = min(r.y for r in rooms) - pad
    by_max = max(r.y + r.h for r in rooms) + pad

    for _, i, j in edges:
        pi, pj = _find(i), _find(j)
        if pi == pj:
            continue
        parent[pi] = pj
        path = _bfs_path(rooms[i], rooms[j], blocked, bx_min, bx_max, by_min, by_max)
        for tile in path:
            corridor_tiles.add(tile)


def _bfs_path(
    a: Room, b: Room,
    blocked: set[tuple[int, int]],
    x_min: int, x_max: int, y_min: int, y_max: int,
) -> list[tuple[int, int]]:
    """BFS from any doorway tile of room *a* to any doorway tile of room *b*.

    Doorway tiles are the one tile just outside each wall centre:
      north: (cx, y+h)   south: (cx, y-1)
      east:  (x+w, cy)   west:  (x-1, cy)
    """
    ax, ay = a.centre_tile
    bx, by = b.centre_tile
    targets: frozenset[tuple[int, int]] = frozenset({
        (bx, b.y + b.h), (bx, b.y - 1),
        (b.x + b.w, by), (b.x - 1, by),
    })

    prev: dict[tuple[int, int], tuple[int, int] | None] = {}
    queue: deque[tuple[int, int]] = deque()
    for src in ((ax, a.y + a.h), (ax, a.y - 1), (a.x + a.w, ay), (a.x - 1, ay)):
        if src not in blocked and src not in prev:
            prev[src] = None
            queue.append(src)

    found: tuple[int, int] | None = None
    while queue and found is None:
        cur = queue.popleft()
        if cur in targets:
            found = cur
            break
        cx2, cy2 = cur
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nb = (cx2 + dx, cy2 + dy)
            if (nb not in blocked and nb not in prev
                    and x_min <= nb[0] <= x_max and y_min <= nb[1] <= y_max):
                prev[nb] = cur
                queue.append(nb)

    if found is None:
        return []
    path: list[tuple[int, int]] = []
    node: tuple[int, int] | None = found
    while node is not None:
        path.append(node)
        node = prev[node]
    return path


def _compute_boundary(
    floor_tiles: set[tuple[int, int]],
    corridor_tiles: set[tuple[int, int]],
) -> dict[tuple[int, int], str]:
    """
    For each non-floor tile adjacent to a floor tile, determine its type.
    A boundary tile adjacent to a corridor floor tile at a corridor-room junction
    is classified as "doorway" instead of a plain wall.
    """
    candidates: set[tuple[int, int]] = set()
    for tx, ty in floor_tiles:
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
            nb = (tx + dx, ty + dy)
            if nb not in floor_tiles:
                candidates.add(nb)

    boundary: dict[tuple[int, int], str] = {}
    for tx, ty in candidates:
        n = (tx,   ty-1) in floor_tiles
        s = (tx,   ty+1) in floor_tiles
        e = (tx+1, ty  ) in floor_tiles
        w = (tx-1, ty  ) in floor_tiles
        is_doorway = _is_doorway(tx, ty, floor_tiles, corridor_tiles)
        tile_type = _classify_boundary(n, s, e, w, is_doorway)
        if tile_type:
            boundary[(tx, ty)] = tile_type
    return boundary


def _is_doorway(
    tx: int, ty: int,
    floor_tiles: set[tuple[int, int]],
    corridor_tiles: set[tuple[int, int]],
) -> bool:
    """
    A boundary tile is a doorway if it has exactly one cardinal corridor neighbour
    AND at least one cardinal floor neighbour that is a room tile (not corridor).
    This ensures we only mark doorways at true corridor-room junctions.
    """
    cardinal = [(tx, ty-1), (tx, ty+1), (tx+1, ty), (tx-1, ty)]
    corridor_neighbours = [p for p in cardinal if p in corridor_tiles]
    room_neighbours = [p for p in cardinal if p in floor_tiles and p not in corridor_tiles]
    return len(corridor_neighbours) == 1 and len(room_neighbours) >= 1


def _classify_boundary(n: bool, s: bool, e: bool, w: bool, is_doorway: bool) -> str | None:
    """Return tile type string for a boundary tile, or None if no tile needed."""
    if is_doorway:
        return "doorway"
    if s and not n and not e and not w:
        return "wall_n"
    if n and not s and not e and not w:
        return "wall_s"
    if w and not e and not n and not s:
        return "wall_e"
    if e and not w and not n and not s:
        return "wall_w"
    if s and e and not n and not w:
        return "corner_ne"
    if s and w and not n and not e:
        return "corner_nw"
    if n and e and not s and not w:
        return "corner_se"
    if n and w and not s and not e:
        return "corner_sw"
    if (n or s) and (e or w):
        return "pillar"
    return None
