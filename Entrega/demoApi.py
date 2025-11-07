##
## =============================================
## ============== Bases de Dados ===============
## ============== LEI  2024/2025 ===============
## =============================================
## =============================================
## === Department of Informatics Engineering ===
## =========== University of Coimbra ===========
## =============================================
##
## Authors:
## Rui Ribeiro a2021189478@student.dei.uc
##   


import flask
import logging
import psycopg2
import time
import random
import datetime
from datetime import datetime, timedelta  # ← Para expiração do token
import jwt          # JWT handling tokens
from functools import wraps
import json

app = flask.Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'some_jwt_secret_key'
# configurar logger no início do ficheiro
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


StatusCodes = {
    'success': 200,
    'api_error': 400,
    'internal_error': 500,
    'unauthorized': 401
}

##########################################################
## DATABASE ACCESS
##########################################################

def db_connection():
    print("Connecting to the PostgreSQL database...")
    db = psycopg2.connect(
        user='postgres',
        password='postgres',
        host='127.0.0.1',
        port='5432',
        #database='dbfichas',
        database='bdproject'  # change to your database name
    )
    #db.autocommit = True  # ← ADD THIS LINE
    print("Connection successful")
    return db

##########################################################
## AUTHENTICATION HELPERS
##########################################################

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = flask.request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Token missing or invalid', 'results': None}), 401
        token = auth.split(' ',1)[1]
        try:
            payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            flask.g.user_id = payload.get('user_id')
            flask.g.role = payload.get('role')
        except jwt.ExpiredSignatureError:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Token expired', 'results': None}), 401
        except jwt.InvalidTokenError:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Invalid token', 'results': None}), 401
        return f(*args, **kwargs)
    return decorated

##########################################################
## ENDPOINTS
##########################################################

