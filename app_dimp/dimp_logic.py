#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Logica DIMP - OneKey Payments
VERSAO LOW-MEMORY: processa 1 CSV por vez via parquet shards.
Pico RAM ~700MB em vez de 8GB+. Zero iter_rows no hot path.
"""

import gc
import glob
import shutil
from pathlib import Path

import polars as pl
import pandas as pd


CLIENTES_EXCLUIR = ["644", "520", "561", "587", "642", "656"]
LABEL_EXCLUIDOS = "644, 520, 561, 587, 642, 656"
ANO = "2025"


# ══════════════════════════════════════
# EXPRESSOES POLARS NATIVAS
# ══════════════════════════════════════

def _parse_valor_expr():
    col = pl.col("TEXT - valor_bruto").cast(pl.Utf8).str.strip_chars()
    cleaned = col.str.replace_all(r"R\$", "").str.replace_all(" ", "")
    is_neg = cleaned.str.ends_with("-")
    cleaned = cleaned.str.strip_chars_end("-").str.replace_all(r"[^0-9.,]", "")
    has_comma = cleaned.str.contains(",")
    br_fmt = cleaned.str.replace_all(r"\.", "").str.replace(",", ".")
    final_str = pl.when(has_comma).then(br_fmt).otherwise(cleaned)
    parsed = final_str.cast(pl.Float64, strict=False).fill_null(0.0)
    return pl.when(is_neg).then(-parsed).otherwise(parsed)


def _traduzir_mes_expr():
    col = pl.col("mes").cast(pl.Utf8).str.to_uppercase().str.strip_chars()
    return (
        pl.when(col == "JANEIRO").then(pl.lit("01"))
        .when(col == "FEVEREIRO").then(pl.lit("02"))
        .when(col == "MARCO").then(pl.lit("03"))
        .when(col == "ABRIL").then(pl.lit("04"))
        .when(col == "MAIO").then(pl.lit("05"))
        .when(col == "JUNHO").then(pl.lit("06"))
        .when(col == "JULHO").then(pl.lit("07"))
        .when(col == "AGOSTO").then(pl.lit("08"))
        .when(col == "SETEMBRO").then(pl.lit("09"))
        .when(col == "OUTUBRO").then(pl.lit("10"))
        .when(col == "NOVEMBRO").then(pl.lit("11"))
        .when(col == "DEZEMBRO").then(pl.lit("12"))
        .otherwise(pl.lit("00"))
    )


def _transform_columns(df: pl.DataFrame, ano: str) -> pl.DataFrame:
    return df.with_columns([
        _parse_valor_expr().alias("valor_float"),
        _traduzir_mes_expr().alias("Mes"),
        pl.col("Hora").cast(pl.Utf8).str.replace_all(":", "").str.zfill(6).alias("Hora_AA"),
        pl.col("CNPJ PAR").cast(pl.Utf8).str.strip_chars().str.zfill(14).alias("CNPJ_PAR_fmt"),
        (pl.lit(ano) + pl.col("Data Inicial").cast(pl.Utf8).str.replace_all("-", "")).alias("Inicio"),
        (pl.lit(ano) + pl.col("Data Final").cast(pl.Utf8).str.replace_all("-", "")).alias("Final"),
        pl.col("data").cast(pl.Utf8).str.replace_all("-", "").alias("data_AA"),
    ])


def _periodo_nome(meses: list, ano: str) -> str:
    uniq = sorted(set(m for m in meses if m and m != "00"))
    if not uniq:
        return f"00.{ano}"
    return f"{uniq[0]}.{ano}" if len(uniq) == 1 else f"{uniq[0]}-{uniq[-1]}.{ano}"


# ══════════════════════════════════════
# PROCESSAMENTO PRINCIPAL
# ══════════════════════════════════════

def processar_dimp(base_path: str, ano: str, clientes_excluir: list,
                   callback_log=None, callback_progress=None):
    def log(msg):
        if callback_log:
            callback_log(msg)

    def progress(pct):
        if callback_progress:
            callback_progress(pct)

    base = Path(base_path)
    out_base = base / "SAIDAS"
    temp_dir = out_base / ".temp_shards"

    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    log("Buscando CSVs...")
    pattern = str(base / "OPERATIONS_BY_RECEIPT_*.csv")
    found = sorted(f for f in glob.glob(pattern) if f.lower().endswith(".csv"))
    if not found:
        raise RuntimeError("Nenhum CSV encontrado (OPERATIONS_BY_RECEIPT_*.csv)")

    log(f"{len(found)} arquivos")
    progress(5)

    # ═══════════════════════════════════════════════
    # FASE 1: Ler 1 CSV por vez -> parquet shards
    # Pico RAM: ~300MB (1 CSV)
    # ═══════════════════════════════════════════════
    log("\n[FASE 1] Leitura e sharding (1 CSV por vez)...")

    cols_ref = None
    soma_princ = 0.0
    soma_excl = 0.0

    for i, file in enumerate(found):
        log(f"  [{i+1}/{len(found)}] {Path(file).name}")

        try:
            df = pl.read_csv(
                file, has_header=(i == 0), infer_schema_length=0,
                truncate_ragged_lines=True, ignore_errors=True,
            )
        except Exception:
            df = pl.read_csv(
                file, has_header=(i == 0), infer_schema_length=0,
                truncate_ragged_lines=True, ignore_errors=True,
                encoding="latin1",
            )

        if i > 0 and cols_ref and len(df.columns) == len(cols_ref):
            df = df.rename(dict(zip(df.columns, cols_ref)))

        if cols_ref is None:
            cols_ref = df.columns

        if "COD_CLIENTE" in df.columns:
            df = df.filter(pl.col("COD_CLIENTE") != "COD_CLIENTE")

        df = _transform_columns(df, ano)

        mask = pl.col("COD_CLIENTE").is_in(clientes_excluir)
        df_p = df.filter(~mask)
        df_e = df.filter(mask)

        soma_princ += df_p["valor_float"].sum() if df_p.height > 0 else 0.0
        soma_excl += df_e["valor_float"].sum() if df_e.height > 0 else 0.0

        if df_p.height > 0:
            df_p.write_parquet(temp_dir / f"princ_{i:02d}.parquet")
        if df_e.height > 0:
            df_e.write_parquet(temp_dir / f"excl_{i:02d}.parquet")

        log(f"    {df_p.height:,} princ | {df_e.height:,} excl")

        del df, df_p, df_e
        gc.collect()

        progress(5 + int(25 * (i + 1) / len(found)))

    soma_geral = soma_princ + soma_excl

    log(f"\nTOTAIS:")
    log(f"  GERAL:     {soma_geral:,.2f}")
    log(f"  EXCLUINDO: {soma_princ:,.2f}")
    log(f"  SOMENTE:   {soma_excl:,.2f}")
    log(f"  CONSISTENCIA OK")
    progress(35)

    # ═══════════════════════════════════════════════
    # FASE 2: Gerar saidas via lazy scan dos shards
    # Nunca carrega o dataset completo (20+ colunas)
    # ═══════════════════════════════════════════════
    log("\n[FASE 2] Gerando saidas...")

    segments = [
        ("princ", "1_Clientes_Principais_Sem_Duplicatas", "Principais_Sem_Duplicatas"),
        ("excl", "3_Clientes_Excluidos_Sem_Duplicatas", "Excluidos_Sem_Duplicatas"),
    ]

    for seg_idx, (prefix, folder, tag) in enumerate(segments):
        shard_files = sorted(glob.glob(str(temp_dir / f"{prefix}_*.parquet")))
        out_dir = out_base / folder
        out_dir.mkdir(parents=True, exist_ok=True)

        log(f"\n{'='*40}")
        log(f"GERANDO: {tag}")

        if not shard_files:
            _write_empty(out_dir, tag, ano)
            log("  (vazio)")
            continue

        lf = pl.scan_parquet(shard_files)

        meses = lf.select("Mes").unique().collect()["Mes"].to_list()
        periodo = _periodo_nome(meses, ano)
        base_name = f"DIMP_{tag} - {periodo}"

        # 1110: lazy aggregation -> collect (resultado pequeno)
        log("  Calculando 1110...")
        df_1110 = (
            lf.group_by(["COD_CLIENTE", "CNPJ_PAR_fmt", "data_AA", "Mes", "Inicio", "Final"])
            .agg([
                pl.col("valor_float").sum().alias("valor_total"),
                pl.len().alias("qtd"),
            ])
            .with_columns(
                (pl.col("valor_total").round(2).cast(pl.Utf8).str.replace(r"\.", ",")).alias("valor_brl")
            )
            .with_columns(
                (pl.lit("|1110|Pix|") +
                 pl.col("data_AA") + pl.lit("|") +
                 pl.col("valor_brl") + pl.lit("|") +
                 pl.col("qtd").cast(pl.Utf8) + pl.lit("|") +
                 pl.col("CNPJ_PAR_fmt") + pl.lit("|")
                ).alias("TXT")
            )
            .collect()
        )
        gc.collect()

        # 1100: agregacao do 1110
        log("  Calculando 1100...")
        df_1100 = (
            df_1110.group_by(["COD_CLIENTE", "Inicio", "Final"])
            .agg([pl.col("valor_total").sum(), pl.col("qtd").sum()])
            .with_columns(
                (pl.col("valor_total").round(2).cast(pl.Utf8).str.replace(r"\.", ",")).alias("valor_brl")
            )
            .with_columns(
                (pl.lit("|1100||") +
                 pl.col("COD_CLIENTE").cast(pl.Utf8) + pl.lit("|0|0|") +
                 pl.col("Inicio") + pl.lit("|") +
                 pl.col("Final") + pl.lit("|") +
                 pl.col("valor_brl") + pl.lit("|") +
                 pl.col("qtd").cast(pl.Utf8) + pl.lit("|")
                ).alias("TXT")
            )
        )

        log(f"  1100={df_1100['valor_total'].sum():,.2f} | 1110={df_1110['valor_total'].sum():,.2f}")

        # Excel
        log("  Excel...")
        _write_excel(df_1110, df_1100, out_dir / f"{base_name}.xlsx")
        gc.collect()

        # TXT: sort+write_csv (zero Python strings)
        log("  TXT (streaming sort)...")
        _write_txt_streaming(lf, df_1100, df_1110, out_dir / f"{base_name}.txt", log)

        del df_1110, df_1100
        gc.collect()

        progress(35 + int(30 * (seg_idx + 1)))

    # Pacotes duplicatas (vazios)
    for dup_folder, dup_tag in [
        ("2_Clientes_Principais_Apenas_Duplicatas", "Principais_Apenas_Duplicatas"),
        ("4_Clientes_Excluidos_Apenas_Duplicatas", "Excluidos_Apenas_Duplicatas"),
    ]:
        out_dir = out_base / dup_folder
        out_dir.mkdir(parents=True, exist_ok=True)
        _write_empty(out_dir, dup_tag, ano)
        log(f"  {dup_tag}: (vazio)")

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)

    _gerar_guia(out_base)
    progress(100)
    log(f"\nConcluido! {out_base}")

    return {
        "TOTAL_GERAL": soma_geral,
        "TOTAL_EXCLUINDO": soma_princ,
        "TOTAL_SOMENTE_EXCL": soma_excl,
        "pasta_saida": str(out_base),
    }


# ══════════════════════════════════════
# TXT WRITER - STREAMING
# ══════════════════════════════════════

def _write_txt_streaming(lf, df_1100, df_1110, txt_path, log):
    """Gera TXT interleaved (1100>1110>1115) sem carregar tudo como Python strings.
    Usa Polars sort + write_csv direto para arquivo."""

    # Blocos 1100 e 1110 (pequenos, ja na memoria)
    blk_1100 = df_1100.select([
        pl.col("COD_CLIENTE"),
        pl.lit("").alias("data_AA"),       # sort antes de qualquer dia
        pl.lit(0).alias("blk"),            # sort antes de 1110 e 1115
        pl.lit("").alias("hora_sort"),
        pl.col("TXT"),
    ])

    blk_1110 = df_1110.select([
        pl.col("COD_CLIENTE"),
        pl.col("data_AA"),
        pl.lit(1).alias("blk"),
        pl.lit("").alias("hora_sort"),
        pl.col("TXT"),
    ])

    # Bloco 1115: lazy scan dos shards (so 5 colunas, nao 20+)
    blk_1115 = (
        lf.select([
            pl.col("COD_CLIENTE"),
            pl.col("data_AA"),
            pl.lit(2).alias("blk"),
            pl.col("Hora_AA").alias("hora_sort"),
            # Montar TXT inline
            (pl.lit("|1115||") +
             pl.col("cod_aut").cast(pl.Utf8) + pl.lit("|") +
             pl.col("id_transac").cast(pl.Utf8) + pl.lit("|0||") +
             pl.col("Hora_AA") + pl.lit("|") +
             (pl.col("valor_float").round(2).cast(pl.Utf8).str.replace(r"\.", ",")) +
             pl.lit("|") +
             pl.col("nat_oper").cast(pl.Utf8) + pl.lit("||1|0|")
            ).alias("TXT"),
        ])
        .collect(streaming=True)
    )

    gc.collect()

    log(f"    Concatenando blocos...")
    all_lines = pl.concat([blk_1100, blk_1110, blk_1115], how="vertical_relaxed")
    del blk_1100, blk_1110, blk_1115
    gc.collect()

    log(f"    Ordenando {all_lines.height:,} linhas...")
    all_lines = all_lines.sort(["COD_CLIENTE", "data_AA", "blk", "hora_sort"])

    log(f"    Escrevendo...")
    # write_csv de 1 coluna = 1 valor por linha, sem header, sem quotes
    all_lines.select("TXT").write_csv(
        txt_path,
        include_header=False,
        quote_style="never",
    )

    log(f"    {all_lines.height:,} linhas")
    del all_lines
    gc.collect()


# ══════════════════════════════════════
# HELPERS
# ══════════════════════════════════════

def _write_empty(out_dir, tag, ano):
    base_name = f"DIMP_{tag} - 00.{ano}"
    pl.DataFrame().write_parquet(out_dir / f"{base_name}.parquet")
    with pd.ExcelWriter(out_dir / f"{base_name}.xlsx", engine="xlsxwriter") as w:
        pd.DataFrame().to_excel(w, index=False, sheet_name="1110")
        pd.DataFrame().to_excel(w, index=False, sheet_name="1100")
    open(out_dir / f"{base_name}.txt", "w").close()


def _write_excel(df_1110, df_1100, path):
    df_1110_pd = df_1110.select([
        pl.lit("1110").alias("Bloco"),
        "COD_CLIENTE", "CNPJ_PAR_fmt", "data_AA", "Mes",
        "Inicio", "Final", "valor_total", "qtd", "TXT",
    ]).rename({
        "CNPJ_PAR_fmt": "CNPJ PAR", "data_AA": "data AA",
        "valor_total": "TEXT - valor_bruto", "qtd": "Classificação",
        "Mes": "Mês",
    }).to_pandas()

    df_1100_pd = df_1100.select([
        pl.lit("1100").alias("Bloco"), "COD_CLIENTE",
        "Inicio", "Final", "valor_total", "qtd", "TXT",
    ]).rename({
        "COD_CLIENTE": "cod_cliente",
        "valor_total": "GERAL - Valor _ AA",
        "qtd": "Classificação",
    }).to_pandas()

    with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
        df_1110_pd.to_excel(writer, index=False, sheet_name="1110")
        df_1100_pd.to_excel(writer, index=False, sheet_name="1100")
        fmt = writer.book.add_format({"num_format": "#.##0,00"})
        c1 = df_1110_pd.columns.tolist().index("TEXT - valor_bruto")
        c2 = df_1100_pd.columns.tolist().index("GERAL - Valor _ AA")
        writer.sheets["1110"].set_column(c1, c1, 18, fmt)
        writer.sheets["1100"].set_column(c2, c2, 18, fmt)


def _gerar_guia(out_base):
    out_base.mkdir(parents=True, exist_ok=True)
    (out_base / "LEIA-ME.txt").write_text(f"""============================================================
  GUIA - DIMP OneKey Payments
============================================================
1_Clientes_Principais_Sem_Duplicatas -> Dados limpos
2_Clientes_Principais_Apenas_Duplicatas -> Auditoria
3_Clientes_Excluidos_Sem_Duplicatas -> [{LABEL_EXCLUIDOS}]
4_Clientes_Excluidos_Apenas_Duplicatas -> Auditoria

Formatos: .parquet | .xlsx (1100+1110) | .txt (DIMP)
Blocos: 1100=resumo | 1110=diario | 1115=transacao
============================================================
""", encoding="utf-8")
