import face_recognition as reconhecedor
import colored
import secrets
import random
import simpy
import json

FOTOS_PESSOAS = [
    "faces/alunos1.jpg",
    "faces/alunos2.jpg",
    "faces/alunos3.jpg",
    "faces/alunos4.jpg"
]
ARQUIVO_DE_CONFIGURACAO = "configuracao.json"

TOTAL_DE_LEITOS_DE_UTI = 10

PROBABILIDADE_DE_LIBERACAO = 30

TEMPO_MEDIO_DE_PERMANENCIA = 60

TEMPO_DE_DETECCAO_DE_ALUNOS = 40
TEMPO_DE_DETECCAO_DE_CADASTRO_PAAE = 20
TEMPO_DE_LIBERACAO_DE_ALUNOS = 60
TEMPO_DE_DETECCAO_DE_PESSOAS_NAO_CADASTRADAS = 25


# ler configuracoes e preparar estruturas de dados


def preparar():
    global configuracao

    configuracao = None
    try:
        with open(ARQUIVO_DE_CONFIGURACAO, "r") as arquivo:
            configuracao = json.load(arquivo)
            if configuracao:
                print("arquivo de configuracao carregado")
            arquivo.close()
    except Exception as e:
        print(f"erro lendo configuração: {str(e)}")

    global alunos_reconhecidos
    alunos_reconhecidos = {}
    


def simular_entradas():
    foto = random.choice(FOTOS_PESSOAS)
    print(f"foto de pessoas: {foto}")

    pessoas = {
        "foto": foto,
        "pacientes": None
    }

    return pessoas


def aluno_reconhecido_previamente(aluno):
    global alunos_reconhecidos

    reconhecido_previamente = False
    for reconhecido in alunos_reconhecidos.values():
        if aluno["matricula"] == reconhecido["matricula"]:
            reconhecido_previamente = True

            break

    return reconhecido_previamente


def reconhecer_alunos(pessoas):
    global configuracao

    print("realizando reconhecimento de alunos...")
    foto_pessoas = reconhecedor.load_image_file(pessoas["foto"])
    caracteristicas_dos_pessoas = reconhecedor.face_encodings(
        foto_pessoas)

    alunos_cadastrados = []
    for aluno in configuracao["alunos_cadastrados"]:
        if not aluno_reconhecido_previamente(aluno):
            fotos = aluno["fotos"]
            total_de_reconhecimentos = 0

            for foto in fotos:
                foto = reconhecedor.load_image_file(foto)
                caracteristicas = reconhecedor.face_encodings(foto)[0]

                reconhecimentos = reconhecedor.compare_faces(
                    caracteristicas_dos_pessoas, caracteristicas)
                if True in reconhecimentos:
                    total_de_reconhecimentos += 1

            if total_de_reconhecimentos/len(fotos) >= 0.6:
                alunos_cadastrados.append(aluno)
        else:
            print("aluno reconhecido previamente")

    return (len(alunos_cadastrados) > 0), alunos_cadastrados


def imprimir_dados_do_aluno(aluno):
    print(colored.fg('black'), colored.bg(
        'yellow'), f"aluno reconhecido em {ambiente_de_simulacao.now}", colored.attr('reset'))
    print(colored.fg('black'), colored.bg(
        'yellow'), f"nome: {aluno['nome']}", colored.attr('reset'))
    print(colored.fg('black'), colored.bg(
        'yellow'), f"idade: {aluno['idade']}", colored.attr('reset'))
    print(colored.fg('black'), colored.bg(
        'yellow'), f"endereço: {aluno['endereco']}", colored.attr('reset'))
    print(colored.fg('black'), colored.bg(
        'yellow'), f"matricula: {aluno['matricula']}", colored.attr('reset'))
    print(colored.fg('black'), colored.bg(
        'yellow'), f"turma: {aluno['turma']}", colored.attr('reset'))


# captura uma foto de pessoas e reconhece se tem pacientes
# entre eles


def reconhecer_pessoas(ambiente_de_simulacao):
    global alunos_reconhecidos

    while True:
        print(
            f"tentando reconhecer um aluno entre pessoas em {ambiente_de_simulacao.now}")

        pessoas = simular_entradas()
        ocorreram_reconhecimentos, alunos_cadastrados = reconhecer_alunos(pessoas)
        if ocorreram_reconhecimentos:
            for aluno in alunos_cadastrados:
                aluno["tempo_para_liberacao"] = ambiente_de_simulacao.now + \
                    TEMPO_MEDIO_DE_PERMANENCIA
                aluno["bolsa_paae_verificada"] = False

                id_reconhecimento = secrets.token_hex(nbytes=16).upper()
                alunos_reconhecidos[id_reconhecimento] = aluno

                imprimir_dados_do_aluno(aluno)

        yield ambiente_de_simulacao.timeout(TEMPO_DE_DETECCAO_DE_ALUNOS)


