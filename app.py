import os
import requests
from flask import Flask, jsonify, request
from datetime import datetime
import json # Importe o módulo json

# URL da API da prefeitura
RIO_API_URL = "https://dados.mobilidade.rio/gps/sppo"

app = Flask(__name__)

def process_bus_data(raw_data_list):
    """
    Processa a lista de dicionários de ônibus brutos.
    Aplica filtros, conversões e cálculos.
    """
    processed_list = []
    if not isinstance(raw_data_list, list):
        print(f"Erro: Esperava uma lista, mas recebeu {type(raw_data_list)}")
        return [] # Retorna lista vazia se a entrada não for uma lista

    for bus in raw_data_list:
        try:
            # 1. (Tarefa 1.e) FILTRAR: Reter apenas ônibus com velocidade > 0
            velocidade_str = bus.get('velocidade', '0')
            velocidade = int(velocidade_str) if velocidade_str.isdigit() else 0
            if velocidade <= 0:
                continue # Pula para o próximo ônibus

            # 2. (Tarefa 1.b) PADRONIZAR COORDENADAS GPS
            lat_str = str(bus.get('latitude', '0')).replace(',', '.')
            lon_str = str(bus.get('longitude', '0')).replace(',', '.')
            latitude = float(lat_str)
            longitude = float(lon_str)

            # 3. (Tarefa 1.c) CONVERTER CAMPO datahora (Timestamp em milissegundos)
            datahora_ms_str = bus.get('datahora', '0')
            datahora_ms = int(datahora_ms_str) if datahora_ms_str.isdigit() else 0
            formatted_timestamp = None
            date_object = None
            if datahora_ms > 0:
                # Divide por 1000 para converter ms para segundos para datetime.fromtimestamp
                date_object = datetime.fromtimestamp(datahora_ms / 1000)
                formatted_timestamp = date_object.strftime('%Y-%m-%d %H:%M:%S')
            else:
                print(f"Timestamp 'datahora' inválido ou zero para o ônibus {bus.get('ordem')}. Pulando.")
                continue # Pula se não tiver timestamp válido

            # 4. (Tarefa 1.d) CALCULAR TEMPO entre datahora e datahoraservidor
            datahoraservidor_ms_str = bus.get('datahoraservidor', '0')
            datahoraservidor_ms = int(datahoraservidor_ms_str) if datahoraservidor_ms_str.isdigit() else 0
            transmission_delay_seconds = None
            if datahoraservidor_ms > 0 and datahora_ms > 0:
                transmission_delay_seconds = (datahoraservidor_ms - datahora_ms) / 1000
            else:
                 print(f"Timestamp 'datahoraservidor' inválido para {bus.get('ordem')}. Não foi possível calcular o atraso.")


            # 5. Montar o objeto de saída processado
            processed_bus = {
                "ordem": bus.get('ordem'),
                "linha": bus.get('linha'),
                "latitude": latitude,
                "longitude": longitude,
                "velocidade": velocidade,
                "datahora_captura": formatted_timestamp,
                "atraso_transmissao_segundos": transmission_delay_seconds,
                # Adicione outros campos originais se desejar, ex:
                # "datahora_envio_ms": bus.get('datahoraenvio'),
                # "datahora_servidor_ms": datahoraservidor_ms
            }
            processed_list.append(processed_bus)

        except (ValueError, TypeError, KeyError) as e:
            # Captura erros durante a conversão ou acesso a chaves
            print(f"Erro ao processar ônibus {bus.get('ordem', 'Desconhecida')}: {e}. Pulando registro.")
            continue # Pula o registro com erro

    return processed_list

@app.route('/')
def health_check():
    """ Endpoint básico para verificar se a API está no ar. """
    return jsonify({"status": "ok", "message": "API de processamento de ônibus do Rio está funcionando."})

@app.route('/processed_data')
def get_processed_data():
    """
    Endpoint principal que busca os dados da prefeitura,
    processa e retorna apenas os dados filtrados e tratados.
    """
    try:
        print("Recebida requisição para /processed_data. Buscando dados da API do Rio...")
        response = requests.get(RIO_API_URL, timeout=30) # Timeout de 30 segundos
        response.raise_for_status() # Levanta um erro para status HTTP 4xx ou 5xx

        print("Dados recebidos da API do Rio. Status:", response.status_code)
        outer_data = response.json() # A API externa retorna um JSON

        # O dado útil está numa string JSON dentro da chave 'data'
        if 'data' in outer_data and isinstance(outer_data['data'], str):
            print("Encontrada chave 'data' como string. Fazendo parse do JSON interno...")
            try:
                # Faça o parse da string JSON interna para obter a lista de ônibus
                raw_bus_list = json.loads(outer_data['data'])
                print(f"Parse do JSON interno bem-sucedido. {len(raw_bus_list)} registros brutos encontrados.")
            except json.JSONDecodeError as json_err:
                print(f"Erro ao fazer parse do JSON interno: {json_err}")
                return jsonify({"error": "Falha ao fazer parse dos dados internos da API do Rio", "details": str(json_err)}), 500
        else:
             print("Erro: Formato inesperado recebido da API do Rio. Chave 'data' não encontrada ou não é string.")
             return jsonify({"error": "Formato inesperado recebido da API do Rio"}), 500

        # Processa a lista de ônibus
        print("Iniciando processamento dos dados dos ônibus...")
        processed_data = process_bus_data(raw_bus_list)
        print(f"Processamento concluído. {len(processed_data)} ônibus retidos após filtro e processamento.")

        # Retorna os dados processados como JSON
        return jsonify(processed_data)

    except requests.exceptions.Timeout:
        print("Erro: Timeout ao conectar com a API do Rio.")
        return jsonify({"error": "Timeout ao buscar dados da API da prefeitura"}), 504 # Gateway Timeout
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição ao buscar dados da API do Rio: {e}")
        return jsonify({"error": "Erro ao buscar dados da API da prefeitura", "details": str(e)}), 502 # Bad Gateway
    except Exception as e:
        # Captura qualquer outro erro inesperado durante o processo
        print(f"Erro inesperado no servidor: {e}")
        return jsonify({"error": "Erro interno do servidor de processamento", "details": str(e)}), 500


if __name__ == '__main__':
    # Render define a porta através da variável de ambiente PORT
    port = int(os.environ.get('PORT', 5000))
    # Para desenvolvimento local, roda em http://localhost:5000
    # Para produção no Render, o Gunicorn usará isso
    app.run(host='0.0.0.0', port=port, debug=False) # debug=False é importante para produção
