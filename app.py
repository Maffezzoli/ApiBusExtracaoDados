import os
import requests
from flask import Flask, jsonify, request # Adicionado request
from datetime import datetime
import json

RIO_API_URL = "https://dados.mobilidade.rio/gps/sppo"
app = Flask(__name__)

# --- Função process_bus_data (COLE A VERSÃO COMPLETA E CORRIGIDA DA FUNÇÃO AQUI) ---
# Certifique-se que a função process_bus_data esteja definida corretamente como antes.
# É importante que ela funcione bem com a lista de dicionários de ônibus.
def process_bus_data(raw_data_list):
    """
    Processa a lista de dicionários de ônibus brutos.
    Aplica filtros, conversões e cálculos.
    """
    processed_list = []
    if not isinstance(raw_data_list, list):
        print(f"Erro interno: process_bus_data esperava uma lista, mas recebeu {type(raw_data_list)}")
        return [] # Retorna lista vazia se a entrada não for uma lista

    for bus in raw_data_list:
        try:
            # 1. FILTRAR: Velocidade > 0
            velocidade_str = bus.get('velocidade', '0')
            velocidade = int(velocidade_str) if velocidade_str.isdigit() else 0
            if velocidade <= 0:
                continue

            # 2. PADRONIZAR COORDENADAS GPS
            lat_str = str(bus.get('latitude', '0')).replace(',', '.')
            lon_str = str(bus.get('longitude', '0')).replace(',', '.')
            latitude = float(lat_str)
            longitude = float(lon_str)

            # 3. CONVERTER datahora (Timestamp ms)
            datahora_ms_str = bus.get('datahora', '0')
            datahora_ms = int(datahora_ms_str) if datahora_ms_str.isdigit() else 0
            formatted_timestamp = None
            date_object = None
            if datahora_ms > 0:
                date_object = datetime.fromtimestamp(datahora_ms / 1000)
                formatted_timestamp = date_object.strftime('%Y-%m-%d %H:%M:%S')
            else:
                continue # Pula se timestamp inválido

            # 4. CALCULAR atraso transmissão
            datahoraservidor_ms_str = bus.get('datahoraservidor', '0')
            datahoraservidor_ms = int(datahoraservidor_ms_str) if datahoraservidor_ms_str.isdigit() else 0
            transmission_delay_seconds = None
            if datahoraservidor_ms > 0 and datahora_ms > 0:
                transmission_delay_seconds = (datahoraservidor_ms - datahora_ms) / 1000

            # 5. Montar o objeto de saída processado
            processed_bus = {
                "ordem": bus.get('ordem'),
                "linha": bus.get('linha'),
                "latitude": latitude,
                "longitude": longitude,
                "velocidade": velocidade,
                "datahora_captura": formatted_timestamp,
                "atraso_transmissao_segundos": transmission_delay_seconds,
            }
            processed_list.append(processed_bus)

        except (ValueError, TypeError, KeyError) as e:
            print(f"Erro ao processar ônibus {bus.get('ordem', 'Desconhecida')}: {e}. Pulando registro.")
            continue
    return processed_list
# --- Fim da função process_bus_data ---


@app.route('/')
def health_check():
    """ Endpoint básico para verificar se a API está no ar. """
    return jsonify({"status": "ok", "message": "API de processamento de ônibus do Rio está funcionando."})

