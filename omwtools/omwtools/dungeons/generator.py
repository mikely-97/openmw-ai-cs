import random
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
        if not any(candidate.overlaps(r) for r in rooms):
            rooms.append(candidate)
    rooms.sort(key=lambda r: r.centre_tile[0])
    return rooms


def _carve_corridors(
    rooms: list[Room],
    room_tiles: set[tuple[int, int]],
    corridor_tiles: set[tuple[int, int]],
) -> None:
    """Connect each room to the next with an L-shaped corridor.
    Only adds tiles that are NOT already room tiles to corridor_tiles.
    """
    for i in range(len(rooms) - 1):
        ax, ay = rooms[i].centre_tile
        bx, by = rooms[i + 1].centre_tile
        # Horizontal leg
        for tx in range(min(ax, bx), max(ax, bx) + 1):
            if (tx, ay) not in room_tiles:
                corridor_tiles.add((tx, ay))
        # Vertical leg
        for ty in range(min(ay, by), max(ay, by) + 1):
            if (bx, ty) not in room_tiles:
                corridor_tiles.add((bx, ty))


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
    A boundary tile is a doorway if it has exactly one cardinal floor neighbour
    that is a corridor tile (the corridor is entering a room through this position).
    """
    cardinal = [(tx, ty-1), (tx, ty+1), (tx+1, ty), (tx-1, ty)]
    corridor_neighbours = [p for p in cardinal if p in corridor_tiles]
    return len(corridor_neighbours) == 1


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