@app.route('/dbproj/user', methods=['PUT'])
def login_user():
    data = flask.request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username and password are required', 'results': None})

    # CONSULTA REAL À BD 
    conn = db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT user_id, role FROM users WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        
        if not user:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Invalid credentials', 'results': None})
        
        print("DEBUG - User found in login user:")
        print(f"DEBUG - User ID: {user[0]}, Role: {user[1]}")
        # GERAR JWT TOKEN REAL AQUI
        token = jwt.encode({
            'user_id': user[0],
            'role': user[1],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, app.config['JWT_SECRET_KEY'], algorithm='HS256')
        
        response = {'status': StatusCodes['success'], 'errors': None, 'results': token}
        logger.info(f'User {username} logged in successfully')
        #print(f"Generated token: {token}")
        
    except Exception as error:
        response = {'status': StatusCodes['internal_error'], 'errors': str(error)}
    finally:
        conn.close()

    return flask.jsonify(response)


@app.route('/dbproj/register/student', methods=['POST'])
@token_required
def register_student():
    # Verificar se user tem permissão (apenas admin) - OBRIGATÓRIO
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'admin':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admin can register students', 'results': None})

    data = flask.request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    # Apenas os campos MENCIONADOS NO ENUNCIADO
    if not username or not email or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username, email, and password are required', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:
        # 1. Inserir na tabela users com role 'student'
        cur.execute("""
            INSERT INTO users (username, password, email, role)
            VALUES (%s, %s, %s, 'student')
            RETURNING user_id
        """, (username, password, email))
        
        user_id = cur.fetchone()[0]

         # 2. Inserir na tabela student
        cur.execute("""
            INSERT INTO student (user_id)
            VALUES (%s)
        """, (user_id,))
        
        # NOTA: O enunciado não pede para preencher outros campos automaticamente
        # Campos como name, birth_date, etc. podem ser atualizados posteriormente
        # ou através de endpoints específicos se necessário
        
        conn.commit()

        response = {'status': StatusCodes['success'], 'errors': None, 'results': user_id}

    except psycopg2.IntegrityError:
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'errors': 'Username already exists', 'results': None}
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        logger.error(f'Register student error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


@app.route('/dbproj/register/admin', methods=['POST'])
@token_required
def register_admin():
    # Verificar se user tem permissão (apenas admin pode criar admin)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'admin':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admin can register other admins', 'results': None})

    data = flask.request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username, email, and password are required', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:
        # 1. Inserir na tabela users
        cur.execute("""
            INSERT INTO users (username, password, email, role)
            VALUES (%s, %s, %s, 'admin')
            RETURNING user_id
        """, (username, password, email))
        user_id = cur.fetchone()[0]
        # 2. Inserir na tabela admin
        cur.execute("""
            INSERT INTO admin (user_id)
            VALUES (%s)
        """, (user_id,))
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': user_id}
    except psycopg2.IntegrityError:
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'errors': 'Username already exists', 'results': None}
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/register/instructor', methods=['POST'])
@token_required
def register_instructor():
    # Verificar se user tem permissão (apenas admin)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'admin':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admin can register instructors', 'results': None})

    data = flask.request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    is_coordinator = data.get('is_coordinator', False)  # Campo específico de instructor

    if not username or not email or not password:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Username, email, and password are required', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:
        # 1. Inserir na tabela users
        cur.execute("""
            INSERT INTO users (username, password, email, role)
            VALUES (%s, %s, %s, 'instructor')
            RETURNING user_id
        """, (username, password, email))
        user_id = cur.fetchone()[0]
        # 2. Inserir na tabela instructor (com campo específico)
        cur.execute("""
            INSERT INTO instructor (user_id, is_coordinator)
            VALUES (%s, %s)
        """, (user_id, is_coordinator))
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': user_id}
    except psycopg2.IntegrityError:
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'errors': 'Username already exists', 'results': None}
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/enroll_degree/<degree_id>', methods=['POST'])
@token_required
def enroll_degree(degree_id):
    # Verificar se user tem permissão (apenas admin)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'admin':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admin can enroll students in degrees', 'results': None})

    data = flask.request.get_json()
    student_id = data.get('student_id')
    date = data.get('date')  # Data de matrícula

    if not student_id or not date:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student ID and date are required', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:
        # 1. Verificar se o student existe
        cur.execute("SELECT 1 FROM student WHERE user_id = %s", (student_id,))
        if not cur.fetchone():
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student does not exist', 'results': None})

        # 2. Verificar se o degree existe
        cur.execute("SELECT 1 FROM degree_program WHERE degree_id = %s", (degree_id,))
        if not cur.fetchone():
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Degree program does not exist', 'results': None})

        # 3. Verificar se já está matriculado
        cur.execute("SELECT 1 FROM degree_enrollment WHERE student_id = %s AND degree_id = %s", (student_id, degree_id))
        if cur.fetchone():
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student is already enrolled in this degree', 'results': None})

        # 4. Inserir na tabela degree_enrollment
        cur.execute("""
            INSERT INTO degree_enrollment (student_id, degree_id, enrollment_date)
            VALUES (%s, %s, %s)
        """, (student_id, degree_id, date))

        # 5. O TRIGGER deve criar automaticamente a financial_account
        # Conforme exigido pelo enunciado: "generates a debt entry in the student's financial account"
        
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None}

    except psycopg2.IntegrityError as e:
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'errors': 'Integrity error: ' + str(e), 'results': None}
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        logger.error(f'Enroll degree error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/enroll_activity/<activity_id>', methods=['POST'])
@token_required
def enroll_activity(activity_id):
    # Verificar se user tem permissão (apenas student)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'student':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only students can enroll in activities', 'results': None})
    current_user_id = flask.g.user_id

    conn = db_connection()
    cur = conn.cursor()

    try:
        # 1. Verificar se a activity existe
        cur.execute("SELECT name, fee FROM activity WHERE activity_id = %s", (activity_id,))
        activity = cur.fetchone()
        if not activity:
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Activity does not exist', 'results': None})
        
        activity_name = activity[0]
        activity_fee = activity[1]

        # 2. Verificar se student já está inscrito
        cur.execute("SELECT 1 FROM activity_participation WHERE student_id = %s AND activity_id = %s", (current_user_id, activity_id))
        if cur.fetchone():
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student is already enrolled in this activity', 'results': None})

        # 3. Inserir na tabela activity_participation
        cur.execute("""
            INSERT INTO activity_participation (student_id, activity_id, registration_date)
            VALUES (%s, %s, CURRENT_DATE)
        """, (current_user_id, activity_id))

        # 4. Atualizar financial_account com a fee (conforme enunciado)
        cur.execute("""
            UPDATE financial_account 
            SET balance = balance + %s
            WHERE student_id = %s
        """, (activity_fee, current_user_id))

        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None}

    except psycopg2.IntegrityError:
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'errors': 'Database integrity error', 'results': None}
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        logger.error(f'Enroll activity error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/enroll_course_edition/<course_edition_id>', methods=['POST'])
@token_required
def enroll_course_edition(course_edition_id):
    # Verificar se user tem permissão (apenas student)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'student':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only students can enroll in courses', 'results': None})
    current_user_id = flask.g.user_id

    data = flask.request.get_json()
    classes = data.get('classes', [])  # Lista de class_ids

    if not classes:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'At least one class ID is required', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:
        # 1. Verificar se course_edition existe e obter detalhes
        cur.execute("""
            SELECT ce.course_code, ce.capacity, ce.year, c.name
            FROM course_edition ce
            JOIN course c ON ce.course_code = c.code
            WHERE ce.edition_id = %s
        """, (course_edition_id,))
        
        edition_info = cur.fetchone()
        if not edition_info:
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Course edition does not exist', 'results': None})
        
        course_code, capacity, year, course_name = edition_info

        # 2. Verificar capacidade da edition
        cur.execute("""
            SELECT COUNT(*) 
            FROM course_enrollment 
            WHERE edition_id = %s
        """, (course_edition_id,))
        
        current_enrollments = cur.fetchone()[0]
        if current_enrollments >= capacity:
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Course edition is full', 'results': None})

        # 3. Verificar se student já está inscrito
        cur.execute("""
            SELECT 1 FROM course_enrollment 
            WHERE student_id = %s AND edition_id = %s
        """, (current_user_id, course_edition_id))
        
        if cur.fetchone():
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student is already enrolled in this course edition', 'results': None})

        # 4. Verificar pré-requisitos (conforme enunciado)
        cur.execute("""
            SELECT COUNT(*) FROM course_prerequisites cp
            WHERE cp.course_code = %s
            AND cp.prerequisite_code NOT IN (
                SELECT c.code 
                FROM course_enrollment ce
                JOIN course_edition ced ON ce.edition_id = ced.edition_id
                JOIN course c ON ced.course_code = c.code
                WHERE ce.student_id = %s AND ce.grade >= 9.5
            )
        """, (course_code, current_user_id))
        
        missing_prerequisites = cur.fetchone()[0]
        if missing_prerequisites > 0:
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student does not meet course prerequisites', 'results': None})

        # 5. Inserir enrollment
        cur.execute("""
            INSERT INTO course_enrollment (student_id, edition_id)
            VALUES (%s, %s)
        """, (current_user_id, course_edition_id))

        # 6. Inscrever student nas classes selecionadas
        for class_id in classes:
            # Verificar se a class pertence à course_edition
            cur.execute("""
                SELECT 1 FROM class 
                WHERE class_id = %s AND edition_id = %s
            """, (class_id, course_edition_id))
            
            if not cur.fetchone():
                return flask.jsonify({
                    'status': StatusCodes['api_error'], 
                    'errors': f'Class {class_id} does not belong to course edition {course_edition_id}',
                    'results': None
                })
            
            # Inserir na nova tabela student_class
            cur.execute("""
                INSERT INTO student_class (student_id, class_id)
                VALUES (%s, %s)
            """, (current_user_id, class_id))

        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None}

    except psycopg2.IntegrityError as e:
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'errors': 'Integrity error: ' + str(e), 'results': None}
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        logger.error(f'Enroll course edition error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/submit_grades/<course_edition_id>', methods=['POST'])
@token_required
def submit_grades(course_edition_id):
    # Verificar se user tem permissão (apenas coordinator do course_edition)
    # Usar flask.g.role para verificar permissão
    current_user_id = flask.g.user_id
    current_user_role = flask.g.role
    if current_user_role != 'instructor':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only instructors can submit grades', 'results': None})

    data = flask.request.get_json()
    period = data.get('period')  # Época de avaliação (e.g., 'Normal', 'Recurso')
    grades = data.get('grades', [])  # Lista de [student_id, grade]

    if not period or not grades:
        return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Evaluation period and grades are required', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:
        # 1. Verificar se user é coordinator desta course_edition
        cur.execute("""
            SELECT coordinator_id FROM course_edition 
            WHERE edition_id = %s
        """, (course_edition_id,))
        
        result = cur.fetchone()
        if not result:
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Course edition does not exist', 'results': None})
            
        coordinator_id = result[0]
        if coordinator_id != current_user_id:
            return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only the course coordinator can submit grades', 'results': None})

        # 2. Processar cada grade
        for grade_data in grades:
            if len(grade_data) != 2:
                continue  # Saltar entradas inválidas
                
            student_id, grade_value = grade_data
            
            # Validar grade
            if not isinstance(grade_value, (int, float)) or grade_value < 0 or grade_value > 20:
                return flask.jsonify({'status': StatusCodes['api_error'], 'errors': f'Invalid grade for student {student_id}', 'results': None})
            
            # 3. Verificar se student está inscrito na course_edition
            cur.execute("""
                SELECT 1 FROM course_enrollment 
                WHERE student_id = %s AND edition_id = %s
            """, (student_id, course_edition_id))
            
            if not cur.fetchone():
                return flask.jsonify({'status': StatusCodes['api_error'], 'errors': f'Student {student_id} is not enrolled in this course edition', 'results': None})
            
            # 4. Atualizar ou inserir a grade
            cur.execute("""
                UPDATE course_enrollment 
                SET grade = %s, evaluation_period = %s
                WHERE student_id = %s AND edition_id = %s
            """, (grade_value, period, student_id, course_edition_id))

        # 5. Atualizar academic records (conforme enunciado)
        # O enunciado diz: "updates the approved students' academic averages"
        # Isso pode ser feito via trigger ou procedure adicional
        
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None}

    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        logger.error(f'Submit grades error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/student_details/<student_id>', methods=['GET'])