def identificar_cadastro_paae(ambiente_de_simulacao):
    global alunos_reconhecidos

    while True:
        print(f"Tentando identificar cadastro no paae em {ambiente_de_simulacao.now}")

        if len(alunos_reconhecidos):
            for id_reconhecimento, aluno in list(alunos_reconhecidos.items()):
                if not aluno.get("bolsa_paae_verificada", False):
                    possui_bolsa_paae = aluno.get("bolsa_paae", "Não")
                    if possui_bolsa_paae == "Sim":
                        alunos_reconhecidos[id_reconhecimento]["bolsa_paae_verificada"] = True
                        print(colored.fg('white'), colored.bg(
                            'dark_blue'), f"Aluno {aluno['nome']} possui cadastro no PAAE em {ambiente_de_simulacao.now}", colored.attr('reset'))

        yield ambiente_de_simulacao.timeout(TEMPO_DE_DETECCAO_DE_CADASTRO_PAAE)
        


def liberar_alunos(ambiente_de_simulacao):
    global alunos_reconhecidos
    
    while True:
        print(f"Tentando liberar entrada de alunos em {ambiente_de_simulacao.now}")
        if len(alunos_reconhecidos):
            for id_reconhecimento, aluno in list(alunos_reconhecidos.items()):
                if aluno["bolsa_paae_verificada"] and ambiente_de_simulacao.now >= aluno["tempo_para_liberacao"]:
                    aluno_liberado = (random.randint(1, 100)) <= PROBABILIDADE_DE_LIBERACAO
                    if aluno_liberado:
                        alunos_reconhecidos.pop(id_reconhecimento)
                        print(colored.fg('white'), colored.bg('green'), f"liberando entrada de {aluno['nome']} em {ambiente_de_simulacao.now}", colored.attr('reset'))
                        print(mostrar_prato_do_dia())
        
        yield ambiente_de_simulacao.timeout(TEMPO_DE_LIBERACAO_DE_ALUNOS)
                    
def mostrar_prato_do_dia():
    global configuracao

    if configuracao and "prato_dia" in configuracao:
        prato_dia = configuracao["prato_dia"]
        if isinstance(prato_dia, list) and len(prato_dia) > 0:
            print(colored.fg('white'), colored.bg('light_magenta'), f"Prato do dia: {prato_dia[0]['nome']}", colored.attr('reset'))
        else:
            print("Nenhum prato do dia encontrado.")
    else:
        print("Nenhum prato do dia encontrado.")
        
def simular_alerta_pessoas_nao_cadastradas(ambiente_de_simulacao):
    global pessoas_nao_cadastradas
    global alunos_cadastrados

    while True:
        print(f"Tentando alertar pessoas não cadastradas em {ambiente_de_simulacao.now}")

        if len(configuracao["pessoas_nao_cadastradas"]) > 0:
            for pessoa in configuracao["pessoas_nao_cadastradas"]:
                matricula_pessoa = pessoa.get("matricula")
                if matricula_pessoa not in [aluno["matricula"] for aluno in configuracao["alunos_cadastrados"]]:
                    print(colored.fg('white'), colored.bg('red'), f"Alerta: Pessoa não cadastrada identificada em {ambiente_de_simulacao.now}", colored.attr('reset'))
                    print(colored.fg('black'), colored.bg('red'), f"Nome: {pessoa['nome']}", colored.attr('reset'))

        yield ambiente_de_simulacao.timeout(TEMPO_DE_DETECCAO_DE_PESSOAS_NAO_CADASTRADAS)

if __name__ == '__main__':
    preparar()
    ambiente_de_simulacao = simpy.Environment()
    ambiente_de_simulacao.process(reconhecer_pessoas(ambiente_de_simulacao))
    ambiente_de_simulacao.process(identificar_cadastro_paae(ambiente_de_simulacao))
    ambiente_de_simulacao.process(simular_alerta_pessoas_nao_cadastradas(ambiente_de_simulacao))
    ambiente_de_simulacao.process(liberar_alunos(ambiente_de_simulacao))
    ambiente_de_simulacao.run(until=1000)

