import unittest
from urgency_detector import detect_urgency

class DetectorTests(unittest.TestCase):
    def test_suicidal_plan(self):
        r = detect_urgency('Paciente con plan suicida actual.')
        self.assertEqual(r['clinical_alert'], 'possible_emergency')
        self.assertEqual(r['document_priority'], 'priority_review')

    def test_negation(self):
        r = detect_urgency('Niega plan suicida.')
        self.assertEqual(r['clinical_alert'], 'none_detected')

    def test_historical(self):
        r = detect_urgency('Antecedente de infarto agudo de miocardio.')
        self.assertEqual(r['clinical_alert'], 'none_detected')

    def test_document_priority(self):
        r = detect_urgency('Biopsia positiva para malignidad.')
        self.assertEqual(r['clinical_alert'], 'none_detected')
        self.assertEqual(r['document_priority'], 'priority_review')

    def test_psychosocial(self):
        r = detect_urgency('Sospecha de abuso sexual en menor de edad.')
        self.assertEqual(r['document_priority'], 'priority_review')

    def test_code_only(self):
        r = detect_urgency({'cie10_sugerido': 'I21.9'})
        self.assertEqual(r['clinical_alert'], 'none_detected')
        self.assertTrue(r['requires_human_review'])

    def test_normal(self):
        r = detect_urgency('Control de rutina sin hallazgos nuevos.')
        self.assertEqual(r['document_priority'], 'routine')
        self.assertFalse(r['requires_human_review'])

    def test_accents(self):
        r = detect_urgency('Paciente con síndrome coronario agudo.')
        self.assertEqual(r['clinical_alert'], 'possible_emergency')

if __name__ == '__main__':
    unittest.main()
