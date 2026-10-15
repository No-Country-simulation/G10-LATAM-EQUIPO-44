import copy
import unittest
from urgency_json_adapter import evaluate_analysis, make_sidecar

BASE = {'status':'procesado','clasificacion':{'tipo_documento':'Informe','especialidad':None,'nivel_prioridad':'Rutina','score_confianza_clasificacion':0.9},'datos_extraidos':{'paciente':{'nombre':None,'edad':None},'medico_solicitante':{'nombre':None,'matricula':None},'estudio_realizado':None,'diagnostico_principal':None,'cie10_sugerido':None,'medicamentos_recetados':[]},'decision_enrutamiento':{'destino_principal':'Cola_Historia_Clinica','requiere_auditoria_humana':False,'justificacion_enrutamiento':'Prueba'}}
class TestAdapter(unittest.TestCase):
    def test_no_mutation(self):
        a=copy.deepcopy(BASE); original=copy.deepcopy(a)
        out=make_sidecar(a,source_text='Control rutinario')
        self.assertEqual(a,original)
        self.assertEqual(out['analysis'],original)
    def test_suicidal_risk(self):
        out=evaluate_analysis(BASE,source_text='Paciente con plan suicida actual')
        self.assertTrue(out['review_recommended'])
        self.assertEqual(out['suggested_priority'],'Urgente')
    def test_missing_source(self):
        out=evaluate_analysis(BASE)
        self.assertEqual(out['input_coverage'],'structured_only')
        self.assertTrue(out['review_recommended'])
    def test_invalid(self):
        with self.assertRaises(TypeError): evaluate_analysis([])
if __name__=='__main__': unittest.main()
