from flask import Flask, request, jsonify
from flask_restful import Api, Resource
from pymongo import MongoClient
from flask_cors import CORS, cross_origin
from flask_bcrypt import Bcrypt
import datetime

app = Flask(__name__)
CORS(app, origins="*")
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['CORS_ORIGINS'] = '*'
bcrypt = Bcrypt(app)

client = MongoClient('mongodb+srv://{username}:{password}@cluster0.tpi5rg1.mongodb.net/')
db = client['teste']
collection = db['Events']
users_collection = db['users']

@app.route('/registro', methods=['POST'])
def cadastro_usuario():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return {'message': 'Nome de usuário e senha são obrigatórios!'}, 400
    
    if ' ' in username or ' ' in password:
        return {'message': 'Nome de usuário e senha não podem conter espaços em branco!'}, 400
    
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    if users_collection.find_one({"username": username}):
        return {'message': 'Usuário já existe!'}, 400
    else:
        users_collection.insert_one({"username": username, "password": hashed_password})
        return {'message': 'Usuário criado com sucesso!'}, 201

@app.route('/login', methods=['POST'])
def login():
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return {'message': 'Nome de usuário e senha são obrigatórios!'}, 400

        user = users_collection.find_one({"username": username})

        if user and bcrypt.check_password_hash(user['password'], password):
            return {'message': "Login bem-sucedido!"}, 200
        else:
            return {'message': 'Credenciais inválidas'}, 401

@app.route('/favorites/<username>', methods=['GET', 'POST', 'DELETE'])
def favorites(username):
    user = users_collection.find_one({"username": username})

    if request.method == 'GET':
        return {'favorites': user.get('favorites', [])}

    elif request.method == 'POST':
        event_id = request.get_json().get('event_id')
        if event_id:
            users_collection.update_one({"username": username}, {'$addToSet': {'favorites': event_id}})
            return {'message': 'Evento favoritado com sucesso!'}
        else:
            return {'message': 'ID do evento é obrigatório!'}, 400

    elif request.method == 'DELETE':
        event_id = request.get_json().get('event_id')
        if event_id:
            users_collection.update_one({"username": username}, {'$pull': {'favorites': event_id}})
            return {'message': 'Evento desfavoritado com sucesso!'}
        else:
            return {'message': 'ID do evento é obrigatório!'}, 400          

@app.route('/criar', methods=['POST'])
def criar_registro():
    try:
        data = request.json
        responseData = data.get("responseData", {})
        event_id = responseData.get("id") or responseData.get("UrlEvento")
        if "id" in responseData:
            existing_event = collection.find_one({"responseData.id": event_id})
        if "UrlEvento" in responseData:
            existing_event = collection.find_one({"responseData.UrlEvento": event_id})

        if existing_event:
            #if (responseData.get("status") != "published" or
                    #(responseData.get("date", [{}])[0].get("status") != "available") or
                    #datetime.datetime.strptime(responseData.get("date", [{}])[0].get("dateTime", {}).get("date", ""), "%d/%m/%Y") < datetime.datetime.now()):
                #responseData["status"] = "Indisponivel"
                #collection.update_one({"_id": existing_event["_id"]}, {"$set": {"responseData": responseData}})
                #return jsonify({"message": "Evento atualizado para 'Indisponivel'."}), 200
            #else:
            return jsonify({"message": "Evento já existe e não foi atualizado."}), 200
        else:
            collection.insert_one({"responseData": responseData})
            return jsonify({"message": "Registro criado com sucesso!"}), 201
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        print(f"Erro: {str(e)}")
        return jsonify({"error": "Ocorreu um erro interno no servidor"}), 500

