"""Cruzamento de atividades × faixas etárias (planilha ou banco)."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import BinaryIO

from django.utils import timezone

from .importacao_xlsx import LinhaProgramacao, extrair_linhas_programacao
from .models import CategoriaProgramacao, Hotel, ProgramacaoDiaria


@dataclass
class AtividadeFaixaScore:
    nome: str
    ocorrencias: int
    exclusividade_pct: float
    score: float
    outras_faixas: list[str] = field(default_factory=list)
    recomendacao: str = ''
    locais_top: list[str] = field(default_factory=list)


@dataclass
class FaixaCruzamento:
    label: str
    categoria_codigo: str | None
    idade_sistema: str
    total_linhas: int
    atividades_distintas: int
    top_atividades: list[AtividadeFaixaScore] = field(default_factory=list)


@dataclass
class ResultadoCruzamento:
    fonte: str
    total_linhas: int
    faixas: list[FaixaCruzamento] = field(default_factory=list)
    multifaixa: list[dict] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)

    @property
    def matriz(self) -> list[dict]:
        """Top 5 atividades por faixa para tabela cruzada."""
        tops = {}
        for f in self.faixas:
            tops[f.label] = [a.nome for a in f.top_atividades[:5]]
        max_len = max((len(v) for v in tops.values()), default=0)
        labels = [f.label for f in self.faixas]
        rows = []
        for i in range(max_len):
            rows.append({
                'rank': i + 1,
                'cells': [
                    tops[label][i] if i < len(tops[label]) else '—'
                    for label in labels
                ],
            })
        return rows


def _idade_sistema(codigo: str | None) -> str:
    if not codigo:
        return '—'
    cat = CategoriaProgramacao.objects.filter(codigo=codigo).first()
    return cat.faixa_label if cat else codigo


def _calcular_cruzamento(linhas: list[LinhaProgramacao], fonte: str) -> ResultadoCruzamento:
    resultado = ResultadoCruzamento(fonte=fonte, total_linhas=len(linhas))
    if not linhas:
        return resultado

    por_faixa_ativ: Counter[tuple[str, str]] = Counter()
    global_ativ: Counter[str] = Counter()
    ativ_faixas: dict[str, set[str]] = defaultdict(set)
    locais_faixa_ativ: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for ln in linhas:
        key = (ln.faixa_label, ln.atividade)
        por_faixa_ativ[key] += 1
        global_ativ[ln.atividade] += 1
        ativ_faixas[ln.atividade].add(ln.faixa_label)
        if ln.local:
            locais_faixa_ativ[key][ln.local] += 1

    faixas_ordem = []
    vistos = set()
    for ln in linhas:
        if ln.faixa_label not in vistos:
            vistos.add(ln.faixa_label)
            faixas_ordem.append((ln.faixa_label, ln.categoria_codigo))

    for faixa_label, codigo in faixas_ordem:
        ativs_faixa = Counter({
            ativ: cnt for (f, ativ), cnt in por_faixa_ativ.items() if f == faixa_label
        })
        scores: list[AtividadeFaixaScore] = []
        for ativ, cnt_f in ativs_faixa.most_common():
            total_g = global_ativ[ativ]
            excl = round(cnt_f / total_g * 100, 1) if total_g else 0
            outras = sorted(ativ_faixas[ativ] - {faixa_label})
            freq_bonus = min(30.0, cnt_f * 0.5)
            score = round(excl * 0.7 + freq_bonus, 1)

            if excl >= 85:
                rec = 'Ideal para esta faixa'
            elif excl >= 55:
                rec = 'Boa combinação'
            elif len(ativ_faixas[ativ]) >= 3:
                rec = 'Multifaixa — evento família'
            elif outras:
                rec = f'Também em: {", ".join(outras[:2])}'
            else:
                rec = 'Atividade recorrente'

            locais = [
                loc for loc, _ in locais_faixa_ativ[(faixa_label, ativ)].most_common(2)
            ]
            scores.append(AtividadeFaixaScore(
                nome=ativ,
                ocorrencias=cnt_f,
                exclusividade_pct=excl,
                score=score,
                outras_faixas=outras,
                recomendacao=rec,
                locais_top=locais,
            ))

        scores.sort(key=lambda s: (-s.score, -s.ocorrencias))
        resultado.faixas.append(FaixaCruzamento(
            label=faixa_label,
            categoria_codigo=codigo,
            idade_sistema=_idade_sistema(codigo),
            total_linhas=sum(ativs_faixa.values()),
            atividades_distintas=len(ativs_faixa),
            top_atividades=scores[:15],
        ))

    multifaixa = []
    for ativ, faixas_set in ativ_faixas.items():
        if len(faixas_set) >= 3:
            multifaixa.append({
                'nome': ativ,
                'faixas': sorted(faixas_set),
                'total': global_ativ[ativ],
            })
    multifaixa.sort(key=lambda x: -x['total'])
    resultado.multifaixa = multifaixa[:20]

    return resultado


def cruzar_planilha(arquivo: BinaryIO) -> ResultadoCruzamento:
    linhas, erros = extrair_linhas_programacao(arquivo)
    r = _calcular_cruzamento(linhas, fonte='planilha')
    r.erros = erros
    return r


def cruzar_banco(hotel: Hotel, *, dias: int = 90) -> ResultadoCruzamento:
    """Cruzamento a partir dos dados já importados no sistema."""
    desde = timezone.localdate() - timedelta(days=dias)
    qs = (
        ProgramacaoDiaria.objects.filter(hotel=hotel, data__gte=desde)
        .select_related('atividade', 'categoria', 'local')
    )
    linhas: list[LinhaProgramacao] = []
    for p in qs.iterator():
        faixa = p.categoria.nome if p.categoria else 'Sem faixa'
        if p.categoria:
            codigo = p.categoria.codigo
            # Refinar label se observações ou categoria genérica
            faixa_label = faixa_label_from_categoria(codigo) or faixa
        else:
            codigo = None
            faixa_label = faixa
        linhas.append(LinhaProgramacao(
            aba='banco',
            faixa_label=faixa_label,
            categoria_codigo=codigo,
            data=p.data,
            hora=p.hora_inicio,
            atividade=p.atividade.nome,
            local=p.local.nome if p.local else '',
        ))
    return _calcular_cruzamento(linhas, fonte=f'banco ({dias} dias)')


def faixa_label_from_categoria(codigo: str) -> str | None:
    mapping = {
        'vulcao-kids': 'Boys & Girls 7–12',
        'boys-girls': 'Teens 13–17',
        'adultos': 'Adultos 18–59',
        'melhor-idade': 'Melhor Idade 60+',
    }
    return mapping.get(codigo)


def melhor_faixa_para_atividade(resultado: ResultadoCruzamento, nome_atividade: str) -> str | None:
    """Retorna a faixa com maior score para uma atividade."""
    melhor = None
    melhor_score = -1.0
    for faixa in resultado.faixas:
        for ativ in faixa.top_atividades:
            if ativ.nome.lower() == nome_atividade.lower():
                if ativ.score > melhor_score:
                    melhor_score = ativ.score
                    melhor = faixa.label
    return melhor