@token_required
def student_details(student_id):
    # Verificar permissões: admin ou o próprio student
    # Usar flask.g.role e flask.g.user_id para verificar permissão
    current_user_id = flask.g.user_id
    current_user_role = flask.g.role
    if current_user_role != 'admin' and current_user_id != int(student_id):
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Permission denied', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:
        # Query para obter todos os cursos do student com detalhes
        cur.execute("""
            SELECT 
                ce.edition_id,
                c.name as course_name,
                ced.year as course_year,
                ce.grade,
                ce.evaluation_period,
                ce.attendance,
                c.code as course_code,
                ced.coordinator_id,
                u.username as coordinator_name
            FROM course_enrollment ce
            JOIN course_edition ced ON ce.edition_id = ced.edition_id
            JOIN course c ON ced.course_code = c.code
            LEFT JOIN users u ON ced.coordinator_id = u.user_id
            WHERE ce.student_id = %s
            ORDER BY ced.year DESC, ce.edition_id DESC
        """, (student_id,))
        
        courses = cur.fetchall()
        
        # Construir resposta
        resultStudentDetails = []
        for course in courses:
            resultStudentDetails.append({
                'course_edition_id': course[0],
                'course_name': course[1],
                'course_edition_year': course[2],
                'grade': float(course[3]) if course[3] is not None else None,
                'evaluation_period': course[4],
                'attendance': course[5],
                'course_code': course[6],
                'coordinator_id': course[7],
                'coordinator_name': course[8]
            })
        
        response = {'status': StatusCodes['success'], 'errors': None, 'results': resultStudentDetails}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Student details error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/degree_details/<degree_id>', methods=['GET'])
