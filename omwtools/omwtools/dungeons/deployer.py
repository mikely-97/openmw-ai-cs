# omwtools/omwtools/dungeons/deployer.py
import shutil
from pathlib import Path

_MESH_SOURCE = Path(__file__).parent / "tilesets" / "meshes"


def deploy_tiles(tileset_name: str, game_dir: Path) -> list[str]:
    """
    Copy missing omwdg_*.dae files to <game_dir>/meshes/omwdg/.
    Never overwrites existing files (allows artist replacement).
    Returns list of filenames copied.
    """
    src_dir = _MESH_SOURCE / tileset_name
    dst_dir = game_dir / "meshes" / "omwdg"
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    if src_dir.exists():
        for src_file in src_dir.glob("omwdg_*.dae"):
            dst_file = dst_dir / src_file.name
            if not dst_file.exists():
                shutil.copy2(src_file, dst_file)
                copied.append(src_file.name)
    return copied
