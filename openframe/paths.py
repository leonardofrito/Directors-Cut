"""Read-only bundled resources and persistent user data must never share a temp root."""
import os,sys
from pathlib import Path
RESOURCE_ROOT=Path(__file__).resolve().parent.parent

def user_data_root():
    override=os.environ.get('OPENFRAME_DATA')
    if override:return Path(override).expanduser().resolve()
    if not getattr(sys,'frozen',False):return RESOURCE_ROOT
    home=Path.home()
    if sys.platform=='win32':return Path(os.environ.get('LOCALAPPDATA',home/'AppData/Local'))/'DirectorsCut'
    if sys.platform=='darwin':return home/'Library/Application Support/DirectorsCut'
    return Path(os.environ.get('XDG_DATA_HOME',home/'.local/share'))/'directors-cut'

DATA_ROOT=user_data_root()