@token_required
def degree_details(degree_id):
    # Verificar se user tem permissão (apenas admin)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'admin':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admin can view degree details', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:
        # Query corrected to filter course editions that belong to the requested degree
        # Uses degree_courses(degree_id, course_code) to find the courses associated with the degree
        cur.execute("""
            SELECT
                c.code AS course_id,
                c.name AS course_name,
                ce.edition_id AS course_edition_id,
                ce.year AS course_edition_year,
                ce.capacity,
                COUNT(ce_enroll.student_id) AS enrolled_count,
                COUNT(ce_enroll.student_id) FILTER (WHERE ce_enroll.grade >= 9.5) AS approved_count,
                ce.coordinator_id,
                ARRAY_REMOVE(ARRAY_AGG(DISTINCT ia.instructor_id), NULL) AS instructors
            FROM course_edition ce
            JOIN course c ON ce.course_code = c.code
            JOIN degree_courses dc ON dc.course_code = c.code AND dc.degree_id = %s
            LEFT JOIN course_enrollment ce_enroll ON ce.edition_id = ce_enroll.edition_id
            LEFT JOIN instructor_assignment ia ON ce.edition_id = ia.edition_id
            GROUP BY c.code, c.name, ce.edition_id, ce.year, ce.capacity, ce.coordinator_id
            ORDER BY ce.year DESC, c.code
        """, (degree_id,))

        degree_courses = cur.fetchall()
        
        # Construir resposta
        resultDegreeDetails = []
        for course in degree_courses:
            resultDegreeDetails.append({
                'course_id': course[0],
                'course_name': course[1],
                'course_edition_id': course[2],
                'course_edition_year': course[3],
                'capacity': course[4],
                'enrolled_count': course[5],
                'approved_count': course[6],
                'coordinator_id': course[7],
                'instructors': course[8] if course[8] is not None else []
            })
        
        response = {'status': StatusCodes['success'], 'errors': None, 'results': resultDegreeDetails}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Degree details error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/top3', methods=['GET'])
