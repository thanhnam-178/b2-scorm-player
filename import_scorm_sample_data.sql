-- Import du lieu mau B2 SCORM Player
-- Chay trong database lv04_db bang psql.
-- Chi them ban ghi; khong xoa va khong cap nhat ban ghi cu.
BEGIN;

-- 1. Hoc ky
INSERT INTO terms (term_code, name, start_date, end_date, status) VALUES ('2026-HK1', 'HK1 2026-2027', DATE '2026-09-07', DATE '2027-01-10', 'open') ON CONFLICT DO NOTHING;

-- 2. Nguoi hoc va nhan su
INSERT INTO people (person_code, family_name, given_name, email, person_type, program_code, cohort) VALUES ('SV000001', 'Nguyễn', 'Văn An', 'sv000001@stu.edu.vn', 'student', 'CNTT-K2024', 2024) ON CONFLICT DO NOTHING;
INSERT INTO people (person_code, family_name, given_name, email, person_type, program_code, cohort) VALUES ('SV000002', 'Trần', 'Thị Bình', 'sv000002@stu.edu.vn', 'student', 'CNTT-K2024', 2024) ON CONFLICT DO NOTHING;
INSERT INTO people (person_code, family_name, given_name, email, person_type, program_code, cohort) VALUES ('SV000003', 'Lê', 'Minh Chi', 'sv000003@stu.edu.vn', 'student', 'CNTT-K2024', 2024) ON CONFLICT DO NOTHING;
INSERT INTO people (person_code, family_name, given_name, email, person_type, program_code, cohort) VALUES ('SV000004', 'Phạm', 'Quốc Dũng', 'sv000004@stu.edu.vn', 'student', 'CNTT-K2024', 2024) ON CONFLICT DO NOTHING;
INSERT INTO people (person_code, family_name, given_name, email, person_type, program_code, cohort) VALUES ('SV000005', 'Hoàng', 'Thu Em', 'sv000005@stu.edu.vn', 'student', 'CNTT-K2024', 2024) ON CONFLICT DO NOTHING;
INSERT INTO people (person_code, family_name, given_name, email, person_type, program_code, cohort) VALUES ('SV000006', 'Vũ', 'Đức Giang', 'sv000006@stu.edu.vn', 'student', 'CNTT-K2024', 2024) ON CONFLICT DO NOTHING;
INSERT INTO people (person_code, family_name, given_name, email, person_type, program_code, cohort) VALUES ('GV001', 'Lê', 'Minh Khoa', 'gv001@stu.edu.vn', 'staff', NULL, NULL) ON CONFLICT DO NOTHING;
INSERT INTO people (person_code, family_name, given_name, email, person_type, program_code, cohort) VALUES ('TG001', 'Đỗ', 'Ngọc Lan', 'tg001@stu.edu.vn', 'staff', NULL, NULL) ON CONFLICT DO NOTHING;

-- 3. Lop hoc phan
INSERT INTO sections (section_code, term_code, course_code, course_name, syllabus_version, faculty_code, faculty_name, credits, updated_at) VALUES ('2026-HK1-INT1234-01', '2026-HK1', 'INT1234', 'Nhập môn lập trình', '2024.1', 'CNTT', 'Công nghệ thông tin', 3, TIMESTAMPTZ '2026-08-15T01:00:00Z') ON CONFLICT DO NOTHING;

-- 4. Dang ky hoc phan
INSERT INTO enrollments (section_code, person_code, role, group_code, status, updated_at) VALUES ('2026-HK1-INT1234-01', 'SV000001', 'student', 'T1', 'registered', TIMESTAMPTZ '2026-08-20T02:00:00Z') ON CONFLICT DO NOTHING;
INSERT INTO enrollments (section_code, person_code, role, group_code, status, updated_at) VALUES ('2026-HK1-INT1234-01', 'SV000002', 'student', 'T1', 'registered', TIMESTAMPTZ '2026-08-20T02:00:00Z') ON CONFLICT DO NOTHING;
INSERT INTO enrollments (section_code, person_code, role, group_code, status, updated_at) VALUES ('2026-HK1-INT1234-01', 'SV000003', 'student', 'T2', 'registered', TIMESTAMPTZ '2026-08-21T02:00:00Z') ON CONFLICT DO NOTHING;
INSERT INTO enrollments (section_code, person_code, role, group_code, status, updated_at) VALUES ('2026-HK1-INT1234-01', 'SV000004', 'student', 'T2', 'cancelled', TIMESTAMPTZ '2026-08-22T02:00:00Z') ON CONFLICT DO NOTHING;
INSERT INTO enrollments (section_code, person_code, role, group_code, status, updated_at) VALUES ('2026-HK1-INT1234-01', 'SV000005', 'student', 'T1', 'withdrawn', TIMESTAMPTZ '2026-08-23T02:00:00Z') ON CONFLICT DO NOTHING;
INSERT INTO enrollments (section_code, person_code, role, group_code, status, updated_at) VALUES ('2026-HK1-INT1234-01', 'SV000006', 'student', 'T2', 'registered', TIMESTAMPTZ '2026-08-24T02:00:00Z') ON CONFLICT DO NOTHING;
INSERT INTO enrollments (section_code, person_code, role, group_code, status, updated_at) VALUES ('2026-HK1-INT1234-01', 'GV001', 'editingteacher', NULL, 'registered', TIMESTAMPTZ '2026-08-15T02:00:00Z') ON CONFLICT DO NOTHING;
INSERT INTO enrollments (section_code, person_code, role, group_code, status, updated_at) VALUES ('2026-HK1-INT1234-01', 'TG001', 'teacher', NULL, 'registered', TIMESTAMPTZ '2026-08-15T02:00:00Z') ON CONFLICT DO NOTHING;

COMMIT;
