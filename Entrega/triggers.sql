-- =============================================
-- TRIGGERS FOR UNIVERSITY DATABASE
-- =============================================

-- 1. Function para financial account
CREATE OR REPLACE FUNCTION create_financial_account()
RETURNS TRIGGER AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM financial_account WHERE student_id = NEW.student_id) THEN
        INSERT INTO financial_account (student_id, balance)
        SELECT NEW.student_id, dp.tuition_fee
        FROM degree_program dp
        WHERE dp.degree_id = NEW.degree_id;
    ELSE
        UPDATE financial_account 
        SET balance = balance + (SELECT tuition_fee FROM degree_program WHERE degree_id = NEW.degree_id),
            last_update = CURRENT_TIMESTAMP
        WHERE student_id = NEW.student_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Function para academic records
'''CREATE OR REPLACE FUNCTION update_academic_records()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.grade >= 9.5 THEN
        UPDATE academic_record 
        SET 
            approved_courses = approved_courses + 1,
            average = (
                SELECT AVG(grade) 
                FROM course_enrollment 
                WHERE student_id = NEW.student_id AND grade >= 9.5
            )
        WHERE student_id = NEW.student_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
'''
CREATE OR REPLACE FUNCTION update_academic_records()
RETURNS TRIGGER AS $$
DECLARE
    current_avg NUMERIC;
    course_count INTEGER;
BEGIN
    -- Debug inicial
    RAISE NOTICE '🔍 TRIGGER INICIADO: student=%, new_grade=%, old_grade=%', 
        NEW.student_id, NEW.grade, OLD.grade;

    -- Verificar se grade é válida e >= 9.5
    IF NEW.grade IS NOT NULL AND NEW.grade >= 9.5 THEN
        RAISE NOTICE '✅ Student % APROVADO com %', NEW.student_id, NEW.grade;
        
        -- Verificar se academic_record existe
        SELECT COUNT(*) INTO course_count FROM academic_record WHERE student_id = NEW.student_id;
        RAISE NOTICE '📊 Academic_record existe? %', (course_count > 0);
        
        -- Calcular média atual
        SELECT COALESCE(AVG(grade), 0) INTO current_avg
        FROM course_enrollment 
        WHERE student_id = NEW.student_id AND grade >= 9.5;
        
        RAISE NOTICE '📈 Média calculada: %', current_avg;
        
        -- Se academic_record não existe, criar
        IF course_count = 0 THEN
            RAISE NOTICE '👤 CRIANDO academic_record para student %', NEW.student_id;
            INSERT INTO academic_record (student_id, degree_id, enrollment_date, approved_courses, average)
            SELECT 
                NEW.student_id,
                de.degree_id,
                de.enrollment_date,
                0,
                0
            FROM degree_enrollment de
            WHERE de.student_id = NEW.student_id
            LIMIT 1
            RETURNING record_id;
            
            RAISE NOTICE '📝 Academic_record criado';
        END IF;

        -- Atualizar academic_record
        RAISE NOTICE '🔄 ATUALIZANDO academic_record para student %', NEW.student_id;
        
        UPDATE academic_record 
        SET 
            approved_courses = approved_courses + 1,
            average = current_avg
        WHERE student_id = NEW.student_id;
        
        -- Verificar se update funcionou
        GET DIAGNOSTICS course_count = ROW_COUNT;
        RAISE NOTICE '✅ Update afectou % linhas', course_count;
        
    ELSE
        RAISE NOTICE '❌ NÃO APROVADO: student=%, grade=%', NEW.student_id, NEW.grade;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Drop e create triggers com IF EXISTS
DROP TRIGGER IF EXISTS trigger_after_degree_enrollment ON degree_enrollment;
CREATE TRIGGER trigger_after_degree_enrollment
    AFTER INSERT ON degree_enrollment
    FOR EACH ROW
    EXECUTE FUNCTION create_financial_account();

DROP TRIGGER IF EXISTS trigger_after_grade_update ON course_enrollment;
CREATE TRIGGER trigger_after_grade_update
    AFTER UPDATE OF grade ON course_enrollment
    FOR EACH ROW
    EXECUTE FUNCTION update_academic_records();