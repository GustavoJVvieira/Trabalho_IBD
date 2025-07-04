import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import duckdb

st.set_page_config(page_title="App SQL básico com CSVs", layout="wide")

st.title("App de consultas SQL básicas em múltiplos CSVs")

st.markdown("""
Carregue múltiplos arquivos CSV e use filtros interativos ou consultas SQL completas.
""")

uploaded_files = st.file_uploader(
    "Upload de arquivos CSV", 
    type=["csv"], 
    accept_multiple_files=True
)

dfs = {}

if uploaded_files:
    # Carrega os dataframes
    for f in uploaded_files:
        try:
            df = pd.read_csv(f, sep=';', encoding='utf-8-sig', on_bad_lines='skip', engine='python')
            tabela_nome = f.name.split(".")[0].replace(" ", "_").upper()  # Nome da tabela padronizado
            dfs[tabela_nome] = df
        except Exception as e:
            st.error(f"Erro ao carregar {f.name}: {e}")

    st.sidebar.header("Tabelas carregadas")
    for nome, df in dfs.items():
        st.sidebar.write(f"{nome}: {df.shape[0]} linhas, {df.shape[1]} colunas")

    tab1, tab2 = st.tabs(["🔧 Consulta Interativa", "📝 Consulta SQL Manual"])

    with tab1:
        # Escolha da tabela principal para consulta
        tabela_principal = st.selectbox("Selecione a tabela para consulta (SELECT)", list(dfs.keys()))

        if tabela_principal:
            df_main = dfs[tabela_principal]

            st.subheader(f"Visualização da tabela principal: {tabela_principal}")
            st.dataframe(df_main.head(20))

            # Escolher colunas para mostrar (projeção)
            colunas_disponiveis = df_main.columns.tolist()
            colunas_selecionadas = st.multiselect("Selecione colunas para mostrar (SELECT)", colunas_disponiveis, default=colunas_disponiveis)

            # Filtragem simples (WHERE)
            st.markdown("### Filtros (WHERE)")
            filtros = []
            for i in range(3):  # até 3 filtros simples
                col_filter = st.selectbox(f"Coluna para filtro {i+1}", ["Nenhum"] + colunas_disponiveis, key=f"filter_col_{i}")
                if col_filter != "Nenhum":
                    op_filter = st.selectbox(f"Operador para filtro {i+1}", ["==", "!=", ">", ">=", "<", "<=", "contains"], key=f"filter_op_{i}")
                    val_filter = st.text_input(f"Valor para filtro {i+1}", key=f"filter_val_{i}")
                    if val_filter != "":
                        filtros.append( (col_filter, op_filter, val_filter) )

            # Aplicar filtros
            df_filtered = df_main.copy()
            for col, op, val in filtros:
                try:
                    if op == "contains":
                        df_filtered = df_filtered[df_filtered[col].astype(str).str.contains(val)]
                    else:
                        try:
                            val_num = float(val)
                            if op == "==":
                                df_filtered = df_filtered[df_filtered[col] == val_num]
                            elif op == "!=":
                                df_filtered = df_filtered[df_filtered[col] != val_num]
                            elif op == ">":
                                df_filtered = df_filtered[df_filtered[col] > val_num]
                            elif op == ">=":
                                df_filtered = df_filtered[df_filtered[col] >= val_num]
                            elif op == "<":
                                df_filtered = df_filtered[df_filtered[col] < val_num]
                            elif op == "<=":
                                df_filtered = df_filtered[df_filtered[col] <= val_num]
                        except:
                            if op == "==":
                                df_filtered = df_filtered[df_filtered[col].astype(str) == val]
                            elif op == "!=":
                                df_filtered = df_filtered[df_filtered[col].astype(str) != val]
                except Exception as e:
                    st.warning(f"Erro ao aplicar filtro {col} {op} {val}: {e}")

            # JOIN
            st.markdown("### Operação JOIN")
            fazer_join = st.checkbox("Fazer join com outra tabela?")
            if fazer_join:
                tabelas_possiveis = [t for t in dfs.keys() if t != tabela_principal]
                if tabelas_possiveis:
                    tabela_join = st.selectbox("Selecione a tabela para JOIN", tabelas_possiveis)
                    df_join = dfs[tabela_join]

                    colunas_comuns = list(set(df_filtered.columns) & set(df_join.columns))
                    if colunas_comuns:
                        coluna_join = st.selectbox("Coluna para JOIN", colunas_comuns)
                        tipo_join = st.selectbox("Tipo de JOIN", ["inner", "left", "right", "outer"])

                        try:
                            df_joined = pd.merge(df_filtered, df_join, on=coluna_join, how=tipo_join)
                        except Exception as e:
                            st.error(f"Erro ao fazer join: {e}")
                            df_joined = df_filtered
                    else:
                        st.warning("Nenhuma coluna em comum para fazer JOIN.")
                        df_joined = df_filtered
                else:
                    st.warning("Nenhuma outra tabela disponível para join.")
                    df_joined = df_filtered
            else:
                df_joined = df_filtered

            # Agrupamento
            st.markdown("### Agrupamento (GROUP BY)")
            colunas_grupo = st.multiselect("Selecione colunas para agrupar (GROUP BY)", df_joined.columns.tolist())
            if colunas_grupo:
                ops = ["sum", "mean", "count", "max", "min"]
                agregacoes = {}
                for col in df_joined.select_dtypes(include=["int64", "float64"]).columns:
                    op = st.selectbox(f"Operação para '{col}'", ops, key=f"agg_{col}")
                    agregacoes[col] = op

                try:
                    df_grouped = df_joined.groupby(colunas_grupo).agg(agregacoes).reset_index()
                except Exception as e:
                    st.error(f"Erro ao fazer agrupamento: {e}")
                    df_grouped = df_joined
            else:
                df_grouped = df_joined

            # Ordenação
            st.markdown("### Ordenação (ORDER BY)")
            col_ordenar = st.selectbox("Selecione coluna para ordenar", df_grouped.columns.tolist())
            ordem = st.radio("Ordem", ("Crescente", "Decrescente"))
            ascending = True if ordem == "Crescente" else False
            df_sorted = df_grouped.sort_values(by=col_ordenar, ascending=ascending)

            # Projeção final
            colunas_final = st.multiselect("Selecione colunas para mostrar (projeção final)", df_sorted.columns.tolist(), default=colunas_selecionadas)

            df_final = df_sorted[colunas_final]

            st.subheader("Resultado da consulta")
            st.dataframe(df_final)

            # Gráfico
            st.markdown("### Visualização gráfica (histograma)")
            num_cols = df_final.select_dtypes(include=["int64", "float64"]).columns.tolist()
            if num_cols:
                col_graf = st.selectbox("Coluna para histograma", num_cols, key="graf_hist")
                fig, ax = plt.subplots()
                sns.histplot(df_final[col_graf].dropna(), kde=True, ax=ax)
                ax.set_xlabel(col_graf)
                ax.set_ylabel("Frequência")
                st.pyplot(fig)
            else:
                st.info("Não há colunas numéricas para gráfico.")

    with tab2:
        st.markdown("### Consulta SQL manual com múltiplas tabelas")

        st.markdown("Você pode usar nomes das tabelas conforme o nome do arquivo CSV (sem extensão, em MAIÚSCULAS).")

        query = st.text_area("Escreva sua consulta SQL abaixo:", height=200)

        if query:
            con = duckdb.connect()
            for nome, df in dfs.items():
                con.register(nome, df)

            try:
                resultado = con.execute(query).df()
                st.success("Consulta executada com sucesso!")
                st.dataframe(resultado)

                # Gráfico SQL
                st.markdown("### Visualização gráfica (histograma)")
                num_cols = resultado.select_dtypes(include=["int64", "float64"]).columns.tolist()
                if num_cols:
                    col_graf = st.selectbox("Coluna para histograma", num_cols, key="graf_hist_sql")
                    fig, ax = plt.subplots()
                    sns.histplot(resultado[col_graf].dropna(), kde=True, ax=ax)
                    ax.set_xlabel(col_graf)
                    ax.set_ylabel("Frequência")
                    st.pyplot(fig)
                else:
                    st.info("Não há colunas numéricas para gráfico.")
            except Exception as e:
                st.error(f"Erro ao executar SQL: {e}")
else:
    st.info("Faça upload de pelo menos um arquivo CSV para começar.")
