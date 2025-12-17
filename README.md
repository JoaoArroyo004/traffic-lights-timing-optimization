# Sistema de Otimização Semafórica Baseada em Algoritmos Genéticos Multiobjetivo

## Instalação de dependências
Primeiro, certifique-se de ter instalada uma versão do python pelo menos 3.11.

Como gerenciador de dependências, é usado o Poetry, que pode ser instalado pelo comando abaixo. Os arquivos de configuração foram feitos para a versão 2.2.1
```shell
pipx install poetry==2.2.1
poetry --version
```

Em seguida, configure para que o ambiente virtual correspondente a este projeto seja gerado no ***root*** do projeto.
```shell
poetry config --local virtualenvs.in-project true
```

Então, gere o ambiente virtual:
```shell
poetry install
```

Para ativar o ambiente virtual:
```shell
source .venv/bin/activate
```

## Execução do projeto diretamente do terminal
Para melhor performance da otimização, recomenda-se que o usuário execute neste modo, dedicando todos
os núcleos de sua máquina para esta tarefa.

Para efetuar a otimização, o usuário deve executar o arquivo ***experiment_runner.py***. Adicione o path do arquivo caso
não esteja na pasta correspondente.
```shell
poetry run python -m experiment_runner
```

Neste arquivo, o usuário pode configurar os principais parâmetros.
- Quantidade de indivíduos por geração
- Quantidade de gerações até a parada da execução
- Path para o arquivo de configuração do simulador SUMO
- Tempo de ciclo dos semáforos
- Quantidade de processos a ser usada no paralelismo (recomenda-se usar a quantidade de ***cores***)

### Resultados
- A semente usada para gerar a população inicial é salva em ***seed.txt***
- O tempo requerido para processar cada geração é salvo em ***gen.txt***
- A fronteira de Pareto com as soluções não dominadas é salva como ***pareto_front.png***
- Na pasta log_parallel, tem-se os arquivos ***worker.csv***, com o histórico completo da otimização.

## Utilizando front-end e back-end

Primeiramente, importe o repositório do front-end com:
```
git clone https://github.com/ArthurMilani/Frontend-tcc.git
```
Em seguida, altere para a branch master e vá ao diretório do projeto, execute para baixar as dependências:
```
npm install
```
Para executar em ambiente de desenvolvimento, use:
```
npm run dev
```
Para executar em produção, execute:
```
npm build
```
E em seguida:
```
npm start
```
Desta forma, o front-end já estará disponível para acesso em:
```
http://localhost:3000/simulacoes
```

Para iniciar o backend do projeto, altere para a branch api_2 deste repositório.
Instale as dependências do projeto com poetry:
```
poetry install 
```
Em seguida, vá ao diretório traffic-lights-timing-optimization/api e rode o comando:
```
poetry run endpoints:app --host 0.0.0.0 --port 8000
```
Desta forma, com front-end e back-end em execução, é possível executar as funcionalidades do sistema via interface web, basta acessar:
```
http://localhost:3000/simulacoes
```