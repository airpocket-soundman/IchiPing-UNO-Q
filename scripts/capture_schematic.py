"""Capture the live rendered schematic for independent visual verification."""
import sys
from pcb_local_audit import api, OUT
from schematic_readability import activate
board=sys.argv[1]
doc=activate(board)
result=api('const b=await eda.dmt_EditorControl.getCurrentRenderedAreaImage('+repr(doc['tabId'])+');return Array.from(new Uint8Array(await b.arrayBuffer()));')
path=OUT/f'{board}-rendered-current.png'
path.write_bytes(bytes(result))
print(path)
