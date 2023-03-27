import os
from datetime import datetime as dt
import matplotlib.pyplot as plt
import scipy.stats as stats
import pandas as pd

#Converte o csv em um DataFrame
def load_data(file_path: str, n_rows: int = 1000) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    df = df.dropna().sort_values(by=['stargazers'], ascending=False)[:n_rows]
    return df

# Calcula a idade do repositorio da linha com relação a data atual em anos
def age_calculator(created_at: str) -> float:
    now = dt.now()
    created_at = dt.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
    return (now - created_at).days / 365.25

# Plota gráficos de dispersão e calcula correlações de Spearman para cada combinação de colunas de qualidade e métricas, salvando os gráficos em arquivos na pasta plots
def plot_correlations(df: pd.DataFrame, quality_columns: list, metric_columns: list, output_dir: str, sd_limit: int = 3):
    for quality_column in quality_columns:
        for metric_column in metric_columns:
            fig, ax = plt.subplots()
            x = df[metric_column]
            y = df[quality_column]
            spearman = stats.spearmanr(x, y)
            title = 'Spearman: ' + str(round(spearman[0], 2))

            # Remover outliers usando desvio padrão
            x_mean, x_std = x.mean(), x.std()
            y_mean, y_std = y.mean(), y.std()
            x_min, x_max = x_mean - sd_limit * x_std, x_mean + sd_limit * x_std
            y_min, y_max = y_mean - sd_limit * y_std, y_mean + sd_limit * y_std
            filtered_df = df[(df[metric_column] >= x_min) & (df[metric_column] <= x_max) & (
                df[quality_column] >= y_min) & (df[quality_column] <= y_max)]
            filtered_x = filtered_df[metric_column]
            filtered_y = filtered_df[quality_column]

            ax.scatter(filtered_x, filtered_y, alpha=0.5)
            ax.set(
                xlabel=metric_column,
                ylabel=quality_column,
                title=title,
            )
            plt.savefig(
                f'{output_dir}/{metric_column}_{quality_column}.png', dpi=300, bbox_inches='tight')
            plt.close()


def main():
    file_path = './output/analysis.csv'
    output_dir = './plots'
    df = load_data(file_path)
    df['age'] = df['createdAt'].apply(age_calculator)
    quality_columns = ['cbo', 'dit', 'lcom']
    metric_columns = ['stargazers', 'releases', 'loc', 'age']
    plot_correlations(df, quality_columns, metric_columns, output_dir)
    print('Done')


if __name__ == '__main__':
    main()