@token_required
def top3_students():
    # Permission check (only admin allowed)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'admin':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admin can access this endpoint', 'results': None})

    conn = db_connection()
    cur = conn.cursor()
    try:
        # Single SQL query that computes student averages for the current year,
        # selects top 3 students and aggregates their grades and activities as JSON
        cur.execute("""
            WITH student_avg AS (
                SELECT 
                    s.user_id AS student_id,
                    s.name AS student_name,
                    ROUND(AVG(ce.grade)::numeric, 2) AS average_grade
                FROM course_enrollment ce
                JOIN course_edition ed ON ce.edition_id = ed.edition_id
                JOIN student s ON ce.student_id = s.user_id
                WHERE ce.grade IS NOT NULL
                    AND ed.year = 2024  -- ← MUDAR PARA 2024
                GROUP BY s.user_id, s.name
            ),
            top_three AS (
                SELECT student_id, student_name, average_grade
                FROM student_avg
                ORDER BY average_grade DESC
                LIMIT 3
            )
            SELECT 
                t.student_id,
                t.student_name,
                t.average_grade,
                COALESCE(
                    (SELECT json_agg(json_build_object(
                        'course_edition_id', ce.edition_id,
                        'course_edition_name', c.name || ' - ' || ed.year::text,
                        'grade', ce.grade,
                        'date', ed.year || '-01-01'
                    ))
                    FROM course_enrollment ce
                    JOIN course_edition ed ON ce.edition_id = ed.edition_id
                    JOIN course c ON ed.course_code = c.code
                    WHERE ce.student_id = t.student_id 
                        AND ce.grade IS NOT NULL
                        AND ed.year = 2024  -- ← MUDAR PARA 2024
                    ), '[]'::json) AS grades,
                COALESCE(
                    (SELECT json_agg(a.name)
                    FROM activity_participation ap
                    JOIN activity a ON ap.activity_id = a.activity_id
                    WHERE ap.student_id = t.student_id
                    ), '[]'::json) AS activities
            FROM top_three t
            ORDER BY t.average_grade DESC
        """)
        rows = cur.fetchall()
        results = []
        for r in rows:
            student_id = r[0]
            student_name = r[1]
            avg_grade = float(r[2]) if r[2] is not None else None
            
            # Já vêm como JSON correto
            grades_json = r[3] or []
            activities_json = r[4] or []

            results.append({
                'student_name': student_name,  # ← APENAS student_name (sem student_id)
                'average_grade': avg_grade,
                'grades': grades_json,
                'activities': activities_json
            })

        # Commit the transaction if successful
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': results}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Top3 error: {error}')
        # Rollback on error
        conn.rollback()
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/top_by_district', methods=['GET'])
@token_required
def top_by_district():
    # Permission check (only admin allowed in this demo - consistent with other endpoints)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'admin':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admin can access this endpoint', 'results': None})

    conn = db_connection()
    cur = conn.cursor()
    try:
        # Compute average grade per student and district, then pick top student(s) per district
        cur.execute("""
            WITH student_averages AS (
                SELECT s.user_id AS student_id,
                       s.district,
                       ROUND(AVG(ce.grade)::numeric, 2) AS average_grade
                FROM course_enrollment ce
                JOIN student s ON ce.student_id = s.user_id
                WHERE ce.grade IS NOT NULL AND s.district IS NOT NULL
                GROUP BY s.user_id, s.district
            ),
            ranked AS (
                SELECT *, RANK() OVER (PARTITION BY district ORDER BY average_grade DESC) AS rnk
                FROM student_averages
            )
            SELECT student_id, district, average_grade
            FROM ranked
            WHERE rnk = 1
            ORDER BY average_grade DESC
        """)

        rows = cur.fetchall()
        results = [
            {'student_id': r[0], 'district': r[1], 'average_grade': float(r[2])}
            for r in rows
        ]

        # Commit the transaction if successful
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': results}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Top by district error: {error}')
        # Rollback on error
        conn.rollback()
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/report', methods=['GET'])
@token_required
def monthly_report():
    # Permission check (admin role)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'admin':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admin can access this endpoint', 'results': None})

    conn = db_connection()
    cur = conn.cursor()
    try:
        # NOTE: the schema does not contain a grade timestamp. We aggregate by course_edition year
        # and produce a month label as YEAR-01. If you have a date for the evaluation, replace the
        # date logic below to use it (e.g., grade_date). The query returns, for each month, the
        # course edition with the most approved students (grade >= 9.5) and counts of approved/evaluated.
        cur.execute("""
            WITH evaluation_stats AS (
                SELECT TO_CHAR(TO_DATE(CE.year::text || '-01-01', 'YYYY-MM-DD'), 'YYYY-MM') AS month_label,
                       ce.edition_id AS course_edition_id,
                       c.name AS course_edition_name,
                       COUNT(ce_en.student_id) FILTER (WHERE ce_en.grade IS NOT NULL) AS evaluated,
                       COUNT(ce_en.student_id) FILTER (WHERE ce_en.grade >= 9.5) AS approved
                FROM course_enrollment ce_en
                JOIN course_edition ce ON ce_en.edition_id = ce.edition_id
                JOIN course c ON ce.course_code = c.code
                WHERE ce_en.grade IS NOT NULL
                  AND ce.year >= EXTRACT(YEAR FROM CURRENT_DATE) - 1
                GROUP BY month_label, ce.edition_id, c.name, ce.year
            ),
            best_per_month AS (
                SELECT DISTINCT ON (month_label) *
                FROM evaluation_stats
                ORDER BY month_label, approved DESC
            )
            SELECT month_label AS month, course_edition_id, course_edition_name, approved, evaluated
            FROM best_per_month
            ORDER BY month_label DESC
        """)

        rows = cur.fetchall()
        results = [
            {
                'month': r[0],
                'course_edition_id': r[1],
                'course_edition_name': r[2],
                'approved': int(r[3]) if r[3] is not None else 0,
                'evaluated': int(r[4]) if r[4] is not None else 0
            }
            for r in rows
        ]

        # Commit the transaction if successful
        conn.commit()
        response = {'status': StatusCodes['success'], 'errors': None, 'results': results}

    except (Exception, psycopg2.DatabaseError) as error:
        logger.error(f'Monthly report error: {error}')
        # Rollback on error
        conn.rollback()
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)

