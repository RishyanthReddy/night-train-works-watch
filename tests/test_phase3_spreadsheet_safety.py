"""Authored XLSM/formula samples are read as values, never executed."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from openpyxl import Workbook
from nightdesk.intake.table import read_table


def test_xlsm_ignores_authored_vba_payload_and_formula_evaluation(tmp_path):
    source=tmp_path/'authored.xlsx';wb=Workbook();ws=wb.active
    ws.append(['id','value','formula']);ws.append(['synthetic',7,'=1+2']);wb.save(source)
    target=tmp_path/'authored.xlsm';sentinel=tmp_path/'macro-executed'
    payload=('Sub Auto_Open()\nOpen "'+str(sentinel)+'" For Output As #1\nPrint #1, "synthetic"\nEnd Sub').encode()
    with ZipFile(source) as original,ZipFile(target,'w',ZIP_DEFLATED) as output:
        for info in original.infolist():output.writestr(info.filename,original.read(info.filename))
        output.writestr('xl/vbaProject.bin',payload)
    before=target.read_bytes();table=read_table(target)
    assert table.rows==[{'id':'synthetic','value':7,'formula':None}]
    assert not sentinel.exists() and target.read_bytes()==before
