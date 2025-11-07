from flask import Flask, request, jsonify, abort
import logging
import psycopg2
import flask
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import datetime

app = Flask(__name__)

# Secret key para assinar tokens (NUNCA hardcode em produção!)
app.config["JWT_SECRET_KEY"] = "super-secret-key"  
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=1)  # token expira em 1h

jwt = JWTManager(app)

posts = [{"id": 1, "name": "Rui", "content": "Content of post 1"},{
    "id": 2, "name": "Rui", "content": "Content of post 2"},]

# configurar logger no início do ficheiro
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

StatusCodes = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500,
    'unauthorized': 401
}



def db_connection():
    return psycopg2.connect(
        user='postgres',
        password='postgres',
        #user='aulaspl',
        #password='aulaspl',
        host='127.0.0.1',     # ou 'localhost'
        port='5432',
        database='dbfichas'
        #database='bdproject2'
    )

## Demo GET
##
## Obtain all dep in JSON format
##

@app.route('/dep/', methods=['GET'])
def get_all_dep():
    logger.info('GET /dep')

    conn = db_connection()
    cur = conn.cursor()

    try:
        cur.execute('SELECT ndep, nome, local FROM dep')
        rows = cur.fetchall()

        logger.debug('GET /dep - parse')
        Results = []
        for row in rows:
            logger.debug(row)
            content = {'ndep': int(row[0]), 'nome': row[1], 'localidade': row[2]}
            #if theres no content, print "No content found"
            if not content:
                logger.debug('No content found')
            else:
                Results.append(content)  # appending to the payload to be returned

        response = {'status': StatusCodes['success'], 'results': Results}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'GET /dep - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

## Demo POST
### Add a new dep
@app.route('/dep/', methods=['POST'])
def add_dep():
    logger.info('POST /dep')
    payload = flask.request.get_json()

    conn = db_connection()
    cur = conn.cursor()

    logger.debug(f'POST /dep - payload: {payload}')
    print(payload)
    # basic payload validation

    # do not forget to validate every argument, e.g.,:
    if 'ndep' not in payload:
        response = {'status': StatusCodes['api_error'], 'results': 'ndep value not in payload'}
        return flask.jsonify(response)

    # parameterized queries, good for security and performance
    statement = 'INSERT INTO dep (ndep, nome, local) VALUES (%s, %s, %s)'
    values = (payload['ndep'], payload['nome'], payload['localidade'])

    try:
        cur.execute(statement, values)

        # commit the transaction
        conn.commit()
        response = {'status': StatusCodes['success'], 'results': f'Inserted dep {payload["ndep"]}'}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'POST /dep - error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}

        # an error occurred, rollback
        conn.rollback()

    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

#JWt Authentication
# Route for user login and token generation
@app.route('/login', methods=['POST'])
def login():
    payload = request.get_json()

    username = payload.get("username")
    password = payload.get("password")

    # ⚠️ Aqui devias validar com a tua base de dados de utilizadores
    if username == "rui" and password == "1234":
        # criar token
        token = create_access_token(identity=username)
        return jsonify(access_token=token), 200
    else:
        return jsonify({"msg": "Invalid credentials"}), 401

#Exemplo de endpoint protegido
@app.route('/protected', methods=['GET'])
@jwt_required()   # esta linha obriga a ter token válido
def protected():
    current_user = get_jwt_identity()  # recupera username guardado no token
    return jsonify(message=f"Hello {current_user}, you are authorized!"), 200



#route to handle the request
@app.route('/posts', methods=['GET'])
def get_posts():
    return jsonify(posts)


@app.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = next((post for post in posts if post['id'] == post_id), None)
    if post is None:
        abort(404)
    return jsonify(post)


@app.route('/posts', methods=['POST'])
def create_post():
    if not request.json or 'name' not in request.json:
        abort(400)
    post = {
        'id': request.json['id'], #posts[-1]['id'] + 1,
        'name': request.json['name'],
        'content': request.json.get('content', "")
    }
    posts.append(post)
    return jsonify(post), 201
def get_input():
    if not request.json or 'name' not in request.json:
        abort(400)
    posts.append({
        'id': input['id'], #posts[-1]['id'] + 1,
        'name': input("Enter name: "),
        'content': input("Enter content: ")
    })
    return jsonify(posts), 201

@app.route('/posts', methods=['DELETE'])
def delete_post():
    if not request.json or 'id' not in request.json:
        abort(400)
    post_id = request.json['id']
    post = next((post for post in posts if post['id'] == post_id), None)
    if post is None:
        abort(404)
    posts.remove(post)
    return jsonify({'result': True})

@app.route('/posts', methods=['PUT'])
def update_post():
    if not request.json or 'id' not in request.json:
        abort(400)
    post_id = request.json['id']
    post = next((post for post in posts if post['id'] == post_id), None)
    if post is None:
        abort(404)
    post['name'] = request.json.get('name', post['name'])
    post['content'] = request.json.get('content', post['content'])
    return jsonify(post)

if __name__ == '__main__':
    try:
        conn = db_connection()
        print("✅ Ligação estabelecida com sucesso!")
        conn.close()
    except Exception as e:
        print("❌ Erro na ligação:", e)

# Arrancar servidor Flask
    app.run(host='192.168.0.15', port=5000, debug=True)