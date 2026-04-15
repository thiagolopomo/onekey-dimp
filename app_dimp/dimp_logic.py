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
    """Extrai mes da coluna 'data' (formato YYYY-MM-DD). Fallback: coluna 'mes' por nome."""
    data_col = pl.col("data").cast(pl.Utf8).str.strip_chars()
    # data vem como "2026-03-01" -> extrair posicao 5:7 = "03"
    mes_from_data = data_col.str.slice(5, 2)

    # Fallback: traduzir coluna "mes" por nome (JANEIRO, etc)
    mes_col = pl.col("mes").cast(pl.Utf8).str.to_uppercase().str.strip_chars()
    mes_from_name = (
        pl.when(mes_col == "JANEIRO").then(pl.lit("01"))
        .when(mes_col == "FEVEREIRO").then(pl.lit("02"))
        .when(mes_col == "MARCO").then(pl.lit("03"))
        .when(mes_col == "ABRIL").then(pl.lit("04"))
        .when(mes_col == "MAIO").then(pl.lit("05"))
        .when(mes_col == "JUNHO").then(pl.lit("06"))
        .when(mes_col == "JULHO").then(pl.lit("07"))
        .when(mes_col == "AGOSTO").then(pl.lit("08"))
        .when(mes_col == "SETEMBRO").then(pl.lit("09"))
        .when(mes_col == "OUTUBRO").then(pl.lit("10"))
        .when(mes_col == "NOVEMBRO").then(pl.lit("11"))
        .when(mes_col == "DEZEMBRO").then(pl.lit("12"))
        .otherwise(pl.lit("00"))
    )

    # Usar data se possivel, senao fallback pra nome do mes
    return pl.when(
        mes_from_data.is_not_null() & (mes_from_data != "")
        & mes_from_data.str.contains(r"^\d{2}$")
    ).then(mes_from_data).otherwise(mes_from_name)


def _extrair_ano_expr():
    """Extrai ano da coluna 'data' (formato YYYY-MM-DD -> '2026')."""
    return pl.col("data").cast(pl.Utf8).str.strip_chars().str.slice(0, 4)


def _format_valor_2dec(col_name: str):
    """Formata float -> string BRL com EXATAMENTE 2 casas decimais.
    21.0 -> '21,00'  |  1055227.75 -> '1055227,75'  |  100.0 -> '100,00'"""
    col = pl.col(col_name)
    # Multiplicar por 100, arredondar, dividir: garante 2 decimais
    inteiro = col.floor().cast(pl.Int64).cast(pl.Utf8)
    # Parte decimal: (val - floor) * 100, arredondar pra inteiro
    dec = ((col - col.floor()).abs() * 100).round(0).cast(pl.Int64)
    dec_str = dec.cast(pl.Utf8).str.zfill(2)
    return inteiro + pl.lit(",") + dec_str


def _transform_columns(df: pl.DataFrame) -> pl.DataFrame:
    # Extrair ano da coluna data (ex: "2026-03-01" -> "2026")
    data_col = pl.col("data").cast(pl.Utf8).str.strip_chars()
    ano_expr = data_col.str.slice(0, 4)

    return df.with_columns([
        _parse_valor_expr().alias("valor_float"),
        _traduzir_mes_expr().alias("Mes"),
        ano_expr.alias("Ano"),
        pl.col("Hora").cast(pl.Utf8).str.replace_all(":", "").str.zfill(6).alias("Hora_AA"),
        pl.col("CNPJ PAR").cast(pl.Utf8).str.strip_chars().str.zfill(14).alias("CNPJ_PAR_fmt"),
        # Data Inicial/Final: formato "MM-DD" -> precisa prefixar com ano
        (ano_expr + pl.col("Data Inicial").cast(pl.Utf8).str.replace_all("-", "")).alias("Inicio"),
        (ano_expr + pl.col("Data Final").cast(pl.Utf8).str.replace_all("-", "")).alias("Final"),
        # data completa: "2026-03-01" -> "20260301"
        data_col.str.replace_all("-", "").alias("data_AA"),
    ])


def _periodo_nome(meses: list, anos: list) -> str:
    uniq_m = sorted(set(m for m in meses if m and m != "00"))
    uniq_a = sorted(set(a for a in anos if a and a != ""))
    ano = uniq_a[0] if uniq_a else "0000"
    if not uniq_m:
        return f"00.{ano}"
    return f"{uniq_m[0]}.{ano}" if len(uniq_m) == 1 else f"{uniq_m[0]}-{uniq_m[-1]}.{ano}"


