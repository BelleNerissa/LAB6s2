from os import environ
import os
from dotenv import load_dotenv
import requests

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

MAX_QUERY_ATTEMPTS = 10
AFTER_PREFIX = ', after: {cursor}'
OUTPUT = 'data/repositories.csv'

QUERY = """
    {
      search(query: "language:java,stars:>100 sort:stars created:{interval}", type: REPOSITORY, first: 25 {after}) {
        pageInfo {
          hasNextPage
          endCursor
        }
        nodes {
          ... on Repository {
            nameWithOwner
            url
            createdAt
            stargazers {
              totalCount
            }
            releases {
              totalCount
            }
            primaryLanguage {
              name
            }
          }
        }
      }
    }
    """

# Exporta a lista de repositórios em um arquivo CSV..


def export_csv(repos: list) -> str:
    with open(OUTPUT, 'w') as f:
        f.write('nameWithOwner,url,createdAt,stargazers,releases\n')
        for repo in repos:
            f.write(
                f"{repo['nameWithOwner']},{repo['url']},{repo['createdAt']},{repo['stargazers']['totalCount']},{repo['releases']['totalCount']}\n")
    return OUTPUT

 # Executa uma query na API GraphQL do GitHub e retorna o resultado.

# Executa uma query na API GraphQL do GitHub e retorna o resultado.


def run_graphql_query(query: str, token: str, attemp=1) -> dict:

    url = 'https://api.github.com/graphql'
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.post(url, json={'query': query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 502 and attemp <= MAX_QUERY_ATTEMPTS:
        print(
            f'Attempt {attemp}/{MAX_QUERY_ATTEMPTS} got Error 502. Retrying...')
        return run_graphql_query(query, token, attemp + 1)
    elif response.status_code == 502 and attemp > MAX_QUERY_ATTEMPTS:
        print('Error 502. Maximum number of attempts reached.')
        exit(1)
    else:
        raise Exception(
            f"Query failed to run by returning code of {response.status_code}. {query}")


# Retorna uma lista dos repositórios mais populares no GitHub e suas características.
def get_repos(token: str, interval: str, after: str) -> list:
    query = QUERY.replace('{after}', after)
    query = query.replace('{interval}', interval)
    result = run_graphql_query(query, token)

    if 'data' in result:
        return result['data']
    else:
        print(result)
        raise Exception(
            f"Error getting repositories. Message: {result['message']}. \n {query}")


# Gera o csv dos repositorios minerados
def mine_github_repositories_csv(results: int, token: str = None) -> str:
    if token is None:
        # Usa as variáveis de ambiente definidas no arquivo .env
        token = os.environ.get('GITHUB_TOKEN')
        if token is None:
            raise Exception(
                "Você precisa definir a variável de ambiente GITHUB_TOKEN de tipo clássico")

    after = ''
    interval = '2008..2015'
    repositories = []

    while len(repositories) < results:
        response = get_repos(token, interval, after)
        nodes = response.get('search', {}).get('nodes', [])
        repositories.extend(nodes)

        if response.get('search', {}).get('pageInfo', {}).get('hasNextPage'):
            cursor = response['search']['pageInfo']['endCursor']
            after = AFTER_PREFIX.format(cursor=f'"{cursor}"')
        elif len(repositories) <= results:
            after = ''
            interval = '2016..2023'
        else:
            break

    return export_csv(repositories)


if __name__ == '__main__':
    import argparse
    # Criar objeto ArgumentParser
    parser = argparse.ArgumentParser(
        description='Consulte a API GitHub GraphQL para obter os repositórios mais populares.')

    # Adicionar argumentos
    parser.add_argument('--token', '-t', help='GitHub access token')
    parser.add_argument(
        '--results', '-r', help='Number of results to return', type=int, default=100)

    # Fazer o parse dos argumentos da linha de comando
    args = parser.parse_args()

    # Chamar a função com os argumentos obtidos
    mine_github_repositories_csv(args.results, args.token)
