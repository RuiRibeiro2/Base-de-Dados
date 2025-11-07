-- ========================
-- Tabela de Utilizadores
-- ========================
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL CHECK (role IN ('student', 'instructor', 'admin'))
);

-- ========================
-- Tabela de Estudantes
-- ========================
CREATE TABLE student (
    user_id INT PRIMARY KEY REFERENCES users(user_id),
    name TEXT NOT NULL,
    birth_date DATE,
    address TEXT,
    district TEXT
);

-- ========================
-- Tabela de Professores
-- ========================
CREATE TABLE instructor (
    user_id INT PRIMARY KEY REFERENCES users(user_id),
    is_coordinator BOOLEAN NOT NULL
);

-- ========================
-- Tabela de Administradores
-- ========================
CREATE TABLE admin (
    user_id INT PRIMARY KEY REFERENCES users(user_id)
);

-- ========================
-- Registo Académico
-- ========================
CREATE TABLE academic_record (
    record_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES student(user_id),
    average NUMERIC(5,2),
    approved_courses INT,
    current_semester INT
);

-- ========================
-- Programas (Licenciatura/Mestrado)
-- ========================
CREATE TABLE degree_program (
    degree_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    tuition_fee NUMERIC(10,2) NOT NULL
);

-- ========================
-- Conta Financeira
-- ========================
CREATE TABLE financial_account (
    account_id SERIAL PRIMARY KEY,
    student_id INT NOT NULL REFERENCES student(user_id),
    balance NUMERIC(10,2) NOT NULL
);

-- ========================
-- Cursos
-- ========================
CREATE TABLE course (
    code VARCHAR(10) PRIMARY KEY,
    name TEXT NOT NULL,
    credits INT NOT NULL
);

-- ========================
-- Edições de Curso
-- ========================
CREATE TABLE course_edition (
    edition_id SERIAL PRIMARY KEY,
    course_code VARCHAR(10) NOT NULL REFERENCES course(code),
    year INT NOT NULL,
    capacity INT NOT NULL,
    schedule TEXT,
    coordinator_id INT NOT NULL REFERENCES instructor(user_id)
);

-- ========================
-- Aulas
-- ========================
CREATE TABLE class (
    class_id SERIAL PRIMARY KEY,
    edition_id INT NOT NULL REFERENCES course_edition(edition_id),
    type CHAR(2) NOT NULL CHECK (type IN ('T', 'PL')),
    schedule TEXT NOT NULL
);

-- ========================
-- Salas
-- ========================
CREATE TABLE classroom (
    room_id SERIAL PRIMARY KEY,
    building TEXT NOT NULL,
    capacity INT NOT NULL,
    location TEXT NOT NULL
);

-- ========================
-- Atribuição de Salas
-- ========================
CREATE TABLE class_assignment (
    class_id INT NOT NULL REFERENCES class(class_id),
    room_id INT NOT NULL REFERENCES classroom(room_id),
    PRIMARY KEY (class_id, room_id)
);

-- ========================
-- Atividades (Clubes, Desporto)
-- ========================
CREATE TABLE activity (
    activity_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    fee NUMERIC(10,2) NOT NULL
);

-- ========================
-- Inscrições em Graus
-- ========================
CREATE TABLE degree_enrollment (
    student_id INT NOT NULL REFERENCES student(user_id),
    degree_id INT NOT NULL REFERENCES degree_program(degree_id),
    enrollment_date DATE NOT NULL,
    PRIMARY KEY (student_id, degree_id)
);

-- ========================
-- Inscrições em Cursos
-- ========================
CREATE TABLE course_enrollment (
    student_id INT NOT NULL REFERENCES student(user_id),
    edition_id INT NOT NULL REFERENCES course_edition(edition_id),
    grade NUMERIC(5,2),
    attendance INT,
    PRIMARY KEY (student_id, edition_id)
);

-- ========================
-- Participação em Atividades
-- ========================
CREATE TABLE activity_participation (
    student_id INT NOT NULL REFERENCES student(user_id),
    activity_id INT NOT NULL REFERENCES activity(activity_id),
    registration_date DATE NOT NULL,
    PRIMARY KEY (student_id, activity_id)
);

-- ========================
-- Professores Atribuídos
-- ========================
CREATE TABLE instructor_assignment (
    instructor_id INT NOT NULL REFERENCES instructor(user_id),
    edition_id INT NOT NULL REFERENCES course_edition(edition_id),
    is_coordinator BOOLEAN NOT NULL,
    PRIMARY KEY (instructor_id, edition_id)
);

-- ========================
-- Pré-Requisitos de Cursos
-- ========================
CREATE TABLE course_prerequisites (
    course_code VARCHAR(10) NOT NULL REFERENCES course(code),
    prerequisite_code VARCHAR(10) NOT NULL REFERENCES course(code),
    PRIMARY KEY (course_code, prerequisite_code)
);

-- ========================
-- Cursos por Programa
-- ========================
CREATE TABLE degree_courses (
    degree_id INT NOT NULL REFERENCES degree_program(degree_id),
    course_code VARCHAR(10) NOT NULL REFERENCES course(code),
    PRIMARY KEY (degree_id, course_code)
);

-- ========================
-- Transações Financeiras
-- ========================
CREATE TABLE financial_transaction (
    transaction_id SERIAL PRIMARY KEY,
    account_id INT NOT NULL REFERENCES financial_account(account_id),
    amount NUMERIC(10,2) NOT NULL,
    description TEXT NOT NULL,
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activity_id INT REFERENCES activity(activity_id),
    degree_id INT REFERENCES degree_program(degree_id)
);