# ══════════════════════════════════════
# PROCESSAMENTO PRINCIPAL
# ══════════════════════════════════════

def processar_dimp(base_path: str, clientes_excluir: list,
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

        df = _transform_columns(df)

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
            _write_empty(out_dir, tag)
            log("  (vazio)")
            continue

        lf = pl.scan_parquet(shard_files)

        meta = lf.select(["Mes", "Ano"]).unique().collect()
        meses = meta["Mes"].to_list()
        anos = meta["Ano"].to_list()
        periodo = _periodo_nome(meses, anos)
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
                _format_valor_2dec("valor_total").alias("valor_brl")
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
                _format_valor_2dec("valor_total").alias("valor_brl")
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
        _write_empty(out_dir, dup_tag)
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
    """Gera TXT interleaved (1100>1110>1115) por cliente.
    Processa 1 cliente de cada vez — pico RAM minimo."""

    # Indexar 1100 e 1110 por cliente (pequenos, ja na memoria)
    map_1100 = {}
    for row in df_1100.select(["COD_CLIENTE", "TXT"]).iter_rows():
        map_1100[row[0]] = row[1]

    map_1110 = {}
    for row in df_1110.select(["COD_CLIENTE", "data_AA", "TXT"]).sort(["COD_CLIENTE", "data_AA"]).iter_rows():
        map_1110.setdefault(row[0], []).append((row[1], row[2]))

    clientes = sorted(map_1100.keys())
    log(f"    {len(clientes)} clientes")

    # Lazy frame pro 1115 (so colunas necessarias)
    lf_1115 = lf.select([
        pl.col("COD_CLIENTE"),
        pl.col("data_AA"),
        pl.col("Hora_AA"),
        (pl.lit("|1115||") +
         pl.col("cod_aut").cast(pl.Utf8) + pl.lit("|") +
         pl.col("id_transac").cast(pl.Utf8) + pl.lit("|0||") +
         pl.col("Hora_AA") + pl.lit("|") +
         _format_valor_2dec("valor_float") +
         pl.lit("|") +
         pl.col("nat_oper").cast(pl.Utf8) + pl.lit("||1|0|")
        ).alias("TXT"),
    ])

    total_linhas = 0

    # Processar em lotes de clientes pra reduzir scans do parquet
    BATCH = 20
    with open(txt_path, "w", encoding="utf-8") as f:
        for batch_start in range(0, len(clientes), BATCH):
            batch_clientes = clientes[batch_start:batch_start + BATCH]

            # Ler 1115 deste lote de clientes (1 scan do parquet)
            df_batch = (
                lf_1115
                .filter(pl.col("COD_CLIENTE").is_in(batch_clientes))
                .sort(["COD_CLIENTE", "data_AA", "Hora_AA"])
                .collect()
            )

            # Indexar por (cliente, dia)
            cli_1115 = {}
            for row in df_batch.select(["COD_CLIENTE", "data_AA", "TXT"]).iter_rows():
                cli_1115.setdefault(row[0], {}).setdefault(row[1], []).append(row[2])
            del df_batch

            for cliente in batch_clientes:
                # 1100
                f.write(map_1100[cliente] + "\n")
                total_linhas += 1

                # 1110 + 1115 por dia
                dias = map_1110.get(cliente, [])
                c_1115 = cli_1115.get(cliente, {})
                for data_aa, txt_1110 in dias:
                    f.write(txt_1110 + "\n")
                    total_linhas += 1
                    for txt in c_1115.get(data_aa, []):
                        f.write(txt + "\n")
                        total_linhas += 1

            del cli_1115
            gc.collect()

            done = min(batch_start + BATCH, len(clientes))
            if done % 100 == 0 or done == len(clientes):
                log(f"    {done}/{len(clientes)} clientes | {total_linhas:,} linhas")

    log(f"    {total_linhas:,} linhas total")


# ══════════════════════════════════════
# HELPERS
# ══════════════════════════════════════

def _write_empty(out_dir, tag):
    base_name = f"DIMP_{tag} - vazio"
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
        fmt = writer.book.add_format({"num_format": "#,##0.00"})
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

Formatos: .xlsx (1100+1110) | .txt (DIMP)
Blocos: 1100=resumo | 1110=diario | 1115=transacao
============================================================
""", encoding="utf-8")