@app.route('/dbproj/delete_details/<student_id>', methods=['DELETE'])
@token_required
def delete_student(student_id):
    # Verificar se user tem permissão (apenas admin)
    # Usar flask.g.role para verificar permissão
    if flask.g.role != 'admin':
        return flask.jsonify({'status': StatusCodes['unauthorized'], 'errors': 'Only admin can delete student data', 'results': None})

    conn = db_connection()
    cur = conn.cursor()

    try:
        # 1. Verificar se o student existe
        cur.execute("SELECT 1 FROM users WHERE user_id = %s AND role = 'student'", (student_id,))
        if not cur.fetchone():
            return flask.jsonify({'status': StatusCodes['api_error'], 'errors': 'Student does not exist', 'results': None})

        # 2. Remover dados por ordem (respeitando foreign keys)
        # Começar pelas tabelas dependentes e terminar na tabela users
        
        # a. Remover activity participation
        cur.execute("DELETE FROM activity_participation WHERE student_id = %s", (student_id,))
        
        # b. Remover student_class assignments
        cur.execute("DELETE FROM student_class WHERE student_id = %s", (student_id,))
        
        # c. Remover course enrollments
        cur.execute("DELETE FROM course_enrollment WHERE student_id = %s", (student_id,))
        
        # d. Remover financial_account
        cur.execute("DELETE FROM financial_account WHERE student_id = %s", (student_id,))
        
        # e. Remover degree enrollments
        cur.execute("DELETE FROM degree_enrollment WHERE student_id = %s", (student_id,))
        
        # f. Remover academic_record
        cur.execute("DELETE FROM academic_record WHERE student_id = %s", (student_id,))
        
        # g. Remover da tabela student
        cur.execute("DELETE FROM student WHERE user_id = %s", (student_id,))
        
        # h. Finalmente remover da tabela users
        cur.execute("DELETE FROM users WHERE user_id = %s", (student_id,))

        conn.commit()
        
        # Verificar se realmente foi removido
        cur.execute("SELECT 1 FROM users WHERE user_id = %s", (student_id,))
        if not cur.fetchone():
            response = {'status': StatusCodes['success'], 'errors': None, 'results': 'Student data deleted successfully'}
        else:
            response = {'status': StatusCodes['internal_error'], 'errors': 'Failed to delete student data', 'results': None}

    except psycopg2.IntegrityError as e:
        conn.rollback()
        response = {'status': StatusCodes['api_error'], 'errors': f'Integrity error: {str(e)}', 'results': None}
    except (Exception, psycopg2.DatabaseError) as error:
        conn.rollback()
        logger.error(f'Delete student error: {error}')
        response = {'status': StatusCodes['internal_error'], 'errors': str(error), 'results': None}
    finally:
        if conn is not None:
            conn.close()

    return flask.jsonify(response)