@app.route('/listar', methods=['GET'])
def listar_registros():
    filtro = request.args.get('filtro')

    if filtro:
        filtro_nome_evento = {
            '$or': [
                {'responseData.NomeEvento': {'$regex': f'.*{filtro}.*', '$options': 'i'}},
                {'responseData.title': {'$regex': f'.*{filtro}.*', '$options': 'i'}},
                {'responseData.description': {'$regex': f'.*{filtro}.*', '$options': 'i'}}
            ]
        }
        registros = list(collection.find(filtro_nome_evento))
    else:
        registros = list(collection.find())

    registros_formatados = []

    for registro in registros:
        responseData = registro.get("responseData", {})

        identificador = responseData.get("id") or responseData.get("UrlEvento", "")

        date_info = responseData.get("date", [{}])
        if date_info:
            date_time_info = date_info[0].get("dateTime", {})
            data_string = date_time_info.get("date", responseData.get("DataEvento", ""))
            time_string = date_time_info.get("time", "")
        else:
            data_string = responseData.get("DataEvento", "")
            time_string = ""

        if data_string: 
            try:
                date_datetime = datetime.datetime.strptime(data_string + " " + time_string, "%d/%m/%Y %H:%M:%S")
            except ValueError:
                date_datetime = None
        else:
            date_datetime = None

        if 'id' in responseData:
            extracted_data = {
                "id": identificador,
                "title": responseData.get("title", responseData.get("name", "")),
                "description": responseData.get("description", ""),
                "type": responseData.get("type", ""),
                "status": responseData.get("status", ""),
                "saleEnabled": responseData.get("saleEnabled", True),
                "link": "https://ingresse.com/" + responseData.get("link", ""),
                "photo": responseData.get("ImagemEvento", responseData.get("poster", "")),
                "datetime": date_datetime.strftime("%Y-%m-%d %H:%M:%S") if date_datetime else None,
                "Organizador": responseData.get("addedBy", {}).get("name", ""),
                "venue": responseData.get("LocalEvento", responseData.get("venue", {})),
            }
        else:
            extracted_data = {
                "id": identificador,
                "title": responseData.get("NomeEvento", ""),
                "saleEnabled": responseData.get("saleEnabled", True),
                "link": responseData.get("UrlEvento", ""),
                "photo": responseData.get("ImagemEvento", ""),
                "datetime": responseData.get("DataHora", ""),
                #"datetime": date_datetime.strftime("%Y-%m-%d %H:%M:%S") if date_datetime else None,
                "venue": responseData.get("LocalEvento", ""),
            }
        if date_datetime and date_datetime >= datetime.datetime.now():
            registros_formatados.append(extracted_data)
        else:
            registros_formatados.append(extracted_data)

    return jsonify(registros_formatados)

@app.route('/atualizar', methods=['PUT'])
def atualizar_registro():
    eventos = list(collection.find({}))
    for evento in eventos:
        date_info = evento.get("responseData", {}).get("date", [{}])[0].get("dateTime", {})
        if date_info:
            date_string = date_info.get("date", "")
            date_datetime = datetime.datetime.strptime(date_string, "%d/%m/%Y")
            if date_datetime < datetime.datetime.now():
                collection.update_one({"_id": evento["_id"]}, {"$set": {"responseData.status": "Indisponivel"}})
                return jsonify({"message": "Registro atualizado com sucesso!"}), 200
            else:
                return jsonify({"message": "Registro não encontrado."}), 404

@app.route('/deletar/<id>', methods=['DELETE'])
def deletar_registro(id):
    registro = collection.find_one({"responseData.id": int(id)})

    if registro:
        collection.delete_one({"_id": registro["_id"]})
        return jsonify({"message": "Registro deletado com sucesso!"}), 200
    else:
        return jsonify({"message": "Registro não encontrado."}), 404

@app.route('/deletar-duplicatas', methods=['DELETE'])
def verificar_e_deletar_duplicatas():
    pipeline = [
        {"$group": {"_id": "$responseData.id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]

    duplicatas = list(collection.aggregate(pipeline))

    for duplicata in duplicatas:
        id_duplicado = duplicata['_id']
        registros_duplicados = list(collection.find({"responseData.id": id_duplicado}))
        
        primeiro_registro = registros_duplicados[0]
        for registro in registros_duplicados[1:]:
            collection.delete_one({"_id": registro["_id"]})

    return jsonify({"message": "Duplicatas verificadas e excluídas com sucesso!"}), 200

@app.route('/deletar-todos', methods=['DELETE'])
def deletar_todos_os_registros():
    result = collection.delete_many({})
    return jsonify({"message": f"{result.deleted_count} registros foram deletados com sucesso!"}), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