@app.route('/processed_data')
def get_processed_data():
    """
    Endpoint principal que busca os dados da prefeitura,
    processa, aplica limite opcional e retorna os dados tratados.
    Adicione ?limit=N à URL para limitar o número de resultados.
    """
    # Pega o parâmetro 'limit' da URL (?limit=50)
    limit_str = request.args.get('limit', default=None) # Pega como string
    limit = None
    if limit_str and limit_str.isdigit():
        limit = int(limit_str)
        print(f"Limite de {limit} registros solicitado.")
    elif limit_str:
        print(f"Valor de 'limit' inválido recebido: {limit_str}. Ignorando.")


    try:
        print("Recebida requisição para /processed_data. Buscando dados da API do Rio...")
        response = requests.get(RIO_API_URL, timeout=30)
        response.raise_for_status()
        print("Dados recebidos da API do Rio. Status:", response.status_code)

        # Tenta obter o JSON
        outer_data = response.json()
        print(f"DEBUG: Resposta JSON recebida da API do Rio: {str(outer_data)[:1000]}...") # Log limitado

        raw_bus_list = None # Inicializa como None

        # --- Tenta extrair a lista de ônibus ---
        if isinstance(outer_data, list):
             # CASO 1: A resposta JÁ É a lista diretamente
             print("Formato detectado: Resposta é uma lista direta.")
             raw_bus_list = outer_data
        elif isinstance(outer_data, dict):
            if 'data' in outer_data and isinstance(outer_data['data'], str):
                 # CASO 2: Chave 'data' com string JSON interna (formato original esperado)
                 print("Formato detectado: Chave 'data' com string JSON interna.")
                 try:
                    raw_bus_list = json.loads(outer_data['data'])
                    print(f"Parse do JSON interno bem-sucedido.")
                 except json.JSONDecodeError as json_err:
                    print(f"Erro ao fazer parse do JSON interno: {json_err}")
                    return jsonify({"error": "Falha ao fazer parse dos dados internos da API do Rio", "details": str(json_err)}), 500
            elif 'data' in outer_data and isinstance(outer_data['data'], list):
                 # CASO 3: Chave 'data' com a lista diretamente
                 print("Formato detectado: Chave 'data' com lista interna.")
                 raw_bus_list = outer_data['data']
            elif 'results' in outer_data and isinstance(outer_data['results'], list):
                 # CASO 4: Chave 'results' com a lista (Exemplo comum em APIs)
                 print("Formato detectado: Chave 'results' com lista interna.")
                 raw_bus_list = outer_data['results']
            # Adicione outros 'elif' aqui se os logs mostrarem outra estrutura
        # --- Fim da extração ---

        # Verifica se conseguiu extrair a lista
        if raw_bus_list is None:
            print("Erro: Não foi possível extrair a lista de ônibus da resposta da API do Rio com os formatos conhecidos.")
            print(f"DEBUG: Tipo da variável outer_data: {type(outer_data)}")
            return jsonify({"error": "Formato inesperado/desconhecido recebido da API do Rio"}), 500
        elif not isinstance(raw_bus_list, list):
            # Segurança extra caso algo tenha dado errado na extração
             print(f"Erro: raw_bus_list foi extraído mas não é uma lista (tipo: {type(raw_bus_list)}). Verifique a lógica de extração.")
             return jsonify({"error": "Erro interno ao extrair a lista de ônibus."}), 500

        print(f"Extração OK. {len(raw_bus_list)} registros brutos encontrados.")

        # Processa a lista de ônibus
        print("Iniciando processamento dos dados dos ônibus...")
        processed_data = process_bus_data(raw_bus_list)
        print(f"Processamento concluído. {len(processed_data)} ônibus retidos após filtro.")

        # Aplica o limite se foi solicitado e válido
        final_data = processed_data
        if limit is not None and limit > 0:
            print(f"Aplicando limite de {limit} registros.")
            final_data = processed_data[:limit] # Pega os primeiros 'limit' elementos
            print(f"Retornando {len(final_data)} registros após aplicar limite.")
        elif limit is not None and limit <=0 :
             print("Limite solicitado é zero ou negativo. Retornando lista vazia.")
             final_data = []

        # Retorna os dados finais (processados e talvez limitados)
        return jsonify(final_data)

    # ... (blocos except iguais aos anteriores, incluindo o JSONDecodeError para response.json()) ...
    except requests.exceptions.Timeout:
        print("Erro: Timeout ao conectar com a API do Rio.")
        return jsonify({"error": "Timeout ao buscar dados da API da prefeitura"}), 504 # Gateway Timeout
    except requests.exceptions.RequestException as e:
        print(f"Erro de requisição ao buscar dados da API do Rio: {e}")
        # Adicionar log da resposta se possível em caso de erro HTTP
        error_details = str(e)
        if e.response is not None:
             error_details += f" | Status: {e.response.status_code} | Response: {e.response.text[:200]}..."
        return jsonify({"error": "Erro ao buscar dados da API da prefeitura", "details": error_details}), 502 # Bad Gateway
    except json.JSONDecodeError as json_err: # Se response.json() falhar
        print(f"Erro ao fazer parse do JSON principal da resposta da API do Rio: {json_err}")
        response_text = "N/A"
        if 'response' in locals() and hasattr(response, 'text'): # Verifica se 'response' existe
             response_text = response.text[:500] # Loga o início do texto bruto
        print(f"DEBUG: Conteúdo da resposta (texto): {response_text}...")
        return jsonify({"error": "Falha ao fazer parse da resposta principal da API do Rio (não é JSON válido?)", "details": str(json_err)}), 500
    except Exception as e:
        # Captura qualquer outro erro inesperado durante o processo
        print(f"Erro inesperado no servidor: {e}")
        import traceback
        print(traceback.format_exc()) # Loga o stack trace completo para erros inesperados
        return jsonify({"error": "Erro interno do servidor de processamento", "details": str(e)}), 500


# ... (if __name__ == '__main__': igual) ...
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
