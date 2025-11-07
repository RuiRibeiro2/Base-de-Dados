-- INIT DATABASE

-- 1. ADMIN USER (OBRIGATÓRIO)
INSERT INTO users (username, password, email, role) 
VALUES ('admin', 'admin123', 'admin@uc.pt', 'admin')
ON CONFLICT (username) DO NOTHING;

INSERT INTO admin (user_id) 
SELECT user_id FROM users WHERE username = 'admin'
ON CONFLICT (user_id) DO NOTHING;

-- 2. DEGREE PROGRAMS (CRÍTICO)
INSERT INTO degree_program (name, tuition_fee) VALUES
('Licenciatura em Engenharia Informática', 5000.00),
('Mestrado em Ciências de Dados', 7000.00),
('Licenciatura em Matemática Aplicada', 4500.00)
ON CONFLICT (name) DO NOTHING;

-- 3. COURSES (IMPORTANTE)
INSERT INTO course (code, name, credits) VALUES
('EI', 'Engenharia Informática', 180),
('CD', 'Ciências de Dados', 120), 
('MA', 'Matemática Aplicada', 180)
ON CONFLICT (code) DO NOTHING;

-- 4. SAMPLE INSTRUCTORS (Antes de criar edições de curso)
INSERT INTO users (username, password, email, role) VALUES
('professor1', 'prof123', 'prof1@uc.pt', 'instructor'),
('professor2', 'prof456', 'prof2@uc.pt', 'instructor')
ON CONFLICT (username) DO NOTHING;

INSERT INTO instructor (user_id, is_coordinator) 
SELECT user_id, true FROM users WHERE username = 'professor1'
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO instructor (user_id, is_coordinator)
SELECT user_id, false FROM users WHERE username = 'professor2' 

-- 3. Criar course editions
/*
INSERT INTO course_edition (course_code, year, capacity, coordinator_id) VALUES
('EI', 2024, 100, (SELECT user_id FROM users WHERE username = 'professor1')),
('CD', 2024, 50, (SELECT user_id FROM users WHERE username = 'professor2'))
ON CONFLICT DO NOTHING;*/
INSERT INTO course_edition (course_code, year, capacity, coordinator_id)
VALUES 
('EI', 2024, 100, (SELECT user_id FROM users WHERE username = 'professor1')),
('CD', 2024, 50, (SELECT user_id FROM users WHERE username = 'professor2'))
ON CONFLICT (course_code, year) DO NOTHING;



-- 4. Criar classes
/*INSERT INTO class (edition_id, type, schedule) VALUES
(1, 'T', 'Segunda 9:00-11:00'),
(1, 'PL', 'Quarta 14:00-16:00'),
(2, 'T', 'Terça 10:00-12:00')
ON CONFLICT DO NOTHING;
*/
-- Criar classes de forma dinâmica, sem depender dos IDs
INSERT INTO class (edition_id, type, schedule)
SELECT edition_id, 'T', 'Segunda 9:00-11:00'
FROM course_edition WHERE course_code = 'EI'
ON CONFLICT DO NOTHING;

INSERT INTO class (edition_id, type, schedule)
SELECT edition_id, 'PL', 'Quarta 14:00-16:00'
FROM course_edition WHERE course_code = 'EI'
ON CONFLICT DO NOTHING;

INSERT INTO class (edition_id, type, schedule)
SELECT edition_id, 'T', 'Terça 10:00-12:00'
FROM course_edition WHERE course_code = 'CD'
ON CONFLICT DO NOTHING;


ON CONFLICT (user_id) DO NOTHING;

-- 5. SAMPLE STUDENTS (OPCIONAL MAS ÚTIL)
INSERT INTO users (username, password, email, role) VALUES
('student1', 'student123', 'student1@uc.pt', 'student'),
('student2', 'student456', 'student2@uc.pt', 'student')
ON CONFLICT (username) DO NOTHING;

INSERT INTO student (user_id, name, district) 
SELECT user_id, 'João Silva', 'Coimbra' FROM users WHERE username = 'student1'
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO student (user_id, name, district)
SELECT user_id, 'Maria Santos', 'Aveiro' FROM users WHERE username = 'student2'
ON CONFLICT (user_id) DO NOTHING;

-- 6. ACTIVITIES (OPCIONAL)
INSERT INTO activity (name, fee) VALUES
('Clube de Programação', 25.00),
('Clube de Robótica', 30.00)
ON CONFLICT (name) DO NOTHING;