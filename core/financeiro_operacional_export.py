"""Exportação de planilhas XLSX — financeiro operacional."""

from __future__ import annotations

import re
from decimal import Decimal
from io import BytesIO

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from .models import ExtraRecreador, ItemCompraSemanal, PagamentoAtracao, PeriodoOperacional

DIAS_SEMANA = (
    ('seg', 'Seg'),
    ('ter', 'Ter'),
    ('qua', 'Qua'),
    ('qui', 'Qui'),
    ('sex', 'Sex'),
    ('sab', 'Sáb'),
    ('dom', 'Dom'),
)

_HEADER_FILL = PatternFill('solid', fgColor='D9EAD3')
_HEADER_FONT = Font(bold=True)
_MONEY_FMT = '#,##0.00'


def _safe_filename(text: str) -> str:
    cleaned = re.sub(r'[^\w\-.]+', '_', text.strip(), flags=re.UNICODE)
    return cleaned[:80] or 'planilha'


def _workbook_bytes(wb: openpyxl.Workbook) -> bytes:
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _style_header_row(ws, row: int, cols: int) -> None:
    for col in range(1, cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = Alignment(horizontal='center')


def _write_periodo_info(ws, periodo: PeriodoOperacional, titulo: str) -> int:
    ws['A1'] = titulo
    ws['A1'].font = Font(bold=True, size=14)
    ws['A2'] = f'Período: {periodo.titulo}'
    ws['A3'] = (
        f'{periodo.data_inicio.strftime("%d/%m/%Y")} a '
        f'{periodo.data_fim.strftime("%d/%m/%Y")}'
    )
    row = 4
    if periodo.ocupacao_pct is not None:
        ws[f'A{row}'] = f'Ocupação: {periodo.ocupacao_pct}%'
        row += 1
    if periodo.qtd_pax:
        ws[f'A{row}'] = f'Hóspedes: {periodo.qtd_pax}'
        row += 1
    return row + 1


def exportar_extras_recreadores_xlsx(periodo: PeriodoOperacional) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Extras recreadores'

    header_row = _write_periodo_info(ws, periodo, 'Extras de recreadores')
    headers = ['Recreador', *[label for _, label in DIAS_SEMANA], 'Total']
    for col, title in enumerate(headers, start=1):
        ws.cell(row=header_row, column=col, value=title)
    _style_header_row(ws, header_row, len(headers))

    totais_dia = {dia: Decimal('0') for dia, _ in DIAS_SEMANA}
    data_row = header_row + 1
    extras = periodo.extras_recreadores.all()

    for extra in extras:
        ws.cell(row=data_row, column=1, value=extra.nome)
        for col, (dia, _) in enumerate(DIAS_SEMANA, start=2):
            valor = getattr(extra, f'valor_{dia}')
            cell = ws.cell(row=data_row, column=col, value=float(valor))
            cell.number_format = _MONEY_FMT
            totais_dia[dia] += valor
        total_cell = ws.cell(row=data_row, column=9, value=float(extra.total))
        total_cell.number_format = _MONEY_FMT
        data_row += 1

    footer_row = data_row
    ws.cell(row=footer_row, column=1, value='Totais do dia').font = _HEADER_FONT
    for col, (dia, _) in enumerate(DIAS_SEMANA, start=2):
        cell = ws.cell(row=footer_row, column=col, value=float(totais_dia[dia]))
        cell.number_format = _MONEY_FMT
        cell.font = _HEADER_FONT
    total_geral = sum(totais_dia.values())
    total_cell = ws.cell(row=footer_row, column=9, value=float(total_geral))
    total_cell.number_format = _MONEY_FMT
    total_cell.font = _HEADER_FONT

    ws.column_dimensions['A'].width = 22
    for col in 'BCDEFGH':
        ws.column_dimensions[col].width = 12
    ws.column_dimensions['I'].width = 14

    return _workbook_bytes(wb)


def exportar_atracoes_xlsx(periodo: PeriodoOperacional) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Atrações'

    header_row = _write_periodo_info(ws, periodo, 'Pagamentos de atrações / artistas')
    headers = [
        'Data', 'Artista', 'Atração', 'Valor (R$)', 'Chave PIX',
        'Evento', 'Status', 'Autorização', 'Observações',
    ]
    for col, title in enumerate(headers, start=1):
        ws.cell(row=header_row, column=col, value=title)
    _style_header_row(ws, header_row, len(headers))

    data_row = header_row + 1
    total = Decimal('0')
    pagamentos = PagamentoAtracao.objects.filter(periodo=periodo).order_by('data_evento', 'artista')

    for pag in pagamentos:
        data_txt = ''
        if pag.data_evento:
            data_txt = pag.data_evento.strftime('%d/%m/%Y')
        elif pag.data_label:
            data_txt = pag.data_label

        ws.cell(row=data_row, column=1, value=data_txt)
        ws.cell(row=data_row, column=2, value=pag.artista)
        ws.cell(row=data_row, column=3, value=pag.atracao)
        valor_cell = ws.cell(row=data_row, column=4, value=float(pag.valor))
        valor_cell.number_format = _MONEY_FMT
        ws.cell(row=data_row, column=5, value=pag.chave_pix)
        ws.cell(row=data_row, column=6, value=pag.evento)
        ws.cell(row=data_row, column=7, value=pag.get_status_display())
        ws.cell(row=data_row, column=8, value=pag.autorizacao_diretoria)
        ws.cell(row=data_row, column=9, value=pag.observacoes)
        total += pag.valor
        data_row += 1

    ws.cell(row=data_row, column=3, value='TOTAL').font = _HEADER_FONT
    total_cell = ws.cell(row=data_row, column=4, value=float(total))
    total_cell.number_format = _MONEY_FMT
    total_cell.font = _HEADER_FONT

    ws.column_dimensions['A'].width = 14
    ws.column_dimensions['B'].width = 24
    ws.column_dimensions['C'].width = 20
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 28
    ws.column_dimensions['F'].width = 22
    ws.column_dimensions['G'].width = 12
    ws.column_dimensions['H'].width = 14
    ws.column_dimensions['I'].width = 30

    return _workbook_bytes(wb)


def exportar_compras_xlsx(periodo: PeriodoOperacional) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Compras'

    header_row = _write_periodo_info(ws, periodo, 'Compras semanais de materiais')
    headers = ['Material', 'Quantidade', 'Link fornecedor', 'Preço unitário', 'Preço total']
    for col, title in enumerate(headers, start=1):
        ws.cell(row=header_row, column=col, value=title)
    _style_header_row(ws, header_row, len(headers))

    data_row = header_row + 1
    total = Decimal('0')
    itens = ItemCompraSemanal.objects.filter(periodo=periodo).order_by('ordem', 'descricao')

    for item in itens:
        ws.cell(row=data_row, column=1, value=item.descricao)
        ws.cell(row=data_row, column=2, value=item.quantidade)
        ws.cell(row=data_row, column=3, value=item.link_fornecedor)
        unit_cell = ws.cell(row=data_row, column=4, value=float(item.preco_unitario))
        unit_cell.number_format = _MONEY_FMT
        total_item = item.preco_total
        total_cell = ws.cell(row=data_row, column=5, value=float(total_item))
        total_cell.number_format = _MONEY_FMT
        total += total_item
        data_row += 1

    ws.cell(row=data_row, column=4, value='TOTAL').font = _HEADER_FONT
    total_cell = ws.cell(row=data_row, column=5, value=float(total))
    total_cell.number_format = _MONEY_FMT
    total_cell.font = _HEADER_FONT

    ws.column_dimensions['A'].width = 36
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 40
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 14

    return _workbook_bytes(wb)


def nome_arquivo_extras(periodo: PeriodoOperacional) -> str:
    return f'{_safe_filename(periodo.titulo)}_extras_recreadores.xlsx'


def nome_arquivo_atracoes(periodo: PeriodoOperacional) -> str:
    return f'{_safe_filename(periodo.titulo)}_atracoes.xlsx'


def nome_arquivo_compras(periodo: PeriodoOperacional) -> str:
    return f'{_safe_filename(periodo.titulo)}_compras.xlsx'