def initialize_database():
    """Execute the initialization SQL script"""
    try:
        conn = db_connection()
        cur = conn.cursor()
        
        # Read and execute the SQL file
        with open('init_database.sql', 'r') as file:
            sql_commands = file.read()
            cur.execute(sql_commands)
        
        conn.commit()
        print("Database initialized successfully!")
        
    except Exception as error:
        print(f"Database initialization failed: {error}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# No seu código Python, antes de criar triggers:
def create_triggers():
    try:
        conn = db_connection()
        cur = conn.cursor()
        
        # Verificar se os triggers já existem
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.triggers 
            WHERE trigger_name IN ('trigger_after_degree_enrollment', 'trigger_after_grade_update')
        """)
        
        trigger_count = cur.fetchone()[0]
        if trigger_count >= 2:
            print("Triggers already exist, skipping creation")
            return
            
        # Se não existirem, executar o script SQL
        with open('triggers.sql', 'r') as file:
            sql_commands = file.read()
            cur.execute(sql_commands)
        
        conn.commit()
        print("Triggers created successfully!")
        
    except Exception as error:
        print(f"Error creating triggers: {error}")

if __name__ == '__main__':
    #logging config at top
    
    # initialize the database (create tables, triggers, etc.)
    initialize_database()
    create_triggers()

    host = '127.0.0.1'
    #host = '192.168.x.x'  # change to your IP if needed
    port = 5000 #normal port for Flask apps
    #app.run(host=host, port=port, debug=True)
    app.run(debug=False)
    #app.run(host=host, debug=True, threaded=True, port=port)
    #logger.info(f'API stubs online: http://{host}:{port}')
