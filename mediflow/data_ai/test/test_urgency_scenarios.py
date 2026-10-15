"""S3-01.4: casos sintéticos, no datos de pacientes. Ejecutar con unittest."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from urgency_detector import detect_urgency

CASES = [
    ('normal_control', 'Control de rutina sin hallazgos nuevos.', 'none_detected', 'routine'),
    ('normal_examen', 'Hemograma normal. Seguimiento habitual.', 'none_detected', 'routine'),
    ('cardiovascular', 'Síndrome coronario agudo.', 'possible_emergency', 'priority_review'),
    ('neurologico', 'Afasia de inicio súbito.', 'possible_emergency', 'priority_review'),
    ('respiratorio', 'Insuficiencia respiratoria aguda.', 'possible_emergency', 'priority_review'),
    ('shock', 'Shock anafiláctico.', 'possible_emergency', 'priority_review'),
    ('metabolico', 'Cetoacidosis diabética.', 'possible_emergency', 'priority_review'),
    ('trauma', 'Traumatismo craneoencefálico grave.', 'possible_emergency', 'priority_review'),
    ('infeccioso', 'Sepsis con disfunción orgánica.', 'possible_emergency', 'priority_review'),
    ('suicidio', 'Paciente con plan suicida actual.', 'possible_emergency', 'priority_review'),
    ('violencia_inmediata', 'Violencia intrafamiliar con peligro actual.', 'possible_urgent_assessment', 'priority_review'),
    ('abuso_sexual', 'Sospecha de abuso sexual.', 'none_detected', 'priority_review'),
    ('vif', 'Violencia intrafamiliar.', 'none_detected', 'priority_review'),
    ('abandono', 'Abandono de persona dependiente.', 'none_detected', 'priority_review'),
    ('crianza', 'Crianza negligente.', 'none_detected', 'priority_review'),
    ('sustancias', 'Uso nocivo de sustancias.', 'none_detected', 'priority_review'),
    ('embarazo_adolescente', 'Embarazo adolescente.', 'none_detected', 'priority_review'),
    ('biopsia', 'Biopsia positiva para malignidad.', 'none_detected', 'priority_review'),
    ('herida', 'Pie diabético Wagner 3.', 'none_detected', 'priority_review'),
    ('negacion', 'Niega plan suicida.', 'none_detected', 'routine'),
    ('historico', 'Antecedente de infarto agudo de miocardio.', 'none_detected', 'indeterminate'),
]

class ScenarioTests(unittest.TestCase):
    def test_scenarios(self):
        for name, text, clinical, priority in CASES:
            with self.subTest(name=name):
                result = detect_urgency(text)
                self.assertEqual(result['clinical_alert'], clinical)
                self.assertEqual(result['document_priority'], priority)

    def test_code_only_is_not_emergency(self):
        result = detect_urgency({'cie10_sugerido':'I21.9'})
        self.assertEqual(result['clinical_alert'], 'none_detected')
        self.assertEqual(result['document_priority'], 'indeterminate')
        self.assertTrue(result['requires_human_review'])

    def test_no_mutation(self):
        doc = {'diagnostico_principal':'Embarazo adolescente', 'cie10_sugerido':'Z34'}
        before = doc.copy()
        detect_urgency(doc)
        self.assertEqual(doc, before)

    def test_invalid_input(self):
        with self.assertRaises(TypeError):
            detect_urgency(['no es documento'])

if __name__ == '__main__':
    unittest.main()
