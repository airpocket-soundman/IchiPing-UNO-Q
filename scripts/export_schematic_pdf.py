"""Export the current schematic page with EasyEDA's documented native exporter."""
import sys
from pcb_local_audit import api, ROOT
from schematic_readability import activate, PAGES

board=sys.argv[1]
activate(board)
data=api('const TYPE={PDF:"PDF"};const f=await eda.sch_ManufactureData.getExportDocumentFile("review",TYPE.PDF,{theme:"Default",lineWidth:"Default",displayAttributesAsMenu:false,size:"Original Size"},"Current Schematic Page",{range:"All",outputMethod:"Merged sheet"});if(!f)throw Error("No PDF returned");return Array.from(new Uint8Array(await f.arrayBuffer()));')
path=ROOT/'output/pdf'/f'{board}-schematic-after.pdf'
path.write_bytes(bytes(data))
print(path,len(data))
