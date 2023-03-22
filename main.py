import os
import shutil
import subprocess
from datetime import datetime as dt
import multiprocessing as mul
import os
import stat
from subprocess import call

import pandas as pd
from git import Repo

from data.query_repo import mine_github_repositories_csv

NUM_REPO = 1000

REPOS_FOLDER = 'data/repos/'
METRICS_FOLDER = 'data/ck_metrics/'
OUTPUT_FOLDER = 'output/'

CK_RUNNER = 'data/Runner.jar'
INPUT_FILE = 'data/repositories.csv'
OUTPUT = 'output/analysis.csv'

COLUMNS = ['nameWithOwner', 'url', 'createdAt', 'stargazers',
           'releases', 'loc', 'cbo', 'dit', 'lcom']


def log_print(message):
    nowDatetime = dt.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'{nowDatetime} - {message}')


# Verifica se o repositório já foi analisado comparando pela coluna nameWithOwner
def already_processed(nameWithOwner: str) -> bool:
    if os.path.exists(OUTPUT):
        df = pd.read_csv(OUTPUT)
        return nameWithOwner in df['nameWithOwner'].values
    return False

# Função para mudar as permissões de escrita do arquivo ou diretório especificado pelo caminho path e, em seguida, tenta remove-lo.


def on_rm_error(func, path, exc_info):
    os.chmod(path, stat.S_IWRITE)
    os.unlink(path)


# Função que exclui os dados armazenados do clone do repositório
def delete_cached_repo_data(repo_name: str):
    try:
        if os.path.exists(os.path.join(REPOS_FOLDER, repo_name)):
            with os.scandir(os.path.join(REPOS_FOLDER, repo_name)) as entries:
                for entry in entries:
                    if entry.name.endswith(('git', 'github')):
                        tmp = os.path.join(REPOS_FOLDER, repo_name, entry.name)
                        # Queremos exibir a pasta .git antes de desvinculá-la.
                        with subprocess.Popen(['attrib', '-H', tmp], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
                            stdout, stderr = proc.communicate()
                        # Para caso exista arquivos que não permitem exclusão, como exemplo '.git'
                        shutil.rmtree(tmp, onerror=on_rm_error)
            shutil.rmtree(os.path.join(REPOS_FOLDER, repo_name))

        for file_name in ['class.csv', 'method.csv']:
            file_path = os.path.join(METRICS_FOLDER, repo_name + file_name)
            if os.path.exists(file_path):
                os.remove(file_path)
    except Exception as e:
        log_print(e)
        log_print(f'Error on exclude {repo_name} =/ ')

# Função que executa a ferramenta de qualidade de codigo CK (https://github.com/mauricioaniche/ck)


def run_ck_metrics(nameWithOwner: str, url: str, created_at: str, stargazers: int, releases: int) -> None:
    try:
        repo_name = nameWithOwner.replace('/', '@')
        delete_cached_repo_data(repo_name)

        # Verifica se o repositório ainda não teve sua análise realizada
        if not os.path.exists(f'{OUTPUT_FOLDER}{repo_name}.csv') and not already_processed(nameWithOwner):
            repo_path = REPOS_FOLDER + repo_name
            ck_metrics_path = METRICS_FOLDER + repo_name

            log_print('Cloning {}'.format(nameWithOwner))
            Repo.clone_from(url, repo_path, depth=1, filter='blob:none')

            log_print('Running CK metrics on {}'.format(repo_name))
            subprocess.call(["java", "-jar", CK_RUNNER, repo_path,
                             "true", "0", "False", ck_metrics_path])

            metrics = pd.read_csv(ck_metrics_path + 'class.csv')
            loc = metrics['loc'].sum()
            cbo = metrics['cbo'].median()
            dit = metrics['dit'].max()
            lcom = metrics['lcom'].median()

            df = pd.DataFrame([[nameWithOwner, url, created_at, stargazers,
                                releases, loc, cbo, dit, lcom]], columns=COLUMNS)
            df.to_csv(OUTPUT_FOLDER + repo_name + '.csv', index=False)

            shutil.rmtree(repo_path)
            os.remove(ck_metrics_path + 'class.csv')
            os.remove(ck_metrics_path + 'method.csv')

            return df

    except Exception as e:
        log_print('Error on {}: {}'.format(nameWithOwner, e))
        delete_cached_repo_data(repo_name)


if __name__ == '__main__':
    rp_list = pd.DataFrame()

    # Crie pastas se elas não existirem
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
    if not os.path.exists(REPOS_FOLDER):
        os.makedirs(REPOS_FOLDER)
    if not os.path.exists(METRICS_FOLDER):
        os.makedirs(METRICS_FOLDER)

    # Verifica se o arquivo de entrada existe e se a entrada é válida. Se não, gera-o.
    if os.path.exists(INPUT_FILE):
        rp_list = pd.read_csv(INPUT_FILE)
        log_print('Reading repositories')
    else:
        log_print('Generating new repositories.csv')
        mine_github_repositories_csv(NUM_REPO)
        rp_list = pd.read_csv(INPUT_FILE)
        log_print('Generating repositories.csv')

    # Ordena a lista por estrelas
    rp_list = rp_list.sort_values(by='stargazers', ascending=False)[
        :int(NUM_REPO*1.25)]

    # Declara o número de threads a serem utilizadas
    pool = mul.Pool(int(os.cpu_count())*3)

    # Obtenha o arquivo de entrada e filtre os repositórios já lidos
    rp_list = pd.read_csv(INPUT_FILE)

    # Execute as métricas CK para cada repositório
    rows = list(rp_list.itertuples(name=None, index=False))
    results = pool.starmap(run_ck_metrics, rows)
    results = list(filter(lambda x: x is not None, results))

    # Cria o arquivo de saída para cada repositório analisado na pasta de saída e remove-o
    output = pd.concat(results) if len(
        results) > 0 else pd.DataFrame(columns=COLUMNS)
    if os.path.exists(OUTPUT):
        output = pd.concat([output, pd.read_csv(OUTPUT)])
    for repo in os.listdir(OUTPUT_FOLDER):
        output = pd.concat([output, pd.read_csv(OUTPUT_FOLDER + repo)])
        os.remove(OUTPUT_FOLDER + repo)

    # Verifica se o arquivo de saída não tem duplicatas
    output = output.drop_duplicates()
    output = output.sort_values(by='stargazers', ascending=False)

    # Exporta o arquivo csv
    output.to_csv(OUTPUT, index=False)

    log_print('Done')
